import threading

class Seat:
    def __init__(self, row: int, col: int, seat_type: str = "standard"):
        self.row = row
        self.col = col
        self.seat_type = seat_type
        self.is_booked = False
        self.lock = threading.Lock()  # per-seat lock

    def __repr__(self):
        return f"Seat({self.row}, {self.col}, type={self.seat_type!r})"


class ReclinerSeat(Seat):
    """Premium recliner seat with extra legroom."""
    def __init__(self, row: int, col: int):
        super().__init__(row, col, seat_type="recliner")


class BalconySeat(Seat):
    """Balcony-level seat with elevated view."""
    def __init__(self, row: int, col: int):
        super().__init__(row, col, seat_type="balcony")


class LowerSeat(Seat):
    """Lower-level seat closer to the screen."""
    def __init__(self, row: int, col: int):
        super().__init__(row, col, seat_type="lower")


class SeatFactory:
    """Factory for creating different seat types.

    Supported types: 'recliner', 'balcony', 'lower', 'standard'.
    """
    _registry: dict[str, type] = {
        "recliner": ReclinerSeat,
        "balcony": BalconySeat,
        "lower": LowerSeat,
        "standard": Seat,
    }

    @classmethod
    def create(cls, seat_type: str, row: int, col: int) -> Seat:
        """Create a seat by type name.

        Args:
            seat_type: One of 'recliner', 'balcony', 'lower', 'standard'.
            row: Row index.
            col: Column index.

        Returns:
            A Seat instance of the requested type.
        """
        seat_cls = cls._registry.get(seat_type)
        if not seat_cls:
            raise ValueError(
                f"Unknown seat type '{seat_type}'. "
                f"Available: {list(cls._registry.keys())}"
            )
        if seat_cls is Seat:
            return Seat(row, col, seat_type="standard")
        return seat_cls(row, col)

    @classmethod
    def register(cls, seat_type: str, seat_cls: type):
        """Register a new seat type at runtime."""
        cls._registry[seat_type] = seat_cls

class Theatre:
    """Base theatre with a 2D grid of seats.

    Args:
        name: Display name for the theatre.
        rows: Number of rows.
        cols: Number of columns.
        seat_layout: Optional dict mapping row indices to seat type strings.
                     Rows not listed default to 'standard'.
                     Example: {0: "recliner", 1: "recliner", 2: "balcony"}
    """
    def __init__(self, name: str, rows: int, cols: int,
                 seat_layout: dict[int, str] | None = None):
        self.name = name
        self.rows = rows
        self.cols = cols
        self.seats = [
            [SeatFactory.create(seat_layout.get(r, "standard") if seat_layout else "standard", r, c)
             for c in range(cols)]
            for r in range(rows)
        ]

    def get_seat(self, row, col):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.seats[row][col]
        return None

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, rows={self.rows}, cols={self.cols})"


class IMAXTheatre(Theatre):
    """IMAX theatre: rows 0-1 recliner, 2-5 standard, 6-7 balcony."""
    def __init__(self, name: str):
        layout = {0: "recliner", 1: "recliner", 6: "balcony", 7: "balcony"}
        super().__init__(name, rows=8, cols=12, seat_layout=layout)


class StandardTheatre(Theatre):
    """Standard theatre: front rows lower, rest standard."""
    def __init__(self, name: str):
        layout = {0: "lower", 1: "lower"}
        super().__init__(name, rows=5, cols=8, seat_layout=layout)


class MiniTheatre(Theatre):
    """Small screening room."""
    def __init__(self, name: str):
        super().__init__(name, rows=3, cols=5)


class TheatreFactory:
    """Factory for creating different types of theatres.

    Supported types: 'imax', 'standard', 'mini', or 'custom'.
    """
    _registry: dict[str, type] = {
        "imax": IMAXTheatre,
        "standard": StandardTheatre,
        "mini": MiniTheatre,
    }

    @classmethod
    def create(cls, theatre_type: str, name: str, **kwargs) -> Theatre:
        """Create a theatre by type name.

        Args:
            theatre_type: One of 'imax', 'standard', 'mini', or 'custom'.
            name: Display name for the theatre.
            **kwargs: For 'custom' type, pass rows and cols.

        Returns:
            A Theatre instance.
        """
        if theatre_type == "custom":
            rows = kwargs.get("rows", 5)
            cols = kwargs.get("cols", 5)
            seat_layout = kwargs.get("seat_layout")
            return Theatre(name, rows, cols, seat_layout=seat_layout)

        theatre_cls = cls._registry.get(theatre_type)
        if not theatre_cls:
            raise ValueError(
                f"Unknown theatre type '{theatre_type}'. "
                f"Available: {list(cls._registry.keys()) + ['custom']}"
            )
        return theatre_cls(name)

    @classmethod
    def register(cls, theatre_type: str, theatre_cls: type):
        """Register a new theatre type at runtime."""
        cls._registry[theatre_type] = theatre_cls

class BookingManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, theatre=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.theatres = {}
        return cls._instance

    def add_theatre(self, name: str, theatre: "Theatre"):
        """Register a theatre by name."""
        self.theatres[name] = theatre

    def get_theatre(self, name: str) -> "Theatre | None":
        return self.theatres.get(name)

    def book_multiple_seats(self, user_id, theatre_name: str, seat_requests):
        """Atomic booking with per-seat locks for a named theatre."""
        theatre = self.get_theatre(theatre_name)
        if not theatre:
            print(f"User {user_id} failed: Theatre '{theatre_name}' not found")
            return None

        seats_to_book = []
        acquired_locks = []

        try:
            # Acquire locks in a consistent order to avoid deadlocks
            sorted_requests = sorted(seat_requests)
            for row, col in sorted_requests:
                seat = theatre.get_seat(row, col)
                if not seat:
                    raise Exception(f"Invalid seat ({row}, {col})")
                seat.lock.acquire()
                acquired_locks.append(seat.lock)
                if seat.is_booked:
                    raise Exception(f"Seat ({row}, {col}) already booked")
                seats_to_book.append(seat)

            # All seats available → book them
            for seat in seats_to_book:
                seat.is_booked = True
            booked_list = [(s.row, s.col) for s in seats_to_book]
            print(f"User {user_id} successfully booked seats: {booked_list}")
            return booked_list

        except Exception as e:
            print(f"User {user_id} failed: {e}")
            return None

        finally:
            # Release all acquired locks
            for lock in acquired_locks:
                lock.release()

# Example usage
def user_booking(user_id, theatre_name, seat_requests):
    manager = BookingManager()
    manager.book_multiple_seats(user_id, theatre_name, seat_requests)

if __name__ == "__main__":
    manager = BookingManager()

    # Use TheatreFactory to create different theatre types
    imax = TheatreFactory.create("imax", "IMAX Screen 1")
    standard = TheatreFactory.create("standard", "Standard Hall A")
    mini = TheatreFactory.create("mini", "Mini Room 3")
    custom = TheatreFactory.create("custom", "Custom Arena", rows=10, cols=15)

    manager.add_theatre(imax.name, imax)
    manager.add_theatre(standard.name, standard)
    manager.add_theatre(mini.name, mini)
    manager.add_theatre(custom.name, custom)

    threads = []
    requests = [
        ("IMAX Screen 1",    [(0,0), (0,1)]),   # User 0
        ("IMAX Screen 1",    [(0,1), (0,2)]),   # User 1 (conflict with User 0)
        ("Standard Hall A",  [(1,1), (1,2)]),   # User 2
        ("Mini Room 3",      [(2,4), (2,3)]),   # User 3
    ]
    for i, (theatre_name, req) in enumerate(requests):
        t = threading.Thread(target=user_booking, args=(i, theatre_name, req))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
