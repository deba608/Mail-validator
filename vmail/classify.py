"""Disposable / role-account / free-provider detection from data lists."""
from dataclasses import dataclass
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> frozenset[str]:
    lines = (_DATA / name).read_text().splitlines()
    return frozenset(
        line.strip().lower() for line in lines
        if line.strip() and not line.startswith("#")
    )


_DISPOSABLE = _load("disposable_domains.txt")
_ROLES = _load("role_accounts.txt")
_FREE = _load("free_providers.txt")


@dataclass
class Flags:
    role: bool
    disposable: bool
    free: bool


def flags(normalized_email: str) -> Flags:
    local, _, domain = normalized_email.lower().partition("@")
    return Flags(
        role=local in _ROLES,
        disposable=domain in _DISPOSABLE,
        free=domain in _FREE,
    )
