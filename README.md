# Vmail

Multi-layer email validation tool. Validates email addresses through syntax checking, DNS resolution, SMTP probing, provider fingerprinting, and classification (disposable/role/free).

## Features

- **Syntax** — RFC validation with typo-based domain suggestions
- **DNS** — MX record resolution with A-record fallback; per-run cache
- **SMTP** — RCPT-TO probing with honest reply classification (ACCEPTS / INVALID / BLOCKED / FULL_MAILBOX / TEMPORARY / UNKNOWN)
- **Provider** — Fingerprints mail providers from MX hostnames; flags providers known to block residential IPs (Zoho, Outlook, Proofpoint)
- **Classification** — Disposable domain, role account, and free provider detection from curated data lists

## Project structure

```
vmail/
├── vmail/
│   ├── __init__.py
│   ├── syntax.py         RFC syntax + domain suggestions
│   ├── dns_check.py      MX/A resolution with cache
│   ├── smtp_probe.py     SMTP RCPT-TO probing
│   ├── provider.py       MX-based provider fingerprinting
│   └── classify.py       Disposable / role / free detection
├── data/
│   ├── disposable_domains.txt
│   ├── free_providers.txt
│   └── role_accounts.txt
├── tests/
├── docs/
└── requirements.txt
```

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

## Usage

```python
from vmail.syntax import check_syntax
from vmail.dns_check import resolve_domain
from vmail.smtp_probe import probe
from vmail.provider import fingerprint, blocks_home_ip
from vmail.classify import flags

# 1. Syntax check
syn = check_syntax("user@gmail.com")

# 2. DNS resolution
dns = resolve_domain(syn.domain)

# 3. Provider fingerprint
provider = fingerprint(dns.mx_hosts)

# 4. SMTP probe (skip if provider blocks home IPs)
if not blocks_home_ip(provider):
    result = probe(syn.normalized, dns.mx_hosts)

# 5. Classification
cls = flags(syn.normalized)
```

## Design notes

- **DNS timeouts are not treated as proof of absence** — the resolver never caches a negative result as definitive
- **SMTP 550 is not blindly mapped to INVALID** — policy blocks (Spamhaus, dynamic IPs) and mailbox-full conditions are classified separately
- **Syntax layer does not check deliverability** — that responsibility belongs to the DNS and SMTP layers
# Mail-validator
