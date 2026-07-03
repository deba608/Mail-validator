"""Identify the mail provider from MX hostnames.

ZOHO / OUTLOOK / PROOFPOINT reject SMTP from residential IPs on policy
grounds, so probing them from a home connection yields misleading 550s.
"""

_PATTERNS = {
    "GOOGLE": ("google.com", "googlemail.com"),
    "ZOHO": ("zoho.",),
    "OUTLOOK": ("protection.outlook.com", "olc.protection.outlook.com"),
    "PROOFPOINT": ("pphosted.com", "ppe-hosted.com"),
}

_HOME_IP_BLOCKERS = frozenset({"ZOHO", "OUTLOOK", "PROOFPOINT"})


def fingerprint(mx_hosts: list[str]) -> str:
    for host in mx_hosts:
        h = host.lower()
        for provider, needles in _PATTERNS.items():
            if any(n in h for n in needles):
                return provider
    return "OTHER"


def blocks_home_ip(provider: str) -> bool:
    return provider in _HOME_IP_BLOCKERS
