use leptos::*;
use serde::Deserialize;
use wasm_bindgen_futures::spawn_local;

#[derive(Clone, Deserialize)]
struct Item {
    id: String,
    name: String,
    description: Option<String>,
}

#[component]
pub fn App(cx: Scope) -> impl IntoView {
    let items = create_signal::<Vec<Item>>(cx, vec![]);
    let metrics = create_signal::<Vec<serde_json::Value>>(cx, vec![]);
    let name = create_node_ref::<html::Input>(cx);
    let desc = create_node_ref::<html::Input>(cx);
    let _edit_id = create_node_ref::<html::Input>(cx);
    let _edit_name = create_node_ref::<html::Input>(cx);
    let _edit_desc = create_node_ref::<html::Input>(cx);

    let load_db = {
        let items = items.clone();
        let metrics = metrics.clone();
        move || {
            let items = items.clone();
            let metrics = metrics.clone();
            spawn_local(async move {
                if let Ok(resp) = reqwest::get("/api/database").await {
                    if let Ok(json) = resp.json::<serde_json::Value>().await {
                        if let Some(arr) = json.get("items").and_then(|v| v.as_array()) {
                            let mut vec = Vec::new();
                            for it in arr {
                                if let Ok(i) = serde_json::from_value::<Item>(it.clone()) {
                                    vec.push(i);
                                }
                            }
                            items.1.set(vec);
                        }
                    }
                }
                if let Ok(resp) = reqwest::get("/api/metrics").await {
                    if let Ok(json) = resp.json::<Vec<serde_json::Value>>().await {
                        metrics.1.set(json);
                    }
                }
            });
        }
    };

    // initial load
    load_db();

    view! { cx,
        <div>
            <h2>"Leptos CRUD with Metrics"</h2>
            <div>
                <input node_ref= name placeholder="Name"/>
                <input node_ref= desc placeholder="Description"/>
                <button on:click=move |_| {
                    let n = name.get().and_then(|el| Some(el.value()));
                    let d = desc.get().and_then(|el| Some(el.value()));
                    if let (Some(n), Some(d)) = (n, d) {
                        spawn_local(async move {
                            let _ = reqwest::Client::new()
                                .post("/api/create")
                                .json(&serde_json::json!({"name": n, "description": d}))
                                .send()
                                .await;
                        });
                    }
                    load_db();
                }>"Add"</button>
            </div>

            <div>
                <h3>"Metrics Log"</h3>
                <table>
                    <tr><th>"Operation"</th><th>"Timestamp"</th></tr>
                    {move || {
                        metrics.0.get().iter().rev().take(10).map(|m| {
                            let op = m.get("operation").and_then(|v| v.as_str()).unwrap_or("").to_string();
                            let ts = m.get("timestamp").and_then(|v| v.as_str()).unwrap_or("").to_string();
                            view! { cx, <tr><td>{op}</td><td>{ts}</td></tr> }.into_view(cx)
                        }).collect::<Vec<_>>()
                    }}
                </table>
            </div>

            <div>
                <h3>"Database"</h3>
                <table>
                    <tr><th>"ID"</th><th>"Name"</th><th>"Desc"</th><th>"Action"</th></tr>
                    {move || {
                        items.0.get().iter().map(|it| {
                            let id = it.id.clone();
                            let name = it.name.clone();
                            let _desc_text = it.description.clone().unwrap_or_default();
                            view! { cx,
                                <tr>
                                    <td>{id.clone()}</td>
                                    <td>{name.clone()}</td>
                                    <td>
                                        <button on:click=move |_| {
                                            let id2 = id.clone();
                                            spawn_local(async move {
                                                let _ = reqwest::get(&format!("/api/read/{}", id2)).await;
                                            });
                                            // after recording, reload db/metrics
                                            load_db();
                                        }>"Show Description"</button>
                                    </td>
                                    <td>
                                        <button on:click=move |_| {
                                            // placeholder for edit flow
                                        }>"Edit"</button>
                                    </td>
                                </tr>
                            }.into_view(cx)
                        }).collect::<Vec<_>>()
                    }}
                </table>
            </div>
        </div>
    }
}