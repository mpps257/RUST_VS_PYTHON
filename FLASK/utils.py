import time
import psutil
import requests
import urllib.parse
import socket


def measure_latency(url, timeout: float = 0.2):
    """Measure network latency (in ms) for a simple GET request.

    IMPORTANT: avoid issuing a blocking HTTP request to the server's own
    endpoint (loopback/localhost). Calling `requests.get()` against the
    same server from inside a request handler causes a nested request that
    can significantly inflate latency (or deadlock) when the server is
    single-threaded. If the URL resolves to a loopback/localhost address
    we return 0.0 to indicate "not measured".
    """
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            return 0.0

        # Avoid self-requests to loopback/localhost addresses
        if host in ("localhost", "127.0.0.1", "::1"):
            return 0.0

        # Try to resolve hostname and treat loopback addresses as local
        try:
            addr = socket.gethostbyname(host)
            if addr.startswith("127.") or addr == "::1":
                return 0.0
        except Exception:
            # If resolution fails, fall back to attempting the request
            pass

        start = time.time()
        try:
            requests.get(url, timeout=timeout)
        except Exception:
            # Ignore network errors — we only want a best-effort latency
            pass
        end = time.time()
        return round((end - start) * 1000, 2)
    except Exception:
        return 0.0


def current_memory_mb():
    """Return the current memory (MB) used by this process."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def measure_execution_metrics(func):
    """
    Measure execution time (ms) and memory delta (MB) for a given function.
    Returns (result, exec_time_ms, memory_used_mb)
    """
    before_mem = current_memory_mb()
    start_time = time.time()

    result = func()  # execute the function

    end_time = time.time()
    after_mem = current_memory_mb()

    exec_time_ms = round((end_time - start_time) * 1000, 2)
    memory_used_mb = round(max(after_mem - before_mem, 0), 2)  # delta only

    return result, exec_time_ms, memory_used_mb
