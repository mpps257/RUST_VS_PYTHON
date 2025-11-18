//Define a datastructure for vehicle to give as input or get as output
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Vehicle{
    pub maker: String,
    pub model: String,
    pub id: String,
    pub year: u16,
}