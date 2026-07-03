from vmail.smtp_probe import classify_reply

SPAMHAUS_550 = (
    "5.7.1 Service unavailable, Client host [49.205.35.112] blocked using "
    "Spamhaus. To request removal from this list see "
    "https://www.spamhaus.org/query/ip/49.205.35.112 AS(1450)"
)
ZOHO_POLICY_550 = (
    "Mail rejected by <Zoho Mail> for policy reasons. We generally do not "
    "accept email from dynamic IP's as they are typically used to deliver "
    "unauthenticated SMTP e-mail to an Internet mail server."
)
GOOGLE_NOSUCHUSER_550 = (
    "5.1.1 The email account that you tried to reach does not exist. Please "
    "try double-checking the recipient's email address for typos or "
    "unnecessary spaces. https://support.google.com/mail/?p=NoSuchUser"
)
GOOGLE_OVERQUOTA_552 = (
    "5.2.2 The recipient's inbox is out of storage space and inactive. "
    "Please direct the recipient to "
    "https://support.google.com/mail/?p=OverQuotaPerm"
)


def test_250_accepts():
    assert classify_reply(250, "2.1.5 OK - gsmtp") == "ACCEPTS"


def test_spamhaus_block_is_not_invalid():
    # THE original bug: old tool marked this INVALID_MAILBOX
    assert classify_reply(550, SPAMHAUS_550) == "BLOCKED"


def test_zoho_policy_block_is_not_invalid():
    # THE original bug, Zoho variant
    assert classify_reply(550, ZOHO_POLICY_550) == "BLOCKED"


def test_google_nosuchuser_is_invalid():
    assert classify_reply(550, GOOGLE_NOSUCHUSER_550) == "INVALID"


def test_overquota_is_full_mailbox_not_temporary():
    # old tool called this TEMPORARY_FAILURE; mailbox exists but is dead-full
    assert classify_reply(552, GOOGLE_OVERQUOTA_552) == "FULL_MAILBOX"


def test_4xx_greylist_is_temporary():
    assert classify_reply(451, "4.7.1 Greylisted, try again later") == "TEMPORARY"


def test_timeout_none_code_is_temporary():
    assert classify_reply(None, "connection timed out") == "TEMPORARY"


def test_unrecognized_5xx_is_unknown_never_invalid():
    assert classify_reply(554, "transaction failed") == "UNKNOWN"


def test_plain_user_unknown_is_invalid():
    assert classify_reply(550, "user unknown") == "INVALID"


def test_access_denied_is_blocked():
    assert classify_reply(550, "Access denied, banned sender") == "BLOCKED"
