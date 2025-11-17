use axum::{routing::{get, post, put, delete}, Router, extract::Path, Json, http::StatusCode};
use axum::http::HeaderMap;
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::{net::SocketAddr, sync::Arc, fs};
use uuid::Uuid;
use csv::WriterBuilder;
use chrono::Local;
use rusqlite::{params, Connection, OptionalExtension};
use sysinfo::{System, SystemExt, ProcessExt};

#[derive(Clone, Serialize, Deserialize, Debug)]
struct Item {
    id: String,
    name: String,
    description: Option<String>,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
struct Metric {
    timestamp: String,
    operation: String,
    execution_time_ms: f64,
    memory_mb: f64,
    network_latency_ms: f64,
}

type Metrics = Arc<Mutex<Vec<Metric>>>;

const CSV_FILE: &str = "output_metrics.csv";

fn append_metric_to_csv(metric: &Metric) -> Result<(), std::io::Error> {
    let file_exists = std::path::Path::new(CSV_FILE).exists();
    let file = fs::OpenOptions::new().create(true).append(true).open(CSV_FILE)?;
    let mut wtr = WriterBuilder::new().has_headers(!file_exists).from_writer(file);
    wtr.serialize(metric)?;
    wtr.flush()?;
    Ok(())
}

fn sample_proc_memory_mb() -> f64 {
    let mut sys = System::new_all();
    sys.refresh_processes();
    let current_pid_str = std::process::id().to_string();
    sys.processes()
        .values()
        .find(|p| p.pid().to_string() == current_pid_str)
        .map(|p| p.memory() as f64 / 1024.0)
        .unwrap_or(0.0)
}

#[tokio::main]
async fn main() {
    let metrics: Metrics = Arc::new(Mutex::new(Vec::new()));

    // Ensure database file and table exist
    let db_path = "db.sqlite";
    let mut created = false;
    if !std::path::Path::new(db_path).exists() {
        created = true;
    }
    let conn = Connection::open(db_path).expect("failed to open sqlite db");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT
        )",
        [],
    ).expect("failed to create items table");

    // add a sample item only if DB was just created
    if created {
        let id = Uuid::new_v4().to_string();
        let _ = conn.execute(
            "INSERT INTO items (id, name, description) VALUES (?1, ?2, ?3)",
            params![id.clone(), "Example Item", Some("This is an example description")],
        );
    }
    drop(conn);

    let app = Router::new()
        .route("/api/database", get({
            move || {
                async move {
                    // open connection per-request
                    let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let mut stmt = conn.prepare("SELECT id, name, description FROM items").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let items_iter = stmt.query_map([], |row| {
                        Ok(Item {
                            id: row.get(0)?,
                            name: row.get(1)?,
                            description: row.get(2).ok(),
                        })
                    }).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let mut items_vec = Vec::new();
                    for it in items_iter {
                        if let Ok(i) = it { items_vec.push(i); }
                    }
                    let total = items_vec.len();
                    let db_info = serde_json::json!({
                        "total_items": total,
                        "items": items_vec,
                        "database_uri": "sqlite://db.sqlite"
                    });
                    Ok::<_, (StatusCode, &'static str)>(Json(db_info))
                }
            }
        }))
        .route("/api/metrics", get({
            let metrics = metrics.clone();
            move || {
                let metrics = metrics.clone();
                async move {
                    let m = metrics.lock().clone();
                    Ok::<_, (StatusCode, &'static str)>(Json(m))
                }
            }
        }))
        .route("/api/metrics_ingest", post({
            let metrics = metrics.clone();
            move |Json(payload): Json<serde_json::Value>| {
                let metrics = metrics.clone();
                async move {
                    let op = payload.get("operation").and_then(|v| v.as_str()).unwrap_or("UNKNOWN").to_string();
                    let net = payload.get("network_latency_ms").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let exec = payload.get("execution_time_ms").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let mem = payload.get("memory_mb").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let metric = Metric {
                        timestamp: Local::now().to_rfc3339(),
                        operation: op,
                        execution_time_ms: exec,
                        memory_mb: mem,
                        network_latency_ms: net,
                    };
                    metrics.lock().push(metric.clone());
                    let _ = append_metric_to_csv(&metric);
                    Ok::<_, (StatusCode, &'static str)>(StatusCode::CREATED)
                }
            }
        }))
        .route("/api/create", post({
            let metrics = metrics.clone();
            move |headers: HeaderMap, Json(payload): Json<serde_json::Value>| {
                let metrics = metrics.clone();
                async move {
                    let name = payload.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let description = payload.get("description").and_then(|v| v.as_str()).map(|s| s.to_string());
                    let id = Uuid::new_v4().to_string();

                    // sample memory before the operation
                    let mem_before = sample_proc_memory_mb();
                    let start = std::time::Instant::now();
                    // perform DB insert
                    let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let _ = conn.execute(
                        "INSERT INTO items (id, name, description) VALUES (?1, ?2, ?3)",
                        params![id.clone(), name.clone(), description.clone()],
                    );
                    let exec = start.elapsed().as_secs_f64() * 1000.0;

                    let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);

                    let mem_after = sample_proc_memory_mb();
                    let mem_mb = mem_after - mem_before; // delta memory used by this operation (MB)

                    let metric = Metric {
                        timestamp: Local::now().to_rfc3339(),
                        operation: "CREATE".to_string(),
                        execution_time_ms: exec,
                        memory_mb: mem_mb,
                        network_latency_ms: client_latency,
                    };
                    metrics.lock().push(metric.clone());
                    let _ = append_metric_to_csv(&metric);
                    Ok::<_, (StatusCode, &'static str)>(StatusCode::CREATED)
                }
            }
        }))
        .route("/api/read", get({
            let metrics = metrics.clone();
            move |headers: HeaderMap| {
                let metrics = metrics.clone();
                async move {
                    // sample memory before the read-all operation
                    let mem_before = sample_proc_memory_mb();
                    let start = std::time::Instant::now();
                    let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let mut stmt = conn.prepare("SELECT id, name, description FROM items").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let items_iter = stmt.query_map([], |row| {
                        Ok(Item {
                            id: row.get(0)?,
                            name: row.get(1)?,
                            description: row.get(2).ok(),
                        })
                    }).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let mut items_vec = Vec::new();
                    for it in items_iter {
                        if let Ok(i) = it { items_vec.push(i); }
                    }
                    let exec = start.elapsed().as_secs_f64() * 1000.0;

                    let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                    let mem_after = sample_proc_memory_mb();
                    let mem_mb = mem_after - mem_before;

                    let metric = Metric {
                        timestamp: Local::now().to_rfc3339(),
                        operation: "READ_ALL".to_string(),
                        execution_time_ms: exec,
                        memory_mb: mem_mb,
                        network_latency_ms: client_latency,
                    };
                    metrics.lock().push(metric.clone());
                    let _ = append_metric_to_csv(&metric);
                    Ok::<_, (StatusCode, &'static str)>(Json(items_vec))
                }
            }
        }))
        .route("/api/read/:id", get({
            let metrics = metrics.clone();
            move |headers: HeaderMap, Path(id): Path<String>| {
                let metrics = metrics.clone();
                async move {
                    // sample memory before the single-read operation
                    let mem_before = sample_proc_memory_mb();
                    let start = std::time::Instant::now();
                    let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let maybe = conn.query_row(
                        "SELECT id, name, description FROM items WHERE id = ?1",
                        params![id.clone()],
                        |row| Ok(Item { id: row.get(0)?, name: row.get(1)?, description: row.get(2).ok() }),
                    ).optional().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let exec = start.elapsed().as_secs_f64() * 1000.0;

                    let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                    let mem_after = sample_proc_memory_mb();
                    let mem_mb = mem_after - mem_before;

                    let metric = Metric {
                        timestamp: Local::now().to_rfc3339(),
                        operation: "READ (Description)".to_string(),
                        execution_time_ms: exec,
                        memory_mb: mem_mb,
                        network_latency_ms: client_latency,
                    };
                    metrics.lock().push(metric.clone());
                    let _ = append_metric_to_csv(&metric);
                    match maybe {
                        Some(item) => Ok::<_, (StatusCode, &'static str)>(Json(item)),
                        None => Err((StatusCode::NOT_FOUND, "Not Found"))
                    }
                }
            }
        }))
        .route("/api/update/:id", put({
            let metrics = metrics.clone();
            move |headers: HeaderMap, Path(id): Path<String>, Json(payload): Json<serde_json::Value>| {
                let metrics = metrics.clone();
                async move {
                    let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    // sample memory before potential update operations
                    let mem_before = sample_proc_memory_mb();
                    let mut changed = false;
                    if let Some(n) = payload.get("name").and_then(|v| v.as_str()) {
                        let _ = conn.execute("UPDATE items SET name = ?1 WHERE id = ?2", params![n, id.clone()]);
                        changed = true;
                    }
                    if let Some(d) = payload.get("description").and_then(|v| v.as_str()) {
                        let _ = conn.execute("UPDATE items SET description = ?1 WHERE id = ?2", params![d, id.clone()]);
                        changed = true;
                    }
                    if changed {
                        let exec = 0.0;
                        let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                        let mem_after = sample_proc_memory_mb();
                        let mem_mb = mem_after - mem_before;
                        let metric = Metric {
                            timestamp: Local::now().to_rfc3339(),
                            operation: "UPDATE".to_string(),
                            execution_time_ms: exec,
                            memory_mb: mem_mb,
                            network_latency_ms: client_latency,
                        };
                        metrics.lock().push(metric.clone());
                        let _ = append_metric_to_csv(&metric);
                        Ok::<_, (StatusCode, &'static str)>(StatusCode::OK)
                    } else {
                        Err((StatusCode::NOT_FOUND, "Not Found"))
                    }
                }
            }
        }))
        .route("/api/delete/:id", delete({
            let metrics = metrics.clone();
            move |headers: HeaderMap, Path(id): Path<String>| {
                let metrics = metrics.clone();
                async move {
                    // sample memory before delete
                    let mem_before = sample_proc_memory_mb();
                    let start = std::time::Instant::now();
                    let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let removed = conn.execute("DELETE FROM items WHERE id = ?1", params![id.clone()]).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
                    let exec = start.elapsed().as_secs_f64() * 1000.0;
                    let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
                    let mem_after = sample_proc_memory_mb();
                    let mem_mb = mem_after - mem_before;
                    let metric = Metric {
                        timestamp: Local::now().to_rfc3339(),
                        operation: "DELETE".to_string(),
                        execution_time_ms: exec,
                        memory_mb: mem_mb,
                        network_latency_ms: client_latency,
                    };
                    metrics.lock().push(metric.clone());
                    let _ = append_metric_to_csv(&metric);
                    if removed > 0 {
                        Ok::<_, (StatusCode, &'static str)>(StatusCode::OK)
                    } else {
                        Err((StatusCode::NOT_FOUND, "Not Found"))
                    }
                }
            }
        }))
        // serve static files (including fallback index) from workspace root
        .fallback_service(axum::routing::get_service(tower_http::services::ServeDir::new("../static")).handle_error(|err| async move {
            (StatusCode::INTERNAL_SERVER_ERROR, format!("Unhandled internal error: {}", err))
        }));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Listening on http://{}", addr);
    axum::Server::bind(&addr).serve(app.into_make_service()).await.unwrap();
}