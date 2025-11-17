#!/usr/bin/env python3
"""
Benchmark harness for comparing CRUD operations across two servers.

Usage:
  python tools/benchmark.py --rust http://127.0.0.1:3000 --flask http://127.0.0.1:5000 --runs 100 --concurrency 10

What it does:
- Runs a set of scenarios (sequential creates, concurrent creates, reads, updates, deletes)
- Measures per-request client-side latency and records timestamps
- Fetches server-side metrics endpoints if available (/api/metrics)
- Produces CSV output with per-request records and summary JSON

Notes:
- Assumes both servers expose REST endpoints compatible with this project:
  /api/create (POST {name,description})
  /api/database (GET)
  /api/read/:id (GET)
  /api/update/:id (PUT {name,description})
  /api/delete/:id (DELETE)
- If the Flask app uses different paths or payloads, pass custom endpoints via flags or edit the script.
"""
import argparse
import asyncio
import aiohttp
import time
import csv
import json
import os
from collections import defaultdict

OUTPUT_DIR = "bench_output"

async def measured_fetch(session, method, url, **kwargs):
    t0 = time.perf_counter()
    async with session.request(method, url, **kwargs) as resp:
        try:
            body = await resp.text()
        except Exception:
            body = ''
        t1 = time.perf_counter()
        return {
            'status': resp.status,
            'text': body,
            'latency_ms': (t1 - t0) * 1000.0
        }

async def create_item(session, base_url, name, desc):
    url = base_url.rstrip('/') + '/api/create'
    return await measured_fetch(session, 'POST', url, json={'name': name, 'description': desc})

async def read_item(session, base_url, id_):
    url = base_url.rstrip('/') + f'/api/read/{id_}'
    return await measured_fetch(session, 'GET', url)

async def list_db(session, base_url):
    url = base_url.rstrip('/') + '/api/database'
    return await measured_fetch(session, 'GET', url)

async def update_item(session, base_url, id_, name, desc):
    url = base_url.rstrip('/') + f'/api/update/{id_}'
    return await measured_fetch(session, 'PUT', url, json={'name': name, 'description': desc})

async def delete_item(session, base_url, id_):
    url = base_url.rstrip('/') + f'/api/delete/{id_}'
    return await measured_fetch(session, 'DELETE', url)

async def fetch_metrics(session, base_url):
    url = base_url.rstrip('/') + '/api/metrics'
    try:
        return await measured_fetch(session, 'GET', url)
    except Exception:
        return None

async def run_sequence(base_url, name_prefix, count, concurrency, tag, writer_rows):
    conn = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=conn) as session:
        # sequential create
        ids = []
        for i in range(count):
            res = await create_item(session, base_url, f"{name_prefix}-{i}", "bench-desc")
            writer_rows.append({
                'server': base_url,
                'scenario': tag,
                'operation': 'CREATE',
                'index': i,
                'status': res['status'],
                'latency_ms': res['latency_ms'],
                'timestamp': time.time()
            })
            # attempt to read back database to discover id (if server returns nothing, caller may need to inspect /api/database)
            # we'll call /api/database and pick last id
            db = await list_db(session, base_url)
            try:
                js = json.loads(db['text'])
                items = js.get('items', [])
                if items:
                    ids.append(items[-1]['id'])
            except Exception:
                pass

        # concurrent reads of all discovered ids
        if ids:
            tasks = [read_item(session, base_url, id_) for id_ in ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    writer_rows.append({'server': base_url, 'scenario': tag, 'operation': 'READ', 'index': i, 'status': 'err', 'latency_ms': None, 'timestamp': time.time()})
                else:
                    writer_rows.append({'server': base_url, 'scenario': tag, 'operation': 'READ', 'index': i, 'status': r['status'], 'latency_ms': r['latency_ms'], 'timestamp': time.time()})

        # concurrent updates (if ids)
        if ids:
            tasks = [update_item(session, base_url, id_, f"{name_prefix}-u-{i}", "updated") for i, id_ in enumerate(ids)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    writer_rows.append({'server': base_url, 'scenario': tag, 'operation': 'UPDATE', 'index': i, 'status': 'err', 'latency_ms': None, 'timestamp': time.time()})
                else:
                    writer_rows.append({'server': base_url, 'scenario': tag, 'operation': 'UPDATE', 'index': i, 'status': r['status'], 'latency_ms': r['latency_ms'], 'timestamp': time.time()})

        # deletes
        if ids:
            tasks = [delete_item(session, base_url, id_) for id_ in ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    writer_rows.append({'server': base_url, 'scenario': tag, 'operation': 'DELETE', 'index': i, 'status': 'err', 'latency_ms': None, 'timestamp': time.time()})
                else:
                    writer_rows.append({'server': base_url, 'scenario': tag, 'operation': 'DELETE', 'index': i, 'status': r['status'], 'latency_ms': r['latency_ms'], 'timestamp': time.time()})

async def run_concurrent_creates(base_url, total, concurrency, tag, writer_rows):
    conn = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=conn) as session:
        sem = asyncio.Semaphore(concurrency)
        async def do_create(i):
            async with sem:
                res = await create_item(session, base_url, f"concurrent-{i}", "bench")
                writer_rows.append({'server': base_url, 'scenario': tag, 'operation':'CREATE_CONC','index':i,'status':res['status'],'latency_ms':res['latency_ms'],'timestamp':time.time()})
        tasks = [do_create(i) for i in range(total)]
        await asyncio.gather(*tasks)

def write_csv(rows, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, 'requests.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['server','scenario','operation','index','status','latency_ms','timestamp']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('Wrote', csv_path)
    return csv_path

async def main_async(args):
    rows = []
    # basic scenarios for each server
    for server_url in [args.rust, args.flask]:
        if not server_url:
            continue
        # simple sequential sequence: create 10 -> read/update/delete
        await run_sequence(server_url, 'seq', 10, args.concurrency, 'sequence', rows)
        # concurrent creates
        await run_concurrent_creates(server_url, args.runs, args.concurrency, 'concurrent_create', rows)
        # snapshot server metrics if available
        async with aiohttp.ClientSession() as session:
            m = await fetch_metrics(session, server_url)
            if m and m.get('status') != 0:
                # store metrics JSON if possible
                try:
                    metrics_json = json.loads(m['text'])
                    fn = os.path.join(OUTPUT_DIR, server_url.replace(':','_').replace('/','_') + '_metrics.json')
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    with open(fn, 'w', encoding='utf-8') as fh:
                        json.dump(metrics_json, fh, indent=2)
                    print('Saved server metrics to', fn)
                except Exception:
                    pass

    csv = write_csv(rows, OUTPUT_DIR)
    summary = {'rows': len(rows), 'output_csv': csv}
    with open(os.path.join(OUTPUT_DIR, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('Summary written to', os.path.join(OUTPUT_DIR, 'summary.json'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rust', help='Rust server base URL (e.g. http://127.0.0.1:3000)')
    parser.add_argument('--flask', help='Flask server base URL (e.g. http://127.0.0.1:5000)')
    parser.add_argument('--runs', type=int, default=50, help='Number of concurrent creates to run')
    parser.add_argument('--concurrency', type=int, default=10, help='Concurrency level')
    args = parser.parse_args()

    asyncio.run(main_async(args))

if __name__ == '__main__':
    main()
