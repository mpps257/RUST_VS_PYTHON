import os
import uuid
from locust import HttpUser, task, between
import time
import csv
from datetime import datetime


def get_impl():
    # Read implementation selection from environment or Locust --env
    return os.getenv('impl') or os.getenv('LOCUST_IMPL') or 'rust'


class CRUDUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        self.impl = get_impl().lower()
        # set endpoints depending on implementation
        if self.impl == 'rust':
            self.paths = {
                'create': '/api/create',
                'list': '/api/read',
                'read_one': '/api/read/{}',
                'update': '/api/update/{}',
                'delete': '/api/delete/{}',
                'bulk_create': '/api/bulk_create',
            }
        else:
            # default to flask
            self.paths = {
                'create': '/create',
                'list': '/read',
                'read_one': '/read/{}',
                'update': '/update/{}',
                'delete': '/delete/{}',
                'bulk_create': '/bulk_create',
            }

        # create a unique item for this user and remember its id
        self.unique_name = f"locust-{uuid.uuid4()}"
        self.my_id = None
        # create item
        with self.client.post(self.paths['create'], json={'name': self.unique_name, 'description': 'created by locust'}, catch_response=True) as resp:
            # we don't rely on the response body for ID; instead query list and find our item
            pass

        # find our item by listing
        r = self.client.get(self.paths['list'])
        try:
            items = r.json()
            for it in items:
                # items may have 'name' key
                if str(it.get('name')) == self.unique_name:
                    self.my_id = it.get('id')
                    break
        except Exception:
            self.my_id = None

    @task(3)
    def read_all(self):
        self.client.get(self.paths['list'])

    @task(2)
    def read_one(self):
        if self.my_id:
            self.client.get(self.paths['read_one'].format(self.my_id))

    @task(2)
    def create_item(self):
        name = f"locust-{uuid.uuid4()}"
        self.client.post(self.paths['create'], json={'name': name, 'description': 'load'})

    @task(1)
    def update_item(self):
        if self.my_id:
            self.client.put(self.paths['update'].format(self.my_id), json={'name': f'upd-{uuid.uuid4()}', 'description': 'updated by locust'})

    @task(1)
    def delete_and_recreate(self):
        if self.my_id:
            self.client.delete(self.paths['delete'].format(self.my_id))
            # recreate a replacement item and update my_id
            name = f"locust-{uuid.uuid4()}"
            self.client.post(self.paths['create'], json={'name': name, 'description': 'recreated'})
            # refresh id by listing
            r = self.client.get(self.paths['list'])
            try:
                items = r.json()
                for it in items:
                    if str(it.get('name')) == name:
                        self.my_id = it.get('id')
                        break
            except Exception:
                pass


    @task(1)
    def bulk_create_benchmark(self):
        

        # Test for these record counts
        record_counts = [100, 1000, 10000, 100000, 1000000]
        for count in record_counts:
            # Prepare payload
            payload = [
                {"name": f"bulk-{uuid.uuid4()}", "description": "bulk load"}
                for _ in range(count)
            ]
            start = time.time()
            with self.client.post(self.paths['bulk_create'], json=payload, catch_response=True) as resp:
                elapsed = (time.time() - start) * 1000  # ms
                # Log to CSV (append)
                log_row = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "operation": f"BULK_CREATE_{self.impl.upper()}_{count}",
                    "execution_time_ms": round(elapsed, 2),
                    "memory_mb": '',  # Not measured here
                    "network_latency_ms": ''  # Not measured here
                }
                # Write to CSV file (per impl)
                csv_file = f"bulk_create_{self.impl}.csv"
                file_exists = os.path.isfile(csv_file)
                with open(csv_file, mode='a', newline='') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=["timestamp", "operation", "execution_time_ms", "memory_mb", "network_latency_ms"]
                    )
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(log_row)
