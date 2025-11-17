from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from utils import *
from models import db, Item
import csv
from datetime import datetime  # ✅ added for timestamps

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///flask_crud.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

metrics_log = []

CSV_FILE = "output_metrics.csv"

# ✅ Updated to include timestamp
def append_metric_to_csv(metric):
    """Append a metric entry (with timestamp) to the CSV log."""
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "operation", "execution_time_ms", "memory_mb", "network_latency_ms"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(metric)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify(metrics_log)


@app.route('/database', methods=['GET'])
def get_database_info():
    items = Item.query.all()
    return jsonify({
        "total_items": len(items),
        "items": [{"id": i.id, "name": i.name, "description": i.description} for i in items],
        "database_uri": os.getenv('DATABASE_URL', 'sqlite:///flask_crud.db')
    })


@app.route('/create', methods=['POST'])
def create_item():
    data = request.json
    item = Item(name=data['name'], description=data.get('description', ''))
    
    _, exec_time, mem_used = measure_execution_metrics(lambda: db.session.add(item))
    db.session.commit()

    metric = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": "CREATE",
        "execution_time_ms": exec_time,
        "memory_mb": mem_used,
        "network_latency_ms": measure_latency(request.url)
    }
    append_metric_to_csv(metric)
    metrics_log.append(metric)
    return jsonify({"message": "Item created successfully"}), 201


@app.route('/read', methods=['GET'])
def read_items():
    items, exec_time, mem_used = measure_execution_metrics(lambda: Item.query.all())
    output = [{"id": i.id, "name": i.name, "description": i.description} for i in items]

    metric = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": "READ",
        "execution_time_ms": exec_time,
        "memory_mb": mem_used,
        "network_latency_ms": measure_latency(request.url)
    }
    append_metric_to_csv(metric)
    metrics_log.append(metric)
    return jsonify(output)


@app.route('/update/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    item = Item.query.get_or_404(item_id)
    item.name = data['name']
    item.description = data.get('description', '')
    _, exec_time, mem_used = measure_execution_metrics(lambda: db.session.commit())

    metric = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": "UPDATE",
        "execution_time_ms": exec_time,
        "memory_mb": mem_used,
        "network_latency_ms": measure_latency(request.url)
    }
    append_metric_to_csv(metric)
    metrics_log.append(metric)
    return jsonify({"message": "Item updated successfully"})


@app.route('/delete/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    _, exec_time, mem_used = measure_execution_metrics(lambda: db.session.delete(item))
    db.session.commit()

    metric = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": "DELETE",
        "execution_time_ms": exec_time,
        "memory_mb": mem_used,
        "network_latency_ms": measure_latency(request.url)
    }
    append_metric_to_csv(metric)
    metrics_log.append(metric)
    return jsonify({"message": "Item deleted successfully"})


@app.route('/read/<int:item_id>', methods=['GET'])
def read_item(item_id):
    """Log a READ metric when user clicks 'Show Description'."""
    item, exec_time, mem_used = measure_execution_metrics(lambda: Item.query.get_or_404(item_id))

    metric = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": "READ (Description)",
        "execution_time_ms": exec_time,
        "memory_mb": mem_used,
        "network_latency_ms": measure_latency(request.url)
    }
    append_metric_to_csv(metric)
    metrics_log.append(metric)

    return jsonify({
        "id": item.id,
        "name": item.name,
        "description": item.description
    })


if __name__ == '__main__':
    app.run(debug=True)
