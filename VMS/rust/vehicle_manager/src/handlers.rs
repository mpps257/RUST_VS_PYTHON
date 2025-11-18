use axum::{debug_handler, Json};
use crate::vehicle::Vehicle;

#[debug_handler]
pub async fn get_vehicle() -> Json<Vehicle> {
    Json::from(Vehicle{
        maker   : "Toyota".to_string(),
        model: "Camry".to_string(),
        id: uuid::Uuid::new_v4().to_string(),
        year: 2020,
    })
}

#[debug_handler]
pub async fn post_vehicle() -> Json<&'static str> {
    Json::from("Something is coming from route using post_vehicle")
}