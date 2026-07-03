# Mail Validator

A robust, multi-layer email validation tool designed to handle home/residential IP blocklists gracefully. It performs syntax checking, DNS resolution, provider fingerprinting, SMTP probing, active catch-all detection, and disposable/role/free domain classification to deliver reliable verification verdicts.

## Features & Verification Pipeline

For every email address, the validation pipeline runs cheap checks first, escalating to network-intensive checks only when preceding checks pass:

1. **Syntax Checking** — RFC-compliant validation with typo-based domain suggestions (e.g., suggesting `@gmail.com` for `@gamil.com`).
2. **DNS Resolution** — Resolves MX records with A/AAAA-record fallback. Employs a per-run cache to avoid redundant lookups.
3. **Provider Fingerprinting** — Inspects MX hostnames to detect providers known to block residential IPs (e.g., Zoho, Outlook, Proofpoint). These are marked as `UNVERIFIABLE` rather than falsifying an `INVALID` result.
4. **SMTP Probing** — Initiates a mail transaction (HELO/MAIL FROM/RCPT TO) without sending an actual message. Classifies response codes and text markers.
5. **Catch-All Detection** — Actively probes a randomized nonexistent address once per domain (cached) to determine if the domain accepts all incoming mail.
6. **Verdict Engine** — Consolidates all collected evidence into a final status, confidence rating, and plain-English explanation.

---

## Project Structure

```
Mail-validator/
├── validate.py           # CLI entry point: python validate.py Raw_Email.xlsx
├── requirements.txt      # Project dependencies (dnspython, openpyxl, etc.)
├── data/                 # Curated data sources for classification
│   ├── disposable_domains.txt
│   ├── free_providers.txt
│   └── role_accounts.txt
├── vmail/                # Core implementation package
│   ├── __init__.py
│   ├── catch_all.py      # Active catch-all mailbox detection
│   ├── classify.py       # Disposable, role-account, and free provider detection
│   ├── dns_check.py      # MX/A DNS resolution and caching
│   ├── excel_io.py       # Openpyxl reader/writer with color-coded fills and summary sheets
│   ├── provider.py       # MX hostname-based provider fingerprinting
│   ├── smtp_probe.py     # HELO/MAIL FROM/RCPT TO probing and response categorization
│   ├── syntax.py         # Syntax check and domain typo suggestions
│   └── verdict.py        # Central decision engine (converts evidence to status)
└── tests/                # Test suite replicating real-world edge cases
```

---

## Installation & Setup

1. **Requirements:** Python 3.10+
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### 1. Command Line Interface (CLI)

Validate any Excel spreadsheet containing email addresses. The script automatically identifies the column containing emails and outputs a styled, color-coded spreadsheet with an added `Summary` tab.

```bash
python validate.py Raw_Email.xlsx
```
*Note: The input file is never modified. The output will be saved as `Raw_Email_validated.xlsx`.*

### 2. Programmatic Usage

You can run individual components or construct the full pipeline programmatically:

```python
from vmail.syntax import check_syntax
from vmail.dns_check import resolve_domain
from vmail.provider import fingerprint, blocks_home_ip
from vmail.smtp_probe import probe
from vmail.catch_all import check_catch_all
from vmail.classify import flags
from vmail.verdict import Evidence, decide

# Validate an email address
email = "user@gmail.com"
syn = check_syntax(email)

if syn.ok:
    # 1. DNS Resolution
    dns = resolve_domain(syn.domain)
    
    # 2. Provider Check
    provider = fingerprint(dns.mx_hosts) if dns.exists else ""
    blocked = blocks_home_ip(provider)
    
    # 3. SMTP & Catch-All Probes (if not blocked by residential IP policy)
    probe_result = None
    catch = None
    if dns.exists and not blocked:
        probe_result = probe(syn.normalized, dns.mx_hosts)
        if probe_result.outcome == "ACCEPTS":
            catch = check_catch_all(syn.domain, dns.mx_hosts)
            
    # 4. Classification
    fl = flags(syn.normalized)
    
    # 5. Decide Verdict
    evidence = Evidence(
        syntax_ok=True,
        syntax_reason=None,
        suggestion=syn.suggestion,
        domain_exists=dns.exists,
        dns_reason=dns.reason,
        provider=provider,
        provider_blocked=blocked,
        probe_outcome=probe_result.outcome if probe_result else None,
        probe_code=probe_result.code if probe_result else None,
        probe_message=probe_result.message if probe_result else None,
        catch_all=catch,
        flags=fl
    )
    verdict = decide(evidence)
    print(f"Status: {verdict.status} (Safe to Send: {verdict.safe_to_send}, Confidence: {verdict.confidence}%)")
```

---

## Verdict Summary Table

The tool uses an evidence-based approach: **when unsure, it defaults to an UNKNOWN-family status rather than fabricating a VALID or INVALID result.**

| Status | Meaning | Safe_To_Send | Confidence | Row Color Fill |
| :--- | :--- | :--- | :--- | :--- |
| **`VALID`** | SMTP 250 accepted and domain is not catch-all. | `YES` | 90–95% | **Green** |
| **`VALID_RISKY`** | SMTP 250 accepted, but domain is catch-all, disposable, or over-quota (452/552). | `CAUTION` | 40–70% | **Yellow** |
| **`INVALID`** | Bad format, dead domain (no DNS/MX), or proven nonexistent mailbox. | `NO` | 95–99% | **Red** |
| **`UNVERIFIABLE`** | Mail provider blocks residential/home IPs; skipped to avoid blocklists. | `MANUAL` | 50% | **Yellow** |
| **`BLOCKED_BY_SERVER`**| Server refused check mid-conversation (e.g., Spamhaus blocklist response). | `MANUAL` | 50% | **Yellow** |
| **`TEMPORARY`** | Greylisting or network timeouts; status could not be verified on this run. | `RETRY` | 30% | **Grey** |
| **`ERROR`** | Unexpected exception encountered while processing the row. | `MANUAL` | 0% | **Grey** |

---

## Running Tests

Verify everything is working using `pytest`:

```bash
python -m pytest
```
