from unittest.mock import patch

from vmail import catch_all
from vmail.catch_all import check_catch_all
from vmail.smtp_probe import ProbeResult


def setup_function(_):
    catch_all.clear_cache()


@patch("vmail.catch_all.probe")
def test_accepting_random_address_means_catch_all(mock_probe):
    mock_probe.return_value = ProbeResult("ACCEPTS", 250, "OK")
    assert check_catch_all("yopmail.com", ["mx.yopmail.com"]) == "CATCH_ALL"
    probed_email = mock_probe.call_args[0][0]
    assert probed_email.endswith("@yopmail.com")
    assert probed_email.startswith("zz-vmail-")


@patch("vmail.catch_all.probe")
def test_rejecting_random_address_means_not_catch_all(mock_probe):
    mock_probe.return_value = ProbeResult("INVALID", 550, "5.1.1 no such user")
    assert check_catch_all("oracura.in", ["mx.example"]) == "NOT_CATCH_ALL"


@patch("vmail.catch_all.probe")
def test_temporary_retries_once_then_unknown(mock_probe):
    mock_probe.return_value = ProbeResult("TEMPORARY", None, "timeout")
    assert check_catch_all("slow.com", ["mx.slow.com"]) == "UNKNOWN"
    assert mock_probe.call_count == 2  # retried once, never silently skipped


@patch("vmail.catch_all.probe")
def test_blocked_probe_is_unknown(mock_probe):
    mock_probe.return_value = ProbeResult("BLOCKED", 550, "spamhaus")
    assert check_catch_all("blocked.com", ["mx.blocked.com"]) == "UNKNOWN"


@patch("vmail.catch_all.probe")
def test_result_cached_per_domain(mock_probe):
    mock_probe.return_value = ProbeResult("INVALID", 550, "no such user")
    check_catch_all("dupe.com", ["mx.dupe.com"])
    check_catch_all("dupe.com", ["mx.dupe.com"])
    assert mock_probe.call_count == 1
