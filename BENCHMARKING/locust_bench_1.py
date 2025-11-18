import os
import uuid
from locust import HttpUser, task, between, events
import sys
import time
import csv
from datetime import datetime
def get_target_endpoint():
    # Priority: command-line arg > env var > default
    for i, arg in enumerate(sys.argv):
        if arg == '--endpoint' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return os.getenv('LOCUST_ENDPOINT')

def get_target_calls():
    # Priority: command-line arg > env var > default
    for i, arg in enumerate(sys.argv):
        if arg == '--calls' and i + 1 < len(sys.argv):
            try:
                return int(sys.argv[i + 1])
            except ValueError:
                pass
    try:
        return int(os.getenv('LOCUST_CALLS', '0'))
    except ValueError:
        return 0


def get_impl():
    # Read implementation selection from environment or Locust --env
    return os.getenv('impl') or os.getenv('LOCUST_IMPL') or 'rust'


class CRUDUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        self.impl = get_impl().lower()
        self.endpoint = get_target_endpoint()
        self.calls_left = get_target_calls()
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
        # create item (needed for endpoints that require an id)
        with self.client.post(self.paths['create'], json={'name': self.unique_name, 'description': 'created by locust'}, catch_response=True) as resp:
            pass
        # find our item by listing
        r = self.client.get(self.paths['list'])
        try:
            items = r.json()
            for it in items:
                if str(it.get('name')) == self.unique_name:
                    self.my_id = it.get('id')
                    break
        except Exception:
            self.my_id = None

    @task
    def dynamic_task(self):
        # If endpoint and calls are set, only run this task
        if self.endpoint and self.calls_left > 0:
            if self.endpoint == 'create':
                name = f"locust-{uuid.uuid4()}"
                self.client.post(self.paths['create'], json={'name': name, 'description': 'load'})
            elif self.endpoint == 'read_all' or self.endpoint == 'list':
                self.client.get(self.paths['list'])
            elif self.endpoint == 'read_one':
                if self.my_id:
                    self.client.get(self.paths['read_one'].format(self.my_id))
            elif self.endpoint == 'update':
                if self.my_id:
                    self.client.put(self.paths['update'].format(self.my_id), json={'name': f'upd-{uuid.uuid4()}', 'description': 'updated by locust'})
            elif self.endpoint == 'delete':
                if self.my_id:
                    self.client.delete(self.paths['delete'].format(self.my_id))
            elif self.endpoint == 'bulk_create':
                payload = [
                    {"name": f"bulk-{uuid.uuid4()}", "description": "bulk load"}
                    for _ in range(10)
                ]
                self.client.post(self.paths['bulk_create'], json=payload)
            self.calls_left -= 1
        elif self.endpoint and self.calls_left <= 0:
            self.environment.runner.quit()
            return

    # ...existing code for other tasks remains for backward compatibility...
