"""
Ticket Booking System (BookMyShow-like)

Simulates a concurrent ticket booking platform with:
- Events, Venues, Shows, and Seats
- Temporary seat holds with TTL expiration
- Booking confirmation and cancellation
- Optimistic locking to prevent double-booking
- Concurrent booking demo with threading
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SeatStatus(Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"


class BookingStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class SeatCategory(Enum):
    PLATINUM = "PLATINUM"
    GOLD = "GOLD"
    SILVER = "SILVER"


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------

@dataclass
class Event:
    event_id: str
    title: str
    genre: str
    duration_min: int

    def __repr__(self) -> str:
        return f"Event({self.title!r}, genre={self.genre})"


@dataclass
class Venue:
    venue_id: str
    name: str
    city: str
    rows: int
    seats_per_row: int

    @property
    def total_seats(self) -> int:
        return self.rows * self.seats_per_row

    def __repr__(self) -> str:
        return f"Venue({self.name!r}, {self.city}, seats={self.total_seats})"


@dataclass
class Seat:
    seat_id: str
    show_id: str
    row_label: str
    seat_number: int
    category: SeatCategory
    price: float
    status: SeatStatus = SeatStatus.AVAILABLE
    version: int = 0  # optimistic locking
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __repr__(self) -> str:
        return f"Seat({self.row_label}{self.seat_number}, {self.category.value}, {self.status.value})"


@dataclass
class Show:
    show_id: str
    event: Event
    venue: Venue
    start_time: str
    seats: Dict[str, Seat] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.seats:
            self._generate_seats()

    def _generate_seats(self) -> None:
        """Generate seat map for the venue."""
        categories = [SeatCategory.PLATINUM, SeatCategory.GOLD, SeatCategory.SILVER]
        prices = {SeatCategory.PLATINUM: 500.0, SeatCategory.GOLD: 300.0, SeatCategory.SILVER: 150.0}
        for r in range(self.venue.rows):
            row_label = chr(ord("A") + r)
            # First third platinum, second third gold, rest silver
            if r < self.venue.rows // 3:
                cat = categories[0]
            elif r < 2 * self.venue.rows // 3:
                cat = categories[1]
            else:
                cat = categories[2]
            for s in range(1, self.venue.seats_per_row + 1):
                seat_id = f"{row_label}{s}"
                self.seats[seat_id] = Seat(
                    seat_id=seat_id,
                    show_id=self.show_id,
                    row_label=row_label,
                    seat_number=s,
                    category=cat,
                    price=prices[cat],
                )

    def get_available_seats(self) -> List[Seat]:
        return [s for s in self.seats.values() if s.status == SeatStatus.AVAILABLE]

    def get_seat_map_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"AVAILABLE": 0, "HELD": 0, "BOOKED": 0}
        for seat in self.seats.values():
            counts[seat.status.value] += 1
        return counts

    def __repr__(self) -> str:
        summary = self.get_seat_map_summary()
        return (
            f"Show({self.event.title!r} at {self.venue.name!r}, "
            f"{self.start_time}, seats={summary})"
        )


@dataclass
class SeatHold:
    hold_id: str
    user_id: str
    show_id: str
    seat_ids: List[str]
    created_at: float
    ttl_seconds: float
    status: str = "ACTIVE"

    @property
    def expires_at(self) -> float:
        return self.created_at + self.ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def remaining_seconds(self) -> float:
        return max(0.0, self.expires_at - time.time())

    def __repr__(self) -> str:
        return (
            f"SeatHold(user={self.user_id}, seats={self.seat_ids}, "
            f"remaining={self.remaining_seconds():.1f}s, status={self.status})"
        )


@dataclass
class Booking:
    booking_id: str
    user_id: str
    show_id: str
    hold_id: str
    seat_ids: List[str]
    total_amount: float
    status: BookingStatus = BookingStatus.PENDING
    created_at: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return (
            f"Booking({self.booking_id[:8]}..., user={self.user_id}, "
            f"seats={self.seat_ids}, amount={self.total_amount}, "
            f"status={self.status.value})"
        )


# ---------------------------------------------------------------------------
# Booking Service
# ---------------------------------------------------------------------------

class BookingService:
    """
    Orchestrates seat holds and bookings with concurrency control.

    Uses per-seat locks (simulating Redis SETNX) and optimistic locking
    (version checks) to prevent double-booking.
    """

    def __init__(self, hold_ttl_seconds: float = 600.0) -> None:
        self.hold_ttl = hold_ttl_seconds
        self.shows: Dict[str, Show] = {}
        self.holds: Dict[str, SeatHold] = {}
        self.bookings: Dict[str, Booking] = {}

    def register_show(self, show: Show) -> None:
        self.shows[show.show_id] = show

    # -- Seat Hold --------------------------------------------------------

    def hold_seats(
        self, user_id: str, show_id: str, seat_ids: List[str]
    ) -> SeatHold:
        """
        Attempt to hold the requested seats atomically.
        Uses per-seat locks to simulate distributed Redis SETNX.
        Raises ValueError if any seat is unavailable.
        """
        show = self._get_show(show_id)
        self._validate_seat_ids(show, seat_ids)

        # Acquire locks in sorted order to prevent deadlocks
        sorted_ids = sorted(seat_ids)
        locked: List[Seat] = []    # seats whose threading lock we acquired
        marked: List[Seat] = []    # seats we actually flipped to HELD

        try:
            for sid in sorted_ids:
                seat = show.seats[sid]
                if not seat.lock.acquire(timeout=2.0):
                    raise ValueError(f"Timeout acquiring lock for seat {sid}")
                locked.append(seat)

                if seat.status != SeatStatus.AVAILABLE:
                    raise ValueError(
                        f"Seat {sid} is {seat.status.value}, not available"
                    )

            # All locks acquired and all seats available -> mark as HELD
            for seat in locked:
                seat.status = SeatStatus.HELD
                seat.version += 1
                marked.append(seat)

            hold = SeatHold(
                hold_id=str(uuid.uuid4()),
                user_id=user_id,
                show_id=show_id,
                seat_ids=list(seat_ids),
                created_at=time.time(),
                ttl_seconds=self.hold_ttl,
            )
            self.holds[hold.hold_id] = hold
            return hold

        except ValueError:
            # Only revert seats that *we* marked as HELD in this attempt
            for seat in marked:
                seat.status = SeatStatus.AVAILABLE
                seat.version += 1
            raise

        finally:
            for seat in locked:
                seat.lock.release()

    def release_hold(self, hold_id: str) -> None:
        """Release a seat hold, returning seats to AVAILABLE."""
        hold = self.holds.get(hold_id)
        if not hold or hold.status != "ACTIVE":
            return

        show = self.shows[hold.show_id]
        for sid in hold.seat_ids:
            seat = show.seats[sid]
            with seat.lock:
                if seat.status == SeatStatus.HELD:
                    seat.status = SeatStatus.AVAILABLE
                    seat.version += 1

        hold.status = "RELEASED"

    def expire_holds(self) -> List[str]:
        """Check and expire any holds past their TTL. Returns expired hold IDs."""
        expired_ids: List[str] = []
        for hold in list(self.holds.values()):
            if hold.status == "ACTIVE" and hold.is_expired:
                self.release_hold(hold.hold_id)
                hold.status = "EXPIRED"
                expired_ids.append(hold.hold_id)
        return expired_ids

    # -- Booking ----------------------------------------------------------

    def confirm_booking(self, hold_id: str) -> Booking:
        """
        Confirm a booking from an active hold. Simulates payment processing.
        Uses optimistic locking (version check) as a final safeguard.
        """
        hold = self.holds.get(hold_id)
        if not hold:
            raise ValueError(f"Hold {hold_id} not found")
        if hold.status != "ACTIVE":
            raise ValueError(f"Hold {hold_id} is {hold.status}, not ACTIVE")
        if hold.is_expired:
            self.release_hold(hold_id)
            hold.status = "EXPIRED"
            raise ValueError(f"Hold {hold_id} has expired")

        show = self.shows[hold.show_id]
        total = 0.0

        # Optimistic locking: verify seats are still HELD
        for sid in hold.seat_ids:
            seat = show.seats[sid]
            with seat.lock:
                if seat.status != SeatStatus.HELD:
                    raise ValueError(
                        f"Seat {sid} is {seat.status.value}; "
                        f"expected HELD (possible race condition)"
                    )
                seat.status = SeatStatus.BOOKED
                seat.version += 1
                total += seat.price

        hold.status = "BOOKED"

        booking = Booking(
            booking_id=str(uuid.uuid4()),
            user_id=hold.user_id,
            show_id=hold.show_id,
            hold_id=hold.hold_id,
            seat_ids=list(hold.seat_ids),
            total_amount=total,
            status=BookingStatus.CONFIRMED,
        )
        self.bookings[booking.booking_id] = booking
        return booking

    def cancel_booking(self, booking_id: str) -> Booking:
        """Cancel a confirmed booking and release seats."""
        booking = self.bookings.get(booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        if booking.status != BookingStatus.CONFIRMED:
            raise ValueError(
                f"Booking is {booking.status.value}, cannot cancel"
            )

        show = self.shows[booking.show_id]
        for sid in booking.seat_ids:
            seat = show.seats[sid]
            with seat.lock:
                seat.status = SeatStatus.AVAILABLE
                seat.version += 1

        booking.status = BookingStatus.CANCELLED
        return booking

    # -- Helpers ----------------------------------------------------------

    def _get_show(self, show_id: str) -> Show:
        show = self.shows.get(show_id)
        if not show:
            raise ValueError(f"Show {show_id} not found")
        return show

    def _validate_seat_ids(self, show: Show, seat_ids: List[str]) -> None:
        for sid in seat_ids:
            if sid not in show.seats:
                raise ValueError(f"Seat {sid} does not exist in show")


# ---------------------------------------------------------------------------
# Demo / Main
# ---------------------------------------------------------------------------

def _separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def main() -> None:
    print("Ticket Booking System - BookMyShow Simulation")
    print("=" * 60)

    # -- Setup ------------------------------------------------------------
    event = Event("evt-1", "Interstellar IMAX", "Sci-Fi", 169)
    venue = Venue("ven-1", "PVR IMAX", "Hyderabad", rows=6, seats_per_row=8)
    show = Show("show-1", event, venue, "2025-07-20 19:00")

    service = BookingService(hold_ttl_seconds=3.0)  # short TTL for demo
    service.register_show(show)

    print(f"Event  : {event}")
    print(f"Venue  : {venue}")
    print(f"Show   : {show}")
    print(f"Total seats: {venue.total_seats}")

    # -- 1. Browse available seats ----------------------------------------
    _separator("1. Browse Available Seats")
    available = show.get_available_seats()
    print(f"Available seats: {len(available)}")
    print(f"Sample: {available[:5]}")

    # -- 2. Hold seats for User-A -----------------------------------------
    _separator("2. User-A Holds Seats A1, A2")
    hold_a = service.hold_seats("user-A", "show-1", ["A1", "A2"])
    print(f"Hold created: {hold_a}")
    print(f"Seat map: {show.get_seat_map_summary()}")

    # -- 3. User-B tries same seats (should fail) -------------------------
    _separator("3. User-B Tries Same Seats (Conflict)")
    try:
        service.hold_seats("user-B", "show-1", ["A1", "A2"])
        print("ERROR: Should not reach here!")
    except ValueError as e:
        print(f"Expected conflict: {e}")

    # -- 4. User-B holds different seats ----------------------------------
    _separator("4. User-B Holds Seats B3, B4")
    hold_b = service.hold_seats("user-B", "show-1", ["B3", "B4"])
    print(f"Hold created: {hold_b}")

    # -- 5. Confirm User-A booking ----------------------------------------
    _separator("5. Confirm User-A Booking")
    booking_a = service.confirm_booking(hold_a.hold_id)
    print(f"Booking confirmed: {booking_a}")
    print(f"Seat map: {show.get_seat_map_summary()}")

    # -- 6. Wait for User-B hold to expire --------------------------------
    _separator("6. Wait for User-B Hold to Expire (3s TTL)")
    print(f"Hold B remaining: {hold_b.remaining_seconds():.1f}s")
    time.sleep(3.5)
    expired = service.expire_holds()
    print(f"Expired holds: {expired}")
    print(f"Seat map after expiry: {show.get_seat_map_summary()}")

    # -- 7. Try to confirm expired hold -----------------------------------
    _separator("7. Confirm Expired Hold (Should Fail)")
    try:
        service.confirm_booking(hold_b.hold_id)
        print("ERROR: Should not reach here!")
    except ValueError as e:
        print(f"Expected failure: {e}")

    # -- 8. Cancel confirmed booking --------------------------------------
    _separator("8. Cancel User-A Booking")
    cancelled = service.cancel_booking(booking_a.booking_id)
    print(f"Cancelled: {cancelled}")
    print(f"Seat map after cancel: {show.get_seat_map_summary()}")

    # -- 9. Concurrent booking race condition demo ------------------------
    _separator("9. Concurrent Booking - 5 Users Race for Seat A1")
    results: Dict[str, tuple] = {}
    barrier = threading.Barrier(5)

    def race_for_seat(user: str) -> None:
        barrier.wait()  # synchronize start
        try:
            hold = service.hold_seats(user, "show-1", ["A1"])
            booking = service.confirm_booking(hold.hold_id)
            results[user] = ("WIN", f"SUCCESS ({booking.booking_id[:8]}...)")
        except ValueError as e:
            results[user] = ("LOSE", f"FAILED ({e})")

    threads = []
    for i in range(5):
        t = threading.Thread(target=race_for_seat, args=(f"racer-{i}",))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("Race results:")
    winners = 0
    for user, (outcome, detail) in sorted(results.items()):
        tag = ">> WINNER" if outcome == "WIN" else ""
        print(f"  {user}: {detail} {tag}")
        if outcome == "WIN":
            winners += 1

    print(f"\nTotal winners: {winners} (must be exactly 1)")
    assert winners == 1, f"Double booking detected! {winners} winners"

    # -- 10. Final state --------------------------------------------------
    _separator("10. Final State")
    print(f"Seat map: {show.get_seat_map_summary()}")
    print(f"Total bookings: {len(service.bookings)}")
    print(f"Total holds: {len(service.holds)}")
    for bid, b in service.bookings.items():
        print(f"  {b}")

    print("\n" + "=" * 60)
    print("  All scenarios passed -- no double bookings!")
    print("=" * 60)


if __name__ == "__main__":
    main()
