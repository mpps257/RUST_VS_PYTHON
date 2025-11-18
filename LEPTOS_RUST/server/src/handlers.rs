
// Handler function imports
use axum::{extract::{Path, Json}, http::{StatusCode, HeaderMap}};
use axum::{routing::{get, post, put, delete}, Router};
use std::sync::Arc;
use uuid::Uuid;
use chrono::Local;
use serde_json::Value;

use rusqlite::{params, Connection, OptionalExtension};

use crate::item::Item;
use crate::metric::Metric;
use crate::utils::{append_metric_to_csv, sample_proc_memory_mb};

use parking_lot::Mutex;
type Metrics = Arc<Mutex<Vec<Metric>>>;

// Handler for /api/database
async fn get_database() -> Result<Json<serde_json::Value>, (StatusCode, &'static str)> {
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
	Ok(Json(db_info))
}

// Handler for /api/metrics
async fn get_metrics(metrics: Metrics) -> Result<Json<Vec<Metric>>, (StatusCode, &'static str)> {
	let m = metrics.lock().clone();
	Ok(Json(m))
}

// Handler for /api/metrics_ingest
async fn ingest_metrics(metrics: Metrics, Json(payload): Json<Value>) -> Result<StatusCode, (StatusCode, &'static str)> {
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
	Ok(StatusCode::CREATED)
}

// Handler for /api/create
async fn create_item(metrics: Metrics, headers: HeaderMap, Json(payload): Json<Value>) -> Result<StatusCode, (StatusCode, &'static str)> {
	let name = payload.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();
	let description = payload.get("description").and_then(|v| v.as_str()).map(|s| s.to_string());
	let id = Uuid::new_v4().to_string();
	let mem_before = sample_proc_memory_mb();
	let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	let start = std::time::Instant::now();
	let _ = conn.execute(
		"INSERT INTO items (id, name, description) VALUES (?1, ?2, ?3)",
		params![id.clone(), name.clone(), description.clone()],
	);
	let exec = start.elapsed().as_secs_f64() * 1000.0;
	let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
	let mem_after = sample_proc_memory_mb();
	let mem_mb = mem_after - mem_before;
	let metric = Metric {
		timestamp: Local::now().to_rfc3339(),
		operation: "CREATE".to_string(),
		execution_time_ms: exec,
		memory_mb: mem_mb,
		network_latency_ms: client_latency,
	};
	metrics.lock().push(metric.clone());
	let _ = append_metric_to_csv(&metric);
	Ok(StatusCode::CREATED)
}

// Handler for /api/bulk_create
async fn bulk_create(metrics: Metrics, headers: HeaderMap, Json(payload): Json<Value>) -> Result<StatusCode, (StatusCode, &'static str)> {
	let mem_before = sample_proc_memory_mb();
	let mut conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	let start = std::time::Instant::now();
	let items = payload.as_array().ok_or((StatusCode::BAD_REQUEST, "Expected an array of items"))?;
	let tx = conn.transaction().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	for item in items {
		let name = item.get("name").and_then(|v| v.as_str()).unwrap_or("");
		let description = item.get("description").and_then(|v| v.as_str());
		let id = Uuid::new_v4().to_string();
		let _ = tx.execute(
			"INSERT INTO items (id, name, description) VALUES (?1, ?2, ?3)",
			params![id, name, description],
		);
	}
	tx.commit().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	let exec = start.elapsed().as_secs_f64() * 1000.0;
	let client_latency = headers.get("x-client-latency-ms").and_then(|v| v.to_str().ok()).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0);
	let mem_after = sample_proc_memory_mb();
	let mem_mb = mem_after - mem_before;
	let metric = Metric {
		timestamp: Local::now().to_rfc3339(),
		operation: format!("BULK_CREATE_{}", items.len()),
		execution_time_ms: exec,
		memory_mb: mem_mb,
		network_latency_ms: client_latency,
	};
	metrics.lock().push(metric.clone());
	let _ = append_metric_to_csv(&metric);
	Ok(StatusCode::CREATED)
}

// Handler for /api/read
async fn read_all(metrics: Metrics, headers: HeaderMap) -> Result<Json<Vec<Item>>, (StatusCode, &'static str)> {
	let mem_before = sample_proc_memory_mb();

	let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	
	let start = std::time::Instant::now();
	let mut stmt = conn.prepare("SELECT id, name, description FROM items")
								      .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;

	let items_iter = stmt.query_map([], |row| {
																								Ok(Item {
																									id: row.get(0)?,
																									name: row.get(1)?,
																									description: row.get(2).ok(),
																								})
																							}).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;

	let exec = start.elapsed().as_secs_f64() * 1000.0;
	let mut items_vec = Vec::new();
	for it in items_iter {
		if let Ok(i) = it { items_vec.push(i); }
	}
	
	let client_latency = headers.get("x-client-latency-ms")
									 .and_then(|v| v.to_str().ok())
									 .and_then(|s| s.parse::<f64>().ok())
									 .unwrap_or(0.0);

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
	Ok(Json(items_vec))
}

// Handler for /api/read/:id
async fn read_one(metrics: Metrics, headers: HeaderMap, Path(id): Path<String>) -> Result<Json<Item>, (StatusCode, &'static str)> {
	let mem_before = sample_proc_memory_mb();
	let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	let start = std::time::Instant::now();
	let maybe = conn.query_row(
												"SELECT id, name, description FROM items WHERE id = ?1",
												params![id.clone()],
												|row| Ok(Item { id: row.get(0)?, name: row.get(1)?, description: row.get(2).ok() }),
											)
											.optional()
											.map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;

	let exec = start.elapsed().as_secs_f64() * 1000.0;
	let client_latency = headers.get("x-client-latency-ms")
									 .and_then(|v| v.to_str().ok())
									 .and_then(|s| s.parse::<f64>().ok())
									 .unwrap_or(0.0);
									
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
		Some(item) => Ok(Json(item)),
		None => Err((StatusCode::NOT_FOUND, "Not Found"))
	}
}

// Handler for /api/update/:id
async fn update_item(metrics: Metrics, headers: HeaderMap, Path(id): Path<String>, Json(payload): Json<Value>) -> Result<StatusCode, (StatusCode, &'static str)> {
	let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	let mem_before = sample_proc_memory_mb();
	let mut changed = false;
	let start = std::time::Instant::now();
	if let Some(n) = payload.get("name").and_then(|v| v.as_str()) {
		let _ = conn.execute("UPDATE items SET name = ?1 WHERE id = ?2", params![n, id.clone()]);
		changed = true;
	}
	if let Some(d) = payload.get("description").and_then(|v| v.as_str()) {
		let _ = conn.execute("UPDATE items SET description = ?1 WHERE id = ?2", params![d, id.clone()]);
		changed = true;
	}
	let exec = start.elapsed().as_secs_f64() * 1000.0;
	if changed {
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
		Ok(StatusCode::OK)
	} else {
		Err((StatusCode::NOT_FOUND, "Not Found"))
	}
}

// Handler for /api/delete/:id
async fn delete_item(metrics: Metrics, headers: HeaderMap, Path(id): Path<String>) -> Result<StatusCode, (StatusCode, &'static str)> {
	let mem_before = sample_proc_memory_mb();
	let conn = Connection::open("db.sqlite").map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "DB error"))?;
	let start = std::time::Instant::now();
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
		Ok(StatusCode::OK)
	} else {
		Err((StatusCode::NOT_FOUND, "Not Found"))
	}
}



pub fn create_app() -> Router {
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

	Router::new()
		.route("/api/database", get(get_database))
		.route("/api/bulk_create", post({
			let metrics = metrics.clone();
			move |headers, payload| bulk_create(metrics.clone(), headers, payload)
		}))
		.route("/api/metrics", get({
			let metrics = metrics.clone();
			move || get_metrics(metrics.clone())
		}))
		.route("/api/metrics_ingest", post({
			let metrics = metrics.clone();
			move |payload| ingest_metrics(metrics.clone(), payload)
		}))
		.route("/api/create", post({
			let metrics = metrics.clone();
			move |headers, payload| create_item(metrics.clone(), headers, payload)
		}))
		.route("/api/read", get({
			let metrics = metrics.clone();
			move |headers| read_all(metrics.clone(), headers)
		}))
		.route("/api/read/:id", get({
			let metrics = metrics.clone();
			move |headers, path| read_one(metrics.clone(), headers, path)
		}))
		.route("/api/update/:id", put({
			let metrics = metrics.clone();
			move |headers, path, payload| update_item(metrics.clone(), headers, path, payload)
		}))
		.route("/api/delete/:id", delete({
			let metrics = metrics.clone();
			move |headers, path| delete_item(metrics.clone(), headers, path)
		}))
		// serve static files (including fallback index) from workspace root
		.fallback_service(axum::routing::get_service(tower_http::services::ServeDir::new("../static")).handle_error(|err| async move {
			(StatusCode::INTERNAL_SERVER_ERROR, format!("Unhandled internal error: {}", err))
		}))
}
