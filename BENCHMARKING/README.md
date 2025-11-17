Benchmarks README

Purpose
- Provide a simple, reproducible way to benchmark CRUD endpoints for both the Flask and Rust implementations.


Install

```powershell
pip install -r requirements.txt  # optional if you want a file; otherwise: pip install requests psutil
```

Quick Start

1) Start the Flask app
   - Open `\flask_crud_metrics`
   - Create an environemnt and install requirements from `requirements.txt`
   - Start the server (common):

```powershell
cd ...\flask_crud_metrics
conda activate <enovironment_name>
pip install -r requirements.txt
python app.py
```

2) Start the Rust server
   - Open `...\leptos_full_crud_metrics\server`
   - Build & run: 

```powershell
cd ...\leptos_full_crud_metrics\server
cargo run --release
```

Check the server logs or `src/main.rs` to confirm the port (common ports: 3000 or 8000).

3) Use the provided `bench.py` to run a test

```powershell
cd ...\benchmarks
python bench.py --method POST --url http://localhost:5000/items --data '{"name":"bob"}' --concurrency 10 --requests 200 --output flask_post.csv
python bench.py --method GET  --url http://localhost:5000/items --concurrency 50 --requests 1000 --output flask_get.csv
```
