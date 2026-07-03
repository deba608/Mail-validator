from unittest.mock import MagicMock, patch

import dns.resolver

from vmail import dns_check
from vmail.dns_check import resolve_domain


def _mx(pref, host):
    rec = MagicMock()
    rec.preference = pref
    rec.exchange = MagicMock()
    rec.exchange.to_text.return_value = host
    return rec


def setup_function(_):
    dns_check.clear_cache()


@patch("vmail.dns_check.dns.resolver.resolve")
def test_mx_records_sorted_by_preference(mock_resolve):
    mock_resolve.return_value = [_mx(20, "mx2.example.com."), _mx(10, "mx1.example.com.")]
    r = resolve_domain("example.com")
    assert r.exists is True
    assert r.mx_hosts == ["mx1.example.com", "mx2.example.com"]
    assert r.used_fallback is False
    assert r.reason is None


@patch("vmail.dns_check.dns.resolver.resolve")
def test_no_mx_falls_back_to_a_record(mock_resolve):
    def side_effect(domain, rtype, lifetime):
        if rtype == "MX":
            raise dns.resolver.NoAnswer
        return [MagicMock()]  # A record exists
    mock_resolve.side_effect = side_effect
    r = resolve_domain("example.com")
    assert r.exists is True
    assert r.mx_hosts == ["example.com"]
    assert r.used_fallback is True


@patch("vmail.dns_check.dns.resolver.resolve")
def test_nxdomain_means_no_domain(mock_resolve):
    mock_resolve.side_effect = dns.resolver.NXDOMAIN
    r = resolve_domain("gq.comal")
    assert r.exists is False
    assert r.reason == "NO_DOMAIN"


@patch("vmail.dns_check.dns.resolver.resolve")
def test_no_mx_no_a_means_no_mx(mock_resolve):
    mock_resolve.side_effect = dns.resolver.NoAnswer
    r = resolve_domain("daybreak-official.com")
    assert r.exists is False
    assert r.reason == "NO_MX"


@patch("vmail.dns_check.dns.resolver.resolve")
def test_timeout_is_not_proof_of_absence(mock_resolve):
    mock_resolve.side_effect = dns.resolver.LifetimeTimeout
    r = resolve_domain("slow.example")
    assert r.exists is False
    assert r.reason == "DNS_TIMEOUT"


@patch("vmail.dns_check.dns.resolver.resolve")
def test_cache_hits_once(mock_resolve):
    mock_resolve.return_value = [_mx(10, "mx.example.com.")]
    resolve_domain("example.com")
    resolve_domain("example.com")
    assert mock_resolve.call_count == 1


@patch("vmail.dns_check.dns.resolver.resolve")
def test_no_nameservers_is_infra_failure_not_absence(mock_resolve):
    mock_resolve.side_effect = dns.resolver.NoNameservers
    r = resolve_domain("flaky-ns.example")
    assert r.exists is False
    assert r.reason == "DNS_TIMEOUT"  # infra failure => retry, never INVALID
