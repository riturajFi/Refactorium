from __future__ import annotations

from typing import TypedDict

from core.models.job.job import Job


class QueueAdapterNotImplementedError(NotImplementedError):
    """Raised for unimplemented queue adapters."""


class RabbitMQConfig(TypedDict):
    url: str
    queue_name: str


class RabbitMQQueue:
    """Skeleton adapter for external RabbitMQ integration."""

    def __init__(self, config: RabbitMQConfig) -> None:
        if config["url"].strip() == "":
            raise ValueError("rabbitmq url is empty")
        if config["queue_name"].strip() == "":
            raise ValueError("rabbitmq queue name is empty")
        self._config = config

    def enqueue(self, _job: Job) -> None:
        raise QueueAdapterNotImplementedError("rabbitmq enqueue: queue adapter not implemented")

    def dequeue(self, timeout: float | None = None) -> Job:  # noqa: ARG002
        raise QueueAdapterNotImplementedError("rabbitmq dequeue: queue adapter not implemented")

    def close(self) -> None:
        return
