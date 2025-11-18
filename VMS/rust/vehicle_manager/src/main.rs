use axum::{Router, routing::get, routing::post};
use vehicle_manager::handlers::{get_vehicle, post_vehicle};

#[tokio::main]
async fn main() {
    //Connection to database can be initialized here if needed
    let _conn = vehicle_manager::db::init_db("vehicle_manager.db").expect("Failed to initialize database");


    //1 Create axum router
    let router_1 = Router::new() //If we have same routes then we can chain them here
    .route("/", get(|| async { "Hello, World!" }))
    .route("/vehicle/get_vehicle",get(get_vehicle))
    .route("/vehicle/post_vehicle", post(post_vehicle));

    //2 Define the IP and port listener
    let address  = "127.0.0.1:3000";
    let listener = tokio::net::TcpListener::bind(address).await.unwrap();

    //3 Start the server to launch the webserver
    axum::serve(listener, router_1).await.unwrap();

}


