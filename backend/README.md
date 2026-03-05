# Refactorium Python Backend

This directory contains a full Python migration of the Go backend.

## Run tests

```bash
cd backend_py
PYTHONPATH=. python -m unittest discover -s tests -v
```

## Run server

```bash
cd backend_py
PYTHONPATH=. python -m cmd.server.main
```

## Key env vars

- `HTTP_ADDR` (default `:8080`)
- `WORKER_COUNT` (default `1`)
- `QUEUE_PROVIDER` (`inmemory` or `rabbitmq`)
- `INMEMORY_QUEUE_BUFFER` (default `256`)
- `REPOSITORY_ROOT_DIR` (default `./.cache/repos`)
- `GIT_AUTH_TOKEN` (optional for private HTTP(S) repos)
