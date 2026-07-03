# Mail Validator

> A robust, multi-layer email validation tool built for outreach lists running from a **home/residential Windows PC**. It honestly reports when a mailbox cannot be verified instead of fabricating false `INVALID` results due to provider blocklists.

---

## Table of Contents

1. [Why This Exists](#1-why-this-exists)
2. [How It Works — The Pipeline](#2-how-it-works--the-pipeline)
3. [Project Structure](#3-project-structure)
4. [Installation & Setup](#4-installation--setup)
5. [Usage Guide](#5-usage-guide)
   - [5.1 Prepare Your Input File](#51-prepare-your-input-file)
   - [5.2 Run the Validator](#52-run-the-validator)
   - [5.3 Read the Terminal Output](#53-read-the-terminal-output)
   - [5.4 Open the Output File](#54-open-the-output-file)
6. [Understanding the Results](#6-understanding-the-results)
   - [6.1 Status Descriptions](#61-status-descriptions)
   - [6.2 What Action to Take per Status](#62-what-action-to-take-per-status)
   - [6.3 Color-Coding Guide](#63-color-coding-guide)
7. [SMTP Reply Classification](#7-smtp-reply-classification)
8. [Output File Details](#8-output-file-details)
9. [Programmatic Usage](#9-programmatic-usage)
10. [Running the Test Suite](#10-running-the-test-suite)
11. [Known Limitations & Design Decisions](#11-known-limitations--design-decisions)

---

## 1. Why This Exists

Standard email validators blindly map an SMTP `550` response to `INVALID`. But `550` is also the response code used by:

- **Spamhaus** blocklists blocking your residential IP
- **Zoho** and **Microsoft Outlook** refusing connections from home connections
- **Proofpoint** spam-filtering gateways

Running from a home PC, these produce **false negatives** — perfectly valid mailboxes marked as invalid. This tool classifies each `550` by inspecting the response text and the provider fingerprint, and honestly reports `UNVERIFIABLE` or `BLOCKED_BY_SERVER` instead of a fabricated `INVALID`.

> **Core Rule: When unsure → report UNKNOWN. Never fabricate INVALID or VALID.**

---

## 2. How It Works — The Pipeline

Every email goes through these layers in order, from cheapest to most expensive. A layer failure stops processing early.

```
[Email Address]
      │
      ▼
┌─────────────────┐
│  1. SYNTAX      │  RFC format check, typo suggestions (e.g. gq.comal → gmail.com)
└────────┬────────┘
         │ PASS
         ▼
┌─────────────────┐
│  2. DNS / MX    │  MX lookup → A/AAAA fallback. Cached per domain per run.
└────────┬────────┘
         │ PASS (domain exists)
         ▼
┌─────────────────┐
│  3. PROVIDER    │  MX hostname fingerprint. If provider blocks home IPs →
│  FINGERPRINT    │  mark UNVERIFIABLE, skip SMTP (saves time, avoids blocklists)
└────────┬────────┘
         │ PASS (not a residential-IP blocker)
         ▼
┌─────────────────┐
│  4. SMTP PROBE  │  HELO → MAIL FROM → RCPT TO (no message sent).
│                 │  Classifies reply code + text markers.
└────────┬────────┘
         │ PASS (250 ACCEPTS)
         ▼
┌─────────────────┐
│  5. CATCH-ALL   │  Probe a randomized fake address once per domain (cached).
│  DETECTION      │  ACCEPTS → catch-all domain (any address passes).
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. VERDICT     │  Combine all evidence → status + confidence + reason
└─────────────────┘
```

**Domain-level results** (DNS, provider fingerprint, catch-all) are **shared across all emails on the same domain** in a single run — the domain is only probed once.

---

## 3. Project Structure

```
Mail-validator/
│
├── validate.py                  # CLI entry point (run this)
├── requirements.txt             # pip dependencies
│
├── data/                        # Curated classification lists
│   ├── disposable_domains.txt   # Throwaway email services (mailinator, etc.)
│   ├── free_providers.txt       # Free email providers (gmail, yahoo, etc.)
│   └── role_accounts.txt        # Role prefixes (info, support, admin, sales, etc.)
│
├── vmail/                       # Core validation package
│   ├── __init__.py
│   ├── syntax.py                # RFC validation + typo suggestions
│   ├── dns_check.py             # MX/A record resolution + per-run cache
│   ├── provider.py              # MX hostname → provider label + home-IP block check
│   ├── smtp_probe.py            # HELO/MAIL FROM/RCPT TO + response classification
│   ├── catch_all.py             # Random fake-address probe, cached per domain
│   ├── classify.py              # Disposable / role / free flags from data lists
│   ├── verdict.py               # Central decision engine — only place statuses are assigned
│   └── excel_io.py              # Read input .xlsx, write color-coded output + Summary sheet
│
└── tests/                       # Full test suite (59 tests, no live network calls)
    ├── test_syntax.py
    ├── test_dns_check.py
    ├── test_provider.py
    ├── test_smtp_classification.py
    ├── test_catch_all.py
    ├── test_classify.py
    ├── test_verdict.py
    ├── test_excel_io.py
    └── test_orchestrator.py
```

---

## 4. Installation & Setup

### Requirements

- **Python 3.10+** (tested on Python 3.14)
- Windows, macOS, or Linux
- Internet connection (for DNS and SMTP probing)

### Steps

```bash
# 1. Clone or download the repository
git clone https://github.com/deba608/Mail-validator.git
cd Mail-validator

# 2. (Optional but recommended) Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt
```

### Dependencies (`requirements.txt`)

| Package | Purpose |
| :--- | :--- |
| `dnspython >= 2.4` | MX and A/AAAA record resolution |
| `openpyxl >= 3.1` | Reading input `.xlsx` and writing color-coded output |
| `email-validator >= 2.1` | RFC-compliant email syntax validation |
| `pytest >= 8.0` | Test suite runner |

---

## 5. Usage Guide

### 5.1 Prepare Your Input File

Your input must be an **Excel file (`.xlsx`)** with at least one column whose header contains the word `email` or `mail` (case-insensitive). Other columns in the file are preserved in the output.

**Example input (`Raw_Email.xlsx`):**

| Name | Email | Company |
| :--- | :--- | :--- |
| Alice | alice@example.com | Acme Corp |
| Bob | bob@gmail.com | Freelancer |

> The tool automatically finds the email column — you do not need to rename or reformat it.

---

### 5.2 Run the Validator

Open a terminal in the project folder and run:

```bash
python validate.py Raw_Email.xlsx
```

> ⚠️ **Your input file is never modified.** The output is written to a new file with `_validated` appended to the name (e.g., `Raw_Email_validated.xlsx`).

You can validate any file, not just `Raw_Email.xlsx`:

```bash
python validate.py my_leads_june.xlsx
# Output: my_leads_june_validated.xlsx

python validate.py "C:\Users\Dev\Desktop\outreach list.xlsx"
# Output: C:\Users\Dev\Desktop\outreach list_validated.xlsx
```

---

### 5.3 Read the Terminal Output

As the tool runs, it prints live progress for every email:

```
Read 27 emails from Raw_Email.xlsx
[1/27]  info@daysahead.nl               -> INVALID
[2/27]  support@dentalkart.com          -> UNVERIFIABLE
[5/27]  support@daybreak-official.com   -> TEMPORARY
[11/27] customersupport@betterdaysco.com -> VALID_RISKY
...
Done. Results: Raw_Email_validated.xlsx
```

The format is `[done/total] email -> STATUS`. Results appear as soon as each email finishes (up to 4 domains are checked in parallel).

**Network safety check:** If the first 3 domains all time out, the tool assumes the internet is down and aborts cleanly before writing any output.

**Keyboard interrupt (`Ctrl+C`):** Immediately stops probing and writes partial results to the output file. Unprocessed rows are marked `TEMPORARY / RETRY`.

---

### 5.4 Open the Output File

Open `Raw_Email_validated.xlsx`. It contains two sheets:

#### Sheet 1: Results
All original columns from your input file, plus 11 new validation columns appended on the right:

| Column | Description |
| :--- | :--- |
| `Status` | Final verdict (see §6.1) |
| `Safe_To_Send` | Action recommendation: `YES`, `NO`, `CAUTION`, `RETRY`, `MANUAL` |
| `Confidence` | Integer 0–99 reflecting certainty |
| `Reason` | Plain-English explanation of the verdict |
| `Provider` | Detected mail provider: `GOOGLE`, `ZOHO`, `OUTLOOK`, `PROOFPOINT`, `OTHER` |
| `Role_Account` | `True` if the local part is a role address (info, support, sales, admin…) |
| `Disposable` | `True` if the domain is a known throwaway service |
| `Free_Provider` | `True` if the domain is a free provider (Gmail, Yahoo, etc.) |
| `Catch_All` | `CATCH_ALL`, `NOT_CATCH_ALL`, or `UNKNOWN` |
| `SMTP_Code` | Raw SMTP response code from the server (e.g., `250`, `550`, `421`) |
| `SMTP_Evidence` | First 500 characters of the server's raw reply text |

Each row is color-coded by status (see §6.3).

#### Sheet 2: Summary
Auto-generated counts broken down by:
- Status (how many VALID, INVALID, TEMPORARY, etc.)
- Safe_To_Send bucket (YES / NO / CAUTION / RETRY / MANUAL)
- Top 15 domains by frequency

---

## 6. Understanding the Results

### 6.1 Status Descriptions

| Status | Meaning |
| :--- | :--- |
| `VALID` | Server confirmed the mailbox exists via SMTP 250, domain is **not** catch-all, and domain is not disposable. High confidence. |
| `VALID_RISKY` | Server accepted the address (250), but a risk factor applies: domain is catch-all (any address is accepted), or it is a known disposable service, or the server replied 552 (over quota / inactive mailbox). |
| `INVALID` | Hard failure: malformed address, domain has no DNS records, or the server explicitly confirmed the mailbox does not exist (SMTP 5.1.1 `NoSuchUser`). |
| `UNVERIFIABLE` | The mail provider (Zoho, Outlook, Proofpoint) rejects all SMTP checks from residential/home IP addresses. The mailbox status is genuinely unknown — not invalid. |
| `BLOCKED_BY_SERVER` | The server responded with a policy 550 (Spamhaus blocklist, dynamic IP block) mid-conversation. This means *the check was blocked*, **not** that the mailbox is invalid. |
| `TEMPORARY` | DNS timeout, greylisting, or other transient network issue. The tool cannot make a determination on this run. Re-run the file later. |
| `ERROR` | An unexpected exception occurred while processing this specific row. Other rows are unaffected. |

---

### 6.2 What Action to Take per Status

| Status | `Safe_To_Send` | Recommended Action |
| :--- | :--- | :--- |
| `VALID` | `YES` | ✅ Safe to include in your outreach. |
| `VALID_RISKY` | `CAUTION` | ⚠️ Use with caution. Catch-all domains mean the mailbox *might* not exist. Monitor bounce rates. |
| `INVALID` | `NO` | ❌ Remove from your list. Will hard bounce. |
| `UNVERIFIABLE` | `MANUAL` | 🔍 Cannot verify from home. Try verifying manually, or accept the risk. |
| `BLOCKED_BY_SERVER` | `MANUAL` | 🔍 Your IP is blocked — the mailbox may be valid. Consider a clean sending IP or manual verification. |
| `TEMPORARY` | `RETRY` | 🔄 Re-run `validate.py` after some time. Often resolves itself. |
| `ERROR` | `MANUAL` | 🔍 Check the `Reason` column for the specific exception. |

---

### 6.3 Color-Coding Guide

The Results sheet rows are filled with color based on status:

| Color | Status |
| :--- | :--- |
| 🟢 **Green** | `VALID` |
| 🔴 **Red** | `INVALID` |
| 🟡 **Yellow** | `VALID_RISKY`, `UNVERIFIABLE`, `BLOCKED_BY_SERVER` |
| ⚫ **Grey** | `TEMPORARY`, `ERROR` |

---

## 7. SMTP Reply Classification

The tool classifies SMTP responses using response codes **and** text markers (the server message body). This avoids mapping all `550` responses as `INVALID`.

| SMTP Code | Text Marker(s) | Classification |
| :--- | :--- | :--- |
| `250` | *(any)* | `ACCEPTS` → candidate `VALID` |
| `550`, `551`, `553` | `5.1.1`, `no such user`, `does not exist`, `unknown user`, `user unknown`, `recipient rejected`, `invalid recipient`, `NoSuchUser` | `INVALID` (mailbox confirmed absent) |
| `550`, `554` | `5.7.`, `spamhaus`, `blocked`, `blacklist`, `policy`, `dynamic ip`, `access denied`, `not authorized`, `spam` | `BLOCKED_BY_SERVER` (check refused, not invalid) |
| `452`, `552` | `over quota`, `storage`, `mailbox full` | `VALID_RISKY` (mailbox exists but inactive) |
| `4xx` | *(any)* | Retried once → `TEMPORARY` |
| Timeout / disconnect | — | `TEMPORARY` |
| Other `5xx` | *(no matching marker)* | `UNKNOWN` → `BLOCKED_BY_SERVER` (never `INVALID`) |

---

## 8. Output File Details

Output path is always: `<input_filename>_validated.xlsx`

- The input file is **never opened for writing** and **never modified**.
- If the output file already exists, it is **overwritten**.
- Output is written even if `Ctrl+C` was pressed mid-run (partial results).

**Concurrency:** Up to 4 domains are validated in parallel. Emails sharing the same domain are processed sequentially to avoid hammering one mail server.

---

## 9. Programmatic Usage

You can import individual modules to build custom validation workflows.

### Quick single-email check

```python
from vmail.syntax import check_syntax
from vmail.dns_check import resolve_domain
from vmail.provider import fingerprint, blocks_home_ip
from vmail.smtp_probe import probe
from vmail.catch_all import check_catch_all
from vmail.classify import flags
from vmail.verdict import Evidence, decide

email = "alice@example.com"

# Step 1: Syntax
syn = check_syntax(email)
if not syn.ok:
    print(f"Bad syntax: {syn.reason}")
    exit()

# Step 2: DNS
dns = resolve_domain(syn.domain)

# Step 3: Provider fingerprint
provider = fingerprint(dns.mx_hosts) if dns.exists else ""
blocked = blocks_home_ip(provider)

# Step 4: SMTP + catch-all
probe_result, catch = None, None
if dns.exists and not blocked:
    probe_result = probe(syn.normalized, dns.mx_hosts)
    if probe_result.outcome == "ACCEPTS":
        catch = check_catch_all(syn.domain, dns.mx_hosts)

# Step 5: Classification flags
fl = flags(syn.normalized)

# Step 6: Verdict
verdict = decide(Evidence(
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
    flags=fl,
))

print(f"Status      : {verdict.status}")
print(f"Safe to Send: {verdict.safe_to_send}")
print(f"Confidence  : {verdict.confidence}%")
print(f"Reason      : {verdict.reason}")
```

### Use only the syntax checker

```python
from vmail.syntax import check_syntax

result = check_syntax("cuma.meroan@gq.comal")
# result.ok        → False
# result.reason    → "Bad format: ..."
# result.suggestion → "gmail.com" (near-miss suggestion)
```

### Use only the classifier

```python
from vmail.classify import flags

fl = flags("info@gmail.com")
# fl.role       → True  (info is a role account)
# fl.disposable → False
# fl.free       → True  (gmail.com is a free provider)
```

---

## 10. Running the Test Suite

The test suite covers all modules with 59 tests and uses **no live network calls** — all DNS and SMTP responses are fixtures.

```bash
python -m pytest
```

Expected output:

```
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.1.1
collected 59 items

tests\test_catch_all.py           .....   [ 8%]
tests\test_classify.py            ....    [15%]
tests\test_dns_check.py           .......  [27%]
tests\test_excel_io.py            ...     [32%]
tests\test_orchestrator.py        .....   [40%]
tests\test_provider.py            ......  [50%]
tests\test_smtp_classification.py ..........  [67%]
tests\test_syntax.py              .....   [76%]
tests\test_verdict.py             ..............  [100%]

============================= 59 passed in 0.53s ==============================
```

To run a single test file:

```bash
python -m pytest tests/test_smtp_classification.py -v
```

---

## 11. Known Limitations & Design Decisions

| Limitation | Reason |
| :--- | :--- |
| **UNVERIFIABLE for Zoho, Outlook, Proofpoint** | These providers actively block SMTP from residential IPs. Probing them would only produce misleading `550` responses — so they are skipped and honestly reported as unverifiable. |
| **Many TEMPORARY results on first run** | Greylisting (servers that temporarily reject unknown senders) and DNS timeouts are common. Re-running the same file usually resolves these on the second pass. |
| **No live-network tests in CI** | All SMTP and DNS calls in tests are fixtures from real captured responses. This makes tests fast and reproducible without an internet connection. |
| **No paid API or VPS used** | The tool is intentionally zero-cost and runs from any PC. Provider blocklists are an inherent trade-off of this approach. |
| **Output file is overwritten** | If you run the tool twice on the same input, the previous output is replaced. Rename your output file if you want to keep it. |
| **Concurrency capped at 4 workers** | Per-domain serialization prevents hammering any single mail server. 4 workers balances speed with politeness. |
