use serde::{Serialize, Deserialize};

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Metric {
    pub timestamp: String,
    pub operation: String,
    pub execution_time_ms: f64,
    pub memory_mb: f64,
    pub network_latency_ms: f64,
}
