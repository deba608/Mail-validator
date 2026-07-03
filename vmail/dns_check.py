"""MX/A resolution with a per-run cache. Timeouts are never proof of absence."""
from dataclasses import dataclass, field

import dns.resolver
import dns.exception

_TIMEOUT = 8.0
_cache: dict[str, "DnsResult"] = {}


@dataclass
class DnsResult:
    exists: bool
    mx_hosts: list[str] = field(default_factory=list)
    used_fallback: bool = False
    reason: str | None = None


def clear_cache() -> None:
    _cache.clear()


def resolve_domain(domain: str) -> DnsResult:
    domain = domain.lower()
    if domain in _cache:
        return _cache[domain]
    result = _resolve(domain)
    _cache[domain] = result
    return result


def _resolve(domain: str) -> DnsResult:
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=_TIMEOUT)
        hosts = sorted(
            (r.preference, r.exchange.to_text().rstrip(".").lower()) for r in answers
        )
        return DnsResult(exists=True, mx_hosts=[h for _, h in hosts])
    except dns.resolver.NXDOMAIN:
        return DnsResult(exists=False, reason="NO_DOMAIN")
    except dns.resolver.NoNameservers:
        return DnsResult(exists=False, reason="DNS_TIMEOUT")
    except dns.resolver.NoAnswer:
        pass  # fall through to A-record check
    except dns.exception.Timeout:
        return DnsResult(exists=False, reason="DNS_TIMEOUT")

    try:
        dns.resolver.resolve(domain, "A", lifetime=_TIMEOUT)
        return DnsResult(exists=True, mx_hosts=[domain], used_fallback=True)
    except dns.resolver.NXDOMAIN:
        return DnsResult(exists=False, reason="NO_DOMAIN")
    except dns.resolver.NoNameservers:
        return DnsResult(exists=False, reason="DNS_TIMEOUT")
    except dns.resolver.NoAnswer:
        return DnsResult(exists=False, reason="NO_MX")
    except dns.exception.Timeout:
        return DnsResult(exists=False, reason="DNS_TIMEOUT")
