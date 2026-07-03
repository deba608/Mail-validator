"""RFC syntax validation plus near-miss domain suggestions."""
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from email_validator import EmailNotValidError, validate_email

_DATA = Path(__file__).resolve().parent.parent / "data"
_KNOWN_DOMAINS = [
    line.strip().lower()
    for line in (_DATA / "free_providers.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]


@dataclass
class SyntaxResult:
    ok: bool
    normalized: str | None = None
    domain: str | None = None
    reason: str | None = None
    suggestion: str | None = None


def _suggest(domain: str) -> str | None:
    matches = get_close_matches(domain, _KNOWN_DOMAINS, n=1, cutoff=0.85)
    if matches and matches[0] != domain:
        return matches[0]
    return None


def check_syntax(email) -> SyntaxResult:
    if not email or not str(email).strip():
        return SyntaxResult(ok=False, reason="Empty email")
    raw = str(email).strip()
    try:
        # check_deliverability=False: DNS is Task 4's job, not the syntax layer's
        info = validate_email(raw, check_deliverability=False)
    except EmailNotValidError as exc:
        domain = raw.rsplit("@", 1)[-1].lower() if "@" in raw else None
        return SyntaxResult(
            ok=False,
            reason=f"Bad format: {exc}",
            suggestion=_suggest(domain) if domain else None,
        )
    domain = info.domain.lower()
    local_part = info.local_part.lower()
    return SyntaxResult(
        ok=True,
        normalized=f"{local_part}@{domain}",
        domain=domain,
        suggestion=_suggest(domain),
    )
