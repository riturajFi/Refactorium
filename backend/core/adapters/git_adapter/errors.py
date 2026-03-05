from __future__ import annotations


class EmptyAdapterRootError(ValueError):
    """Raised when adapter root directory is empty."""


class EmptyRepoIDError(ValueError):
    """Raised when repository id is empty."""


class NonRemoteRepoIDError(ValueError):
    """Raised when repository id is not a supported remote identifier."""
