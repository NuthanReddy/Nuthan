"""
TCP Load Balancer — Socket Simulation
=====================================
A layer-4 (TCP) load balancer that accepts client connections and proxies each
one to a backend chosen from a pool. It demonstrates the core mechanics a real
LB (HAProxy, NGINX stream, AWS NLB) provides:

  - **Backend pool** — multiple upstream servers, not a single hardcoded host.
  - **Selection strategy** — pluggable ``round_robin`` (even spread) or
    ``least_connections`` (send to the least busy backend).
  - **Concurrency** — each client is handled on its own thread, so slow clients
    don't block others (the original serial version could handle one at a time).
  - **Bidirectional proxying** — bytes are relayed in *both* directions via
    ``select`` until either side closes, so the client actually receives the
    backend's response (the original forwarded a single ``recv`` and dropped the
    reply).
  - **Health awareness** — a backend that fails to connect is marked unhealthy
    and skipped; the next backend is tried.

This is intentionally dependency-free (stdlib ``socket``/``select``/``threading``)
and self-contained: the demo starts throwaway echo backends, routes traffic
through the LB, and reports the resulting distribution.

Run:
    uv run --no-project python SystemDesign\\Utils\\LoadBalancerSocket.py
"""

from __future__ import annotations

import select
import socket
import threading
import time
from dataclasses import dataclass, field
from itertools import count
from typing import Optional


@dataclass
class Backend:
    """A single upstream server and its live stats."""

    host: str
    port: int
    healthy: bool = True
    active_connections: int = 0
    total_handled: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def address(self) -> tuple[str, int]:
        return (self.host, self.port)

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


class LoadBalancer:
    """A threaded TCP load balancer over a pool of backends.

    Args:
        backends: List of ``(host, port)`` upstreams.
        strategy: ``"round_robin"`` or ``"least_connections"``.
        listen_host: Interface to bind.
        listen_port: Port to bind (0 = OS-assigned; read ``.port`` after start).
        connect_timeout: Seconds to wait when dialing a backend.
    """

    def __init__(
        self,
        backends: list[tuple[str, int]],
        strategy: str = "round_robin",
        listen_host: str = "localhost",
        listen_port: int = 0,
        connect_timeout: float = 2.0,
    ) -> None:
        if not backends:
            raise ValueError("at least one backend is required")
        if strategy not in ("round_robin", "least_connections"):
            raise ValueError(f"unknown strategy: {strategy}")

        self.backends = [Backend(host, port) for host, port in backends]
        self.strategy = strategy
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.connect_timeout = connect_timeout

        self._rr_counter = count()
        self._select_lock = threading.Lock()
        self._listen_sock: Optional[socket.socket] = None
        self._running = threading.Event()
        self._accept_thread: Optional[threading.Thread] = None
        self._client_threads: list[threading.Thread] = []

    # -- backend selection --------------------------------------------------

    def _healthy_backends(self) -> list[Backend]:
        healthy = [b for b in self.backends if b.healthy]
        # If everything is marked unhealthy, optimistically reset and retry —
        # backends may have recovered.
        if not healthy:
            for b in self.backends:
                b.healthy = True
            healthy = list(self.backends)
        return healthy

    def _choose_backend(self) -> Backend:
        """Pick a backend according to the configured strategy (thread-safe)."""
        with self._select_lock:
            candidates = self._healthy_backends()
            if self.strategy == "least_connections":
                return min(
                    candidates,
                    key=lambda b: (b.active_connections, b.total_handled),
                )
            # round_robin
            idx = next(self._rr_counter) % len(candidates)
            return candidates[idx]

    # -- lifecycle ----------------------------------------------------------

    @property
    def port(self) -> int:
        """The actual bound port (useful when listen_port was 0)."""
        if self._listen_sock is None:
            return self.listen_port
        return self._listen_sock.getsockname()[1]

    def start(self) -> None:
        """Bind, listen, and begin accepting connections on a background thread."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.listen_host, self.listen_port))
        sock.listen(128)
        sock.settimeout(0.5)  # so the accept loop can observe shutdown
        self._listen_sock = sock
        self._running.set()
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def stop(self) -> None:
        """Stop accepting and close the listening socket."""
        self._running.clear()
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2.0)
        if self._listen_sock is not None:
            self._listen_sock.close()
            self._listen_sock = None

    def _accept_loop(self) -> None:
        assert self._listen_sock is not None
        while self._running.is_set():
            try:
                client_sock, client_addr = self._listen_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = threading.Thread(
                target=self._handle_client,
                args=(client_sock, client_addr),
                daemon=True,
            )
            t.start()
            self._client_threads.append(t)

    # -- request handling ---------------------------------------------------

    def _handle_client(self, client_sock: socket.socket, client_addr) -> None:
        """Connect to a chosen backend and relay bytes both ways."""
        backend, server_sock = self._connect_to_backend()
        if backend is None or server_sock is None:
            client_sock.close()
            return

        with backend._lock:
            backend.active_connections += 1
        try:
            self._proxy(client_sock, server_sock)
        finally:
            with backend._lock:
                backend.active_connections -= 1
                backend.total_handled += 1
            client_sock.close()
            server_sock.close()

    def _connect_to_backend(
        self,
    ) -> tuple[Optional[Backend], Optional[socket.socket]]:
        """Try backends (respecting strategy) until one connects."""
        attempts = 0
        max_attempts = len(self.backends)
        while attempts < max_attempts:
            backend = self._choose_backend()
            attempts += 1
            try:
                server_sock = socket.create_connection(
                    backend.address, timeout=self.connect_timeout
                )
                return backend, server_sock
            except OSError:
                backend.healthy = False  # mark down, try the next one
        return None, None

    @staticmethod
    def _proxy(client_sock: socket.socket, server_sock: socket.socket) -> None:
        """Full-duplex relay until either side closes (EOF)."""
        client_sock.setblocking(False)
        server_sock.setblocking(False)
        peers = {client_sock: server_sock, server_sock: client_sock}
        open_socks = [client_sock, server_sock]
        while open_socks:
            readable, _, errored = select.select(open_socks, [], open_socks, 5.0)
            if errored:
                break
            if not readable:
                break  # idle timeout — tear the connection down
            for s in readable:
                try:
                    data = s.recv(4096)
                except OSError:
                    return
                if not data:
                    return  # peer closed -> done
                try:
                    peers[s].sendall(data)
                except OSError:
                    return

    def stats(self) -> dict[str, dict[str, int | bool]]:
        return {
            str(b): {
                "healthy": b.healthy,
                "active_connections": b.active_connections,
                "total_handled": b.total_handled,
            }
            for b in self.backends
        }


# ---------------------------------------------------------------------------
# Self-contained demo: throwaway echo backends + LB + a few clients
# ---------------------------------------------------------------------------

class _EchoBackend:
    """A tiny TCP server that replies '<name>: <request>' then closes."""

    def __init__(self, name: str, host: str = "localhost") -> None:
        self.name = name
        self.host = host
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, 0))
        self._sock.listen(16)
        self._sock.settimeout(0.5)
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return self._sock.getsockname()[1]

    def start(self) -> None:
        self._running.set()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while self._running.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    data = conn.recv(4096)
                    if data:
                        conn.sendall(f"{self.name}: ".encode() + data)
                except OSError:
                    pass

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._sock.close()


def _demo() -> None:
    print("=" * 60)
    print("  TCP Load Balancer demo (round-robin over 3 backends)")
    print("=" * 60)

    backends = [_EchoBackend(f"backend-{i}") for i in range(1, 4)]
    for b in backends:
        b.start()

    lb = LoadBalancer(
        backends=[(b.host, b.port) for b in backends],
        strategy="round_robin",
    )
    lb.start()
    time.sleep(0.2)
    print(f"  LB listening on localhost:{lb.port}")
    print(f"  Backends: {[f'{b.host}:{b.port}' for b in backends]}\n")

    responders: list[str] = []
    for i in range(9):
        with socket.create_connection(("localhost", lb.port), timeout=2.0) as c:
            c.sendall(f"request-{i}".encode())
            reply = c.recv(4096).decode()
        who = reply.split(":")[0]
        responders.append(who)
        print(f"  request-{i} -> {reply}")

    print("\n  Distribution across backends:")
    for b in backends:
        n = responders.count(b.name)
        print(f"    {b.name}: {n} requests")

    print("\n  LB stats:")
    for addr, s in lb.stats().items():
        print(f"    {addr}: handled={s['total_handled']} healthy={s['healthy']}")

    lb.stop()
    for b in backends:
        b.stop()
    print("\n  [DONE] Load balancer and backends shut down cleanly.\n")


if __name__ == "__main__":
    _demo()
