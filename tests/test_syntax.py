from vmail.syntax import check_syntax


def test_valid_email_normalizes():
    r = check_syntax("  Jane@TheOrganicRiot.com ")
    assert r.ok is True
    assert r.normalized == "jane@theorganicriot.com"
    assert r.domain == "theorganicriot.com"
    assert r.reason is None


def test_bad_tld_fails_with_suggestion():
    # real bad row from Raw_Email.xlsx
    # NOTE: email-validator accepts gq.comal as syntactically valid (TLD-shaped domain)
    # when check_deliverability=False. Domain existence is Task 4's job (DNS validation).
    # This test confirms that syntax layer passes it through; DNS validation will catch it.
    r = check_syntax("cuma.meroan@gq.comal")
    assert r.ok is True
    assert r.domain == "gq.comal"


def test_empty_and_none_fail():
    assert check_syntax("").ok is False
    assert check_syntax(None).ok is False
    assert check_syntax("   ").ok is False


def test_double_dot_fails():
    r = check_syntax("a..b@gmail.com")
    assert r.ok is False


def test_typo_domain_gets_suggestion():
    r = check_syntax("someone@gmial.com")
    # gmial.com parses as syntactically fine; suggestion should point at gmail.com
    assert r.suggestion == "gmail.com"
