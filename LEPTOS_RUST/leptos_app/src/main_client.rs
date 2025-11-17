use leptos::*;
use leptos_app::App;

fn main() {
    mount_to_body(|cx| {
        view! { cx, <App/> }
    });
}