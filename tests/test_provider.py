from vmail.provider import blocks_home_ip, fingerprint


def test_google():
    assert fingerprint(["aspmx.l.google.com", "alt1.aspmx.l.google.com"]) == "GOOGLE"


def test_zoho():
    assert fingerprint(["mx.zoho.in", "mx2.zoho.in"]) == "ZOHO"


def test_outlook():
    assert fingerprint(["koraorganics-com.mail.protection.outlook.com"]) == "OUTLOOK"


def test_proofpoint():
    assert fingerprint(["mx2-us1.ppe-hosted.com"]) == "PROOFPOINT"
    assert fingerprint(["mxa-001.pphosted.com"]) == "PROOFPOINT"


def test_other():
    assert fingerprint(["mail.nakedallnatural.com"]) == "OTHER"
    assert fingerprint([]) == "OTHER"


def test_blockers():
    assert blocks_home_ip("ZOHO") is True
    assert blocks_home_ip("OUTLOOK") is True
    assert blocks_home_ip("PROOFPOINT") is True
    assert blocks_home_ip("GOOGLE") is False
    assert blocks_home_ip("OTHER") is False
