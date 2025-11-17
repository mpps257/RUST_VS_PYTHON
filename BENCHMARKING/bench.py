#!/usr/bin/env python3
"""
Simple HTTP benchmarker for CRUD endpoints.
Writes per-request timings to CSV and prints summary (p50/p95/p99, mean, throughput).
Optional PID monitoring records CPU/memory of the server process while the load test runs.

Usage examples:
  python bench.py --method POST --url http://localhost:5000/items --data '{"name":"x"}' --concurrency 10 --requests 200 --output results.csv
  python bench.py --method GET --url http://localhost:5000/items --concurrency 50 --requests 1000

Requires: requests, psutil (psutil only if --monitor-pid used)
"""

from __future__ import annotations
import argparse
import csv
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json as _json
try:
    import requests
except Exception as e:
    print("Missing dependency: requests. Install with: pip install requests")
    raise


def percentile(data, p: float):
    if not data:
        return None
    data = sorted(data)
    k = (len(data)-1) * (p/100.0)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[-1]
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return d0 + d1


def worker(session: requests.Session, method: str, url: str, data, headers, timeout):
    start = time.perf_counter()
    try:
        if method.upper() == 'GET':
            r = session.get(url, headers=headers, timeout=timeout)
        elif method.upper() == 'POST':
            r = session.post(url, data=data, headers=headers, timeout=timeout)
        elif method.upper() == 'PUT':
            r = session.put(url, data=data, headers=headers, timeout=timeout)
        elif method.upper() == 'DELETE':
            r = session.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
        elapsed = (time.perf_counter() - start) * 1000.0
        return True, elapsed, r.status_code
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        return False, elapsed, None


def worker_json(session: requests.Session, method: str, url: str, json_payload, headers, timeout):
    """Same as worker but sends a `json=` payload to requests (keeps return tuple consistent)."""
    start = time.perf_counter()
    try:
        r = session.request(method, url, json=json_payload, headers=headers, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000.0
        return True, elapsed, r.status_code
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000.0
        return False, elapsed, None


class ResourceMonitor(threading.Thread):
    def __init__(self, pid: int | None, interval: float = 0.5):
        super().__init__()
        self.pid = pid
        self.interval = interval
        # CHANGE: Renamed _stop to _should_stop to avoid collision with threading.Thread._stop()
        self._should_stop = threading.Event()
        self.samples = []
        self._psutil = None
        if pid is not None:
            try:
                import psutil
                self._psutil = psutil
                self.proc = psutil.Process(pid)
            except Exception:
                print("Warning: psutil is required for PID monitoring. Install with: pip install psutil")
                self.pid = None
                self.proc = None

    def run(self):
        if self.pid is None:
            return
        while not self._should_stop.is_set():
            try:
                cpu = self.proc.cpu_percent(interval=None)
                mem = self.proc.memory_info().rss
                ts = time.time()
                self.samples.append((ts, cpu, mem))
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self._should_stop.set()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--method', required=True)
    p.add_argument('--url', required=True)
    p.add_argument('--concurrency', '-c', type=int, default=10)
    p.add_argument('--requests', '-n', type=int, default=100)
    p.add_argument('--data', '-d')
    p.add_argument('--headers', '-H', nargs='*', help='Header values KEY:VALUE')
    p.add_argument('--timeout', type=float, default=10.0)
    p.add_argument('--output', '-o', default=None, help='CSV output file path')
    p.add_argument('--monitor-pid', type=int, default=None, help='Server PID to monitor resource usage')
    p.add_argument('--include-client-latency', action='store_true', help='Measure a short client-side latency probe and send as x-client-latency-ms header')
    # CHANGE: Add diagnostic flag to print the first request URL/data for debugging
    p.add_argument('--verbose-first-request', action='store_true', help='Print the URL and data of the first request (for debugging)')
    args = p.parse_args()

    headers = {}
    if args.headers:
        for h in args.headers:
            if ':' in h:
                k, v = h.split(':', 1)
                headers[k.strip()] = v.strip()

    # If requested, perform a short probe to measure client-side latency
    # and include it as the header `x-client-latency-ms` for server-side metrics.
    # This avoids per-request measurement overhead but gives the server a
    # consistent client-latency value to record (used by the Rust server).
    if args.include_client_latency:
        try:
            probe_start = time.perf_counter()
            requests.head(args.url, timeout=0.5)
            probe_ms = (time.perf_counter() - probe_start) * 1000.0
        except Exception:
            probe_ms = 0.0
        headers.setdefault('x-client-latency-ms', f"{probe_ms:.2f}")

    total = args.requests
    concurrency = max(1, args.concurrency)
    method = args.method.upper()
    url = args.url

    # CHANGE: Print diagnostic info if verbose flag is set (helps debug URL/data issues)
    if args.verbose_first_request:
        print(f"[DIAGNOSTIC] Method: {method}")
        print(f"[DIAGNOSTIC] URL: {url}")
        print(f"[DIAGNOSTIC] Data: {args.data}")
        print(f"[DIAGNOSTIC] Headers: {headers}")
        print(f"[DIAGNOSTIC] Concurrency: {concurrency}, Requests: {total}\n")

    monitor = ResourceMonitor(args.monitor_pid)
    if args.monitor_pid:
        monitor.start()

    results = []
    start_all = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = []
        session_local = threading.local()

        # Prepare parsed JSON payload if Content-Type indicates JSON.
        # CHANGE: auto-detect JSON and parse once to pass via `json=` to requests.
        parsed_json = None
        if args.data and any(k.lower() == 'content-type' and 'application/json' in v.lower() for k, v in headers.items()):
            try:
                parsed_json = _json.loads(args.data)
            except Exception:
                parsed_json = None

        def submit_one(i):
            if not hasattr(session_local, 'session'):
                session_local.session = requests.Session()
            # If parsed_json is present, use worker_json so return values stay consistent
            if parsed_json is None:
                return ex.submit(worker, session_local.session, method, url, args.data, headers, args.timeout)
            else:
                return ex.submit(worker_json, session_local.session, method, url, parsed_json, headers, args.timeout)

        for i in range(total):
            futures.append(submit_one(i))

        completed = 0
        for fut in as_completed(futures):
            ok, elapsed, status = fut.result()
            results.append((time.time(), ok, elapsed, status))
            completed += 1
            if completed % 100 == 0:
                print(f"Completed {completed}/{total}")

    duration = time.perf_counter() - start_all
    if args.monitor_pid:
        monitor.stop()
        # CHANGE: Increased join timeout to 2.0s to allow thread to exit cleanly
        monitor.join(timeout=2.0)

    latencies = [r[2] for r in results if r[1]]
    successes = sum(1 for r in results if r[1])
    failures = len(results) - successes

    def ms(x):
        return f"{x:.2f} ms" if x is not None else 'n/a'

    print('\nSummary:')
    print(f"Total requests: {len(results)}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    if latencies:
        print(f"Mean: {sum(latencies)/len(latencies):.2f} ms")
        print(f"p50: {percentile(latencies,50):.2f} ms")
        print(f"p95: {percentile(latencies,95):.2f} ms")
        print(f"p99: {percentile(latencies,99):.2f} ms")
    print(f"Total duration: {duration:.2f} s")
    print(f"Throughput: {len(results)/duration:.2f} req/s")

    if args.output:
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['timestamp','success','latency_ms','status_code'])
            for t, ok, latency, status in results:
                w.writerow([datetime.fromtimestamp(t).isoformat(), int(ok), f"{latency:.3f}", status or ''])
        print(f"Wrote per-request CSV to {args.output}")

    if args.monitor_pid and monitor.samples:
        monfile = (args.output or 'results') + '.resources.csv'
        with open(monfile, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['timestamp','cpu_percent','rss_bytes'])
            for ts, cpu, mem in monitor.samples:
                w.writerow([datetime.fromtimestamp(ts).isoformat(), cpu, mem])
        print(f"Wrote resource samples to {monfile}")

if __name__ == '__main__':
    main()
