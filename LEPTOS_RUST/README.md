# Leptos + Axum CRUD with Metrics (Timestamped CSV)

This project is a scaffold demonstrating a Leptos frontend (client-side) and an Axum backend that:
- Implements CRUD endpoints for items (in-memory).
- Logs metrics for operations with a timestamp.
- Appends metrics to `output_metrics.csv` with headers:
  `timestamp,operation,execution_time_ms,memory_mb,network_latency_ms`.
- Records a `READ (Description)` metric when the frontend requests `/api/read/:id` (used when "Show Description" is clicked).

## Project layout

- `Cargo.toml` - workspace file
- `server/` - Axum backend
  - `src/main.rs` - server implementation, API routes, CSV logging
- `leptos_app/` - Leptos frontend scaffold (WASM)
  - `Cargo.toml`, `src/lib.rs`, `src/main_client.rs`
- `static/index.html` - fallback static UI that can be used without building WASM

## Build & Run

### Requirements
- Rust toolchain (stable)
- For the Leptos frontend (WASM) build: `cargo install cargo-leptos` (optional) or use `trunk`.
- If you only want to run the backend and use the fallback UI, you don't need to build the WASM.

### Run backend (quick)
```bash
cd server
cargo run --release
```
