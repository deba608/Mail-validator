"""Catch-all detection: does the domain accept a clearly-nonexistent address?

Probed once per domain per run (cached). Retried once on temp failure —
never silently skipped like the previous tool's latency-based skip.
"""
import uuid

from vmail.smtp_probe import probe

_cache: dict[str, str] = {}


def clear_cache() -> None:
    _cache.clear()


def check_catch_all(domain: str, mx_hosts: list[str]) -> str:
    domain = domain.lower()
    if domain in _cache:
        return _cache[domain]

    fake = f"zz-vmail-{uuid.uuid4().hex[:12]}@{domain}"
    result = probe(fake, mx_hosts, timeout=10.0, retry_delay=0.0)
    if result.outcome == "TEMPORARY":
        result = probe(fake, mx_hosts, timeout=10.0, retry_delay=0.0)

    if result.outcome == "ACCEPTS":
        verdict = "CATCH_ALL"
    elif result.outcome == "INVALID":
        verdict = "NOT_CATCH_ALL"
    else:  # BLOCKED / TEMPORARY / UNKNOWN / FULL_MAILBOX — cannot tell
        verdict = "UNKNOWN"

    _cache[domain] = verdict
    return verdict
