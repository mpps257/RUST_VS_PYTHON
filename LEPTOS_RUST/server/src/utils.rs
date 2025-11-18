use std::fs;
use csv::WriterBuilder;
use crate::metric::Metric;
use sysinfo::{System, SystemExt, ProcessExt};

const CSV_FILE: &str = "read.csv";

pub fn append_metric_to_csv(metric: &Metric) -> Result<(), std::io::Error> {
    let file_exists = std::path::Path::new(CSV_FILE).exists();
    let file = fs::OpenOptions::new().create(true).append(true).open(CSV_FILE)?;
    let mut wtr = WriterBuilder::new().has_headers(!file_exists).from_writer(file);
    wtr.serialize(metric)?;
    wtr.flush()?;
    Ok(())
}

pub fn sample_proc_memory_mb() -> f64 {
    let mut sys = System::new_all();
    sys.refresh_processes();
    let current_pid_str = std::process::id().to_string();
    sys.processes()
        .values()
        .find(|p| p.pid().to_string() == current_pid_str)
        .map(|p| p.memory() as f64 / 1024.0)
        .unwrap_or(0.0)
}
