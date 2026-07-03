from unittest.mock import patch

from validate import _network_sanity_check, validate_one
from vmail.dns_check import DnsResult
from vmail.smtp_probe import ProbeResult


def test_bad_syntax_short_circuits_no_network():
    with patch("validate.resolve_domain") as mock_dns:
        result = validate_one("not-an-email")
        assert result["Status"] == "INVALID"
        mock_dns.assert_not_called()


@patch("validate.resolve_domain")
def test_dead_domain_short_circuits_no_smtp(mock_dns):
    mock_dns.return_value = DnsResult(exists=False, reason="NO_DOMAIN")
    with patch("validate.probe") as mock_probe:
        result = validate_one("x@gq.comal")
        assert result["Status"] == "INVALID"
        mock_probe.assert_not_called()


@patch("validate.resolve_domain")
def test_zoho_skips_smtp_marked_unverifiable(mock_dns):
    mock_dns.return_value = DnsResult(exists=True, mx_hosts=["mx.zoho.in"])
    with patch("validate.probe") as mock_probe:
        result = validate_one("support@dentalkart.com")
        assert result["Status"] == "UNVERIFIABLE"
        assert result["Provider"] == "ZOHO"
        mock_probe.assert_not_called()


@patch("validate.check_catch_all")
@patch("validate.probe")
@patch("validate.resolve_domain")
def test_google_hosted_valid_path(mock_dns, mock_probe, mock_ca):
    mock_dns.return_value = DnsResult(exists=True, mx_hosts=["aspmx.l.google.com"])
    mock_probe.return_value = ProbeResult("ACCEPTS", 250, "2.1.5 OK - gsmtp")
    mock_ca.return_value = "NOT_CATCH_ALL"
    result = validate_one("hr@oracura.in")
    assert result["Status"] == "VALID"
    assert result["Safe_To_Send"] == "YES"
    assert result["SMTP_Code"] == 250


@patch("validate.resolve_domain")
def test_row_level_exception_becomes_error_status(mock_dns):
    mock_dns.side_effect = RuntimeError("boom")
    result = validate_one("x@example.com")
    assert result["Status"] == "ERROR"
    assert result["Safe_To_Send"] == "MANUAL"


@patch("validate.resolve_domain")
def test_network_sanity_aborts_on_small_all_timeout_file(mock_dns):
    mock_dns.return_value = DnsResult(exists=False, reason="DNS_TIMEOUT")
    rows = [
        {"_email": "a@example.com"},
        {"_email": "b@example.org"},
    ]
    try:
        _network_sanity_check(rows)
        assert False, "expected SystemExit"
    except SystemExit:
        pass


@patch("validate.resolve_domain")
def test_network_sanity_passes_when_domains_resolve(mock_dns):
    mock_dns.return_value = DnsResult(exists=True, mx_hosts=["mx.example.com"])
    rows = [
        {"_email": "a@example.com"},
        {"_email": "b@example.org"},
    ]
    _network_sanity_check(rows)
