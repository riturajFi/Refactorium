from __future__ import annotations

import os
import signal
import threading
from wsgiref.simple_server import make_server

from cmd.server.http_server import Server
from core.adapters.git_adapter import GitAdapter
from core.runtime.queue.queue import InMemoryQueue
from core.runtime.queue.rabbitmq_queue import RabbitMQConfig, RabbitMQQueue
from core.runtime.store.store import InMemoryStore
from core.runtime.worker.service import WorkerService


def main() -> None:
    stop_event = threading.Event()

    def _signal_handler(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    store = InMemoryStore()
    repo_access = GitAdapter(env_or_default("REPOSITORY_ROOT_DIR", "./.cache/repos"))

    queue = build_queue()
    worker_threads = start_worker_pool(
        stop_event=stop_event,
        queue=queue,
        store=store,
        repo_access=repo_access,
        worker_count=env_or_default_int("WORKER_COUNT", 1),
    )

    host, port = parse_http_addr(env_or_default("HTTP_ADDR", ":8080"))
    app = Server(store, queue).handler()

    httpd = make_server(host, port, app)
    try:
        while not stop_event.is_set():
            httpd.handle_request()
    finally:
        stop_event.set()
        queue.close()
        for thread in worker_threads:
            thread.join(timeout=1)


def build_queue():
    provider = env_or_default("QUEUE_PROVIDER", "inmemory").strip().lower()
    if provider == "inmemory":
        return InMemoryQueue(env_or_default_int("INMEMORY_QUEUE_BUFFER", 256))
    if provider == "rabbitmq":
        return RabbitMQQueue(
            {
                "url": os.getenv("RABBITMQ_URL", ""),
                "queue_name": env_or_default("RABBITMQ_QUEUE", "refactorium.jobs"),
            }
        )
    raise ValueError("unsupported QUEUE_PROVIDER")


def start_worker_pool(*, stop_event: threading.Event, queue, store, repo_access, worker_count: int):
    if worker_count < 1:
        worker_count = 1

    threads: list[threading.Thread] = []

    # TODO : Convert this to a wrapper like in retry
    for i in range(worker_count):
        svc = WorkerService(queue, store, repo_access)
        thread = threading.Thread(target=svc.run, args=(stop_event,), name=f"worker-{i}", daemon=True)
        thread.start()
        threads.append(thread)
    return threads


def env_or_default(key: str, fallback: str) -> str:
    value = os.getenv(key, "").strip()
    return value if value else fallback


def env_or_default_int(key: str, fallback: int) -> int:
    value = os.getenv(key, "").strip()
    if value == "":
        return fallback
    try:
        parsed = int(value)
    except ValueError:
        return fallback
    if parsed < 1:
        return fallback
    return parsed


def parse_http_addr(value: str) -> tuple[str, int]:
    raw = value.strip()
    if raw == "":
        return "0.0.0.0", 8080

    if raw.startswith(":"):
        return "0.0.0.0", int(raw[1:])

    if ":" not in raw:
        return raw, 8080

    host, port = raw.rsplit(":", 1)
    if host == "":
        host = "0.0.0.0"
    return host, int(port)


if __name__ == "__main__":
    main()
