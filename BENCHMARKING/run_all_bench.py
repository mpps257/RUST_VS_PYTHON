import subprocess
import json
import os

# Configuration
implementations = {
    "flask": {
        "base_url": "http://localhost:5000",
        "endpoints": {
            "create": {"method": "POST", "path": "/create", "data": {"name": "bench_item", "description": "desc"}},
            "read": {"method": "GET", "path": "/read"},
            "update": {"method": "PUT", "path": "/update/1", "data": {"name": "bench_item_upd", "description": "desc_upd"}},
            "delete": {"method": "DELETE", "path": "/delete/1"},
            "bulk_create": {"method": "POST", "path": "/bulk_create"},
        }
    },
    "rust": {
        "base_url": "http://localhost:8000/api",
        "endpoints": {
            "create": {"method": "POST", "path": "/create", "data": {"name": "bench_item", "description": "desc"}},
            "read": {"method": "GET", "path": "/read"},
            "update": {"method": "PUT", "path": "/update/1", "data": {"name": "bench_item_upd", "description": "desc_upd"}},
            "delete": {"method": "DELETE", "path": "/delete/1"},
            "bulk_create": {"method": "POST", "path": "/bulk_create"},
        }
    }
}

bulk_sizes = [100, 1000, 10000, 100000, 1000000]
requests_per_endpoint = 100  # For non-bulk endpoints

def run_bench(method, url, data, headers, requests, output):
    cmd = [
        "python", "bench.py",
        "--method", method,
        "--url", url,
        "--requests", str(requests),
        "--concurrency", "10",
        "--output", output
    ]
    if data is not None:
        cmd += ["--data", data]
    if headers:
        for h in headers:
            cmd += ["--headers", h]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    for impl, config in implementations.items():
        base_url = config["base_url"]
        for ep_name, ep in config["endpoints"].items():
            if ep_name == "bulk_create":
                for size in bulk_sizes:
                    payload = [{"name": f"bulk_{i}", "description": "desc"} for i in range(size)]
                    data = json.dumps(payload)
                    url = base_url + ep["path"]
                    output = f"{impl}_bulk_create_{size}.csv"
                    run_bench(
                        ep["method"], url, data,
                        ["Content-Type:application/json"], 1, output
                    )
            else:
                url = base_url + ep["path"]
                data = json.dumps(ep["data"]) if "data" in ep else None
                output = f"{impl}_{ep_name}_{requests_per_endpoint}.csv"
                headers = ["Content-Type:application/json"] if data else []
                run_bench(
                    ep["method"], url, data, headers, requests_per_endpoint, output
                )

if __name__ == "__main__":
    main()