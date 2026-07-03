"""The only module that decides statuses. Everything else supplies evidence.

Core rule: when unsure → UNKNOWN-family status. Never fabricate INVALID
or VALID.
"""
from dataclasses import dataclass

from vmail.classify import Flags


@dataclass
class Evidence:
    syntax_ok: bool
    syntax_reason: str | None
    suggestion: str | None
    domain_exists: bool
    dns_reason: str | None
    provider: str
    provider_blocked: bool
    probe_outcome: str | None
    probe_code: int | None
    probe_message: str | None
    catch_all: str | None
    flags: Flags | None


@dataclass
class Verdict:
    status: str
    safe_to_send: str
    confidence: int
    reason: str


def decide(ev: Evidence) -> Verdict:
    if not ev.syntax_ok:
        reason = ev.syntax_reason or "Bad format"
        if ev.suggestion:
            reason += f" (did you mean @{ev.suggestion}?)"
        return Verdict("INVALID", "NO", 99, reason)

    if not ev.domain_exists:
        if ev.dns_reason == "DNS_TIMEOUT":
            return Verdict("TEMPORARY", "RETRY", 30,
                           "DNS lookup timed out — rerun later")
        detail = "domain does not exist" if ev.dns_reason == "NO_DOMAIN" \
            else "domain has no mail server (no MX/A records)"
        return Verdict("INVALID", "NO", 99, f"Dead domain: {detail}")

    if ev.provider_blocked:
        return Verdict(
            "UNVERIFIABLE", "MANUAL", 50,
            f"{ev.provider} rejects checks from home/residential IPs — "
            "mailbox cannot be verified from this machine",
        )

    outcome = ev.probe_outcome or "TEMPORARY"

    if outcome == "ACCEPTS":
        flags = ev.flags or Flags(False, False, False)
        if flags.disposable:
            return Verdict("VALID_RISKY", "CAUTION", 40,
                           "Mailbox accepts mail but domain is disposable")
        if ev.catch_all == "CATCH_ALL":
            return Verdict("VALID_RISKY", "CAUTION", 60,
                           "Domain accepts ALL addresses (catch-all) — "
                           "acceptance proves nothing")
        if ev.catch_all == "NOT_CATCH_ALL":
            conf = 90 if flags.role else 95
            note = " (role account)" if flags.role else ""
            return Verdict("VALID", "YES", conf, f"Mailbox exists{note}")
        return Verdict("VALID_RISKY", "CAUTION", 70,
                       "Mailbox accepted but catch-all status unverifiable")

    if outcome == "FULL_MAILBOX":
        return Verdict("VALID_RISKY", "CAUTION", 50,
                       "Mailbox exists but is over quota / inactive")

    if outcome == "INVALID":
        return Verdict("INVALID", "NO", 95,
                       "Server confirmed mailbox does not exist")

    if outcome in ("BLOCKED", "UNKNOWN"):
        return Verdict("BLOCKED_BY_SERVER", "MANUAL", 50,
                       "Server refused the check (policy/blocklist) — "
                       "mailbox status unknown, NOT proof it is invalid")

    return Verdict("TEMPORARY", "RETRY", 30,
                   "Server temporarily unavailable — rerun later")
