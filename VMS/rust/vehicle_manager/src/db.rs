use rusqlite::{Result, Connection};
use std::path::Path;

pub fn init_db(db_path: &str) -> Result<Connection> {
    let is_new = !Path::new(db_path).exists();

    let conn = Connection::open(db_path)?;

    conn.execute(
        "CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT
        )",
        [],
    )?;

    if is_new {
        println!("Database created: {}", db_path);
    } else {
        println!("Database opened: {}", db_path);
    }

    Ok(conn)
}