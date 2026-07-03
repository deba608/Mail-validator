from vmail.classify import Flags
from vmail.verdict import Evidence, decide


def _ev(**kw):
    base = dict(
        syntax_ok=True, syntax_reason=None, suggestion=None,
        domain_exists=True, dns_reason=None,
        provider="OTHER", provider_blocked=False,
        probe_outcome=None, probe_code=None, probe_message=None,
        catch_all=None, flags=Flags(role=False, disposable=False, free=False),
    )
    base.update(kw)
    return Evidence(**base)


def test_bad_syntax_is_invalid_99():
    v = decide(_ev(syntax_ok=False, syntax_reason="Bad format: no @"))
    assert (v.status, v.safe_to_send, v.confidence) == ("INVALID", "NO", 99)


def test_dead_domain_is_invalid_99():
    v = decide(_ev(domain_exists=False, dns_reason="NO_DOMAIN"))
    assert (v.status, v.safe_to_send, v.confidence) == ("INVALID", "NO", 99)


def test_dns_timeout_is_temporary_not_invalid():
    v = decide(_ev(domain_exists=False, dns_reason="DNS_TIMEOUT"))
    assert v.status == "TEMPORARY"
    assert v.safe_to_send == "RETRY"


def test_provider_blocked_is_unverifiable():
    v = decide(_ev(provider="ZOHO", provider_blocked=True))
    assert (v.status, v.safe_to_send, v.confidence) == ("UNVERIFIABLE", "MANUAL", 50)
    assert "home" in v.reason.lower() or "residential" in v.reason.lower()


def test_accepts_not_catch_all_is_valid():
    v = decide(_ev(probe_outcome="ACCEPTS", probe_code=250, catch_all="NOT_CATCH_ALL"))
    assert (v.status, v.safe_to_send, v.confidence) == ("VALID", "YES", 95)


def test_role_account_valid_slightly_lower_confidence():
    v = decide(_ev(probe_outcome="ACCEPTS", probe_code=250, catch_all="NOT_CATCH_ALL",
                   flags=Flags(role=True, disposable=False, free=False)))
    assert (v.status, v.confidence) == ("VALID", 90)


def test_accepts_catch_all_domain_is_risky():
    v = decide(_ev(probe_outcome="ACCEPTS", probe_code=250, catch_all="CATCH_ALL"))
    assert (v.status, v.safe_to_send, v.confidence) == ("VALID_RISKY", "CAUTION", 60)


def test_disposable_is_risky_even_if_accepted():
    v = decide(_ev(probe_outcome="ACCEPTS", probe_code=250, catch_all="NOT_CATCH_ALL",
                   flags=Flags(role=False, disposable=True, free=False)))
    assert (v.status, v.confidence) == ("VALID_RISKY", 40)


def test_full_mailbox_is_risky():
    v = decide(_ev(probe_outcome="FULL_MAILBOX", probe_code=552))
    assert (v.status, v.safe_to_send, v.confidence) == ("VALID_RISKY", "CAUTION", 50)


def test_proven_nosuchuser_is_invalid_95():
    v = decide(_ev(probe_outcome="INVALID", probe_code=550))
    assert (v.status, v.safe_to_send, v.confidence) == ("INVALID", "NO", 95)


def test_blocked_probe_is_blocked_by_server():
    v = decide(_ev(probe_outcome="BLOCKED", probe_code=550))
    assert (v.status, v.safe_to_send, v.confidence) == ("BLOCKED_BY_SERVER", "MANUAL", 50)


def test_unknown_5xx_maps_to_blocked_by_server_never_invalid():
    v = decide(_ev(probe_outcome="UNKNOWN", probe_code=554))
    assert v.status == "BLOCKED_BY_SERVER"
    assert v.status != "INVALID"


def test_temporary_probe_is_temporary():
    v = decide(_ev(probe_outcome="TEMPORARY"))
    assert (v.status, v.safe_to_send, v.confidence) == ("TEMPORARY", "RETRY", 30)


def test_accepts_with_unknown_catch_all_is_risky_not_valid():
    # server said 250 but we could not verify catch-all → do not overclaim
    v = decide(_ev(probe_outcome="ACCEPTS", probe_code=250, catch_all="UNKNOWN"))
    assert v.status == "VALID_RISKY"
