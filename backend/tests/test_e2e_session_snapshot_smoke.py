from __future__ import annotations

import json
import os
import threading
import time
import unittest
from pathlib import Path
from urllib import request

from wsgiref.simple_server import make_server

from cmd.server.http_server import Server
from core.adapters.git import GitAdapter
from core.models.session.snapshot_reference import SnapshotSource
from core.models.session.state import State
from core.runtime.queue.queue import InMemoryQueue
from core.runtime.store.store import InMemoryStore
from core.runtime.worker.service import WorkerService as Service


class SessionSnapshotSmokeTests(unittest.TestCase):
    def test_session_snapshot_smoke_remote_repo(self) -> None:
        repo_url = os.getenv("E2E_REMOTE_REPO_URL", "").strip()
        if repo_url == "":
            self.skipTest("set E2E_REMOTE_REPO_URL to run this smoke test")

        store = InMemoryStore()
        queue = InMemoryQueue(10)
        adapter = GitAdapter(str(Path(self._temp_dir()) / "repo-cache"))

        stop_event = threading.Event()
        worker_service = Service(queue, store, adapter)
        worker_thread = threading.Thread(target=worker_service.run, args=(stop_event,), daemon=True)
        worker_thread.start()

        app = Server(store, queue).handler()
        httpd = make_server("127.0.0.1", 0, app)
        port = httpd.server_port
        server_stop = threading.Event()

        def serve_loop() -> None:
            while not server_stop.is_set():
                httpd.handle_request()

        server_thread = threading.Thread(target=serve_loop, daemon=True)
        server_thread.start()

        try:
            payload: dict[str, str] = {"repoId": repo_url}
            ref = os.getenv("E2E_REMOTE_REF", "").strip()
            if ref:
                payload["ref"] = ref

            create_req = request.Request(
                f"http://127.0.0.1:{port}/sessions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(create_req, timeout=10) as resp:
                self.assertEqual(resp.status, 200)
                created = json.loads(resp.read().decode("utf-8"))

            session_id = created.get("sessionId", "")
            self.assertNotEqual(session_id, "")

            final = None
            for _ in range(40):
                with request.urlopen(f"http://127.0.0.1:{port}/sessions/{session_id}", timeout=10) as resp:
                    polled = json.loads(resp.read().decode("utf-8"))

                if polled.get("status") == State.SNAPSHOT_READY.value:
                    final = polled
                    break

                time.sleep(0.25)

            self.assertIsNotNone(final)
            assert final is not None
            self.assertEqual(final["status"], State.SNAPSHOT_READY.value)
            self.assertNotEqual(final["snapshot"]["commitHash"], "")
            self.assertNotEqual(final["snapshot"]["branchRef"], "")
            self.assertGreater(final["snapshot"]["fileCount"], 0)
            self.assertEqual(final["snapshot"]["source"], SnapshotSource.REMOTE.value)
        finally:
            server_stop.set()
            stop_event.set()
            queue.close()
            try:
                request.urlopen(f"http://127.0.0.1:{port}/__shutdown_ping__", timeout=1)
            except Exception:  # noqa: BLE001
                pass
            worker_thread.join(timeout=2)
            server_thread.join(timeout=2)

    def _temp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp()


if __name__ == "__main__":
    unittest.main()
