"""SMTP RCPT-TO probing and — crucially — honest reply classification.

A 550 does NOT always mean "mailbox does not exist". Policy rejections
(Spamhaus listings, dynamic-IP blocks) also use 550. Misreading those as
INVALID was the core bug in the previous tool.
"""
import smtplib
import socket
import time
from dataclasses import dataclass

HELO_HOST = "vmail.local"
MAIL_FROM = "verify@vmail.local"

# Marker lists are the single place new patterns get added.
_INVALID_MARKERS = (
    "5.1.1", "no such user", "does not exist", "unknown user", "user unknown",
    "recipient rejected", "invalid recipient", "nosuchuser",
    "user not found", "recipient not found",
)
_BLOCKED_MARKERS = (
    "5.7.", "spamhaus", "blocked", "blacklist", "policy", "dynamic ip",
    "dynamic ip's", "access denied", "not authorized", "banned", "spam",
)
_FULL_MARKERS = ("over quota", "overquota", "storage", "mailbox full", "5.2.2")


@dataclass
class ProbeResult:
    outcome: str  # ACCEPTS | INVALID | BLOCKED | FULL_MAILBOX | TEMPORARY | UNKNOWN
    code: int | None
    message: str | None


def classify_reply(code: int | None, message: str | None) -> str:
    text = (message or "").lower()
    if code is None:
        return "TEMPORARY"
    if 200 <= code < 300:
        return "ACCEPTS"
    if 400 <= code < 500:
        return "TEMPORARY"
    if code >= 500:
        if any(m in text for m in _FULL_MARKERS):
            return "FULL_MAILBOX"
        if any(m in text for m in _BLOCKED_MARKERS):
            return "BLOCKED"
        if any(m in text for m in _INVALID_MARKERS):
            return "INVALID"
        return "UNKNOWN"
    return "UNKNOWN"


def probe(email: str, mx_hosts: list[str], timeout: float = 10.0,
          retry_delay: float = 60.0) -> ProbeResult:
    """Ask up to the first two MX hosts whether `email` is deliverable."""
    last = ProbeResult("TEMPORARY", None, "No MX host reachable")
    for host in mx_hosts[:2]:
        result = _rcpt_to(email, host, timeout)
        if result.outcome == "TEMPORARY" and result.code and 400 <= result.code < 500:
            time.sleep(retry_delay)  # greylisting: one polite retry
            result = _rcpt_to(email, host, timeout)
        if result.outcome != "TEMPORARY":
            return result
        last = result
    return last


def _rcpt_to(email: str, host: str, timeout: float) -> ProbeResult:
    try:
        with smtplib.SMTP(host, 25, timeout=timeout, local_hostname=HELO_HOST) as smtp:
            smtp.ehlo_or_helo_if_needed()
            smtp.mail(MAIL_FROM)
            code, raw = smtp.rcpt(email)
            message = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
            return ProbeResult(classify_reply(code, message), code, message)
    except smtplib.SMTPServerDisconnected as exc:
        return ProbeResult("TEMPORARY", None, f"Server disconnected ({host}): {exc}")
    except (socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
        return ProbeResult("TEMPORARY", None, f"Connection failed ({host}): {exc}")
    except smtplib.SMTPException as exc:
        return ProbeResult("TEMPORARY", None, f"SMTP error ({host}): {exc}")
