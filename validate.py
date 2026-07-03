"""Vmail validator CLI.

Usage:  python validate.py Raw_Email.xlsx
Output: Raw_Email_validated.xlsx (input file is never modified)
"""
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby
from pathlib import Path

from vmail.catch_all import check_catch_all
from vmail.classify import flags
from vmail.dns_check import resolve_domain
from vmail.excel_io import read_emails, write_results
from vmail.provider import blocks_home_ip, fingerprint
from vmail.smtp_probe import probe
from vmail.syntax import check_syntax
from vmail.verdict import Evidence, Verdict, decide

MAX_WORKERS = 4


def validate_one(email: str) -> dict:
    try:
        return _validate(email)
    except Exception:
        return _to_row(
            Verdict("ERROR", "MANUAL", 0,
                    f"Unexpected error: {traceback.format_exc(limit=1).strip()}"),
            provider="", fl=None, catch=None, code=None, evidence_msg=None,
        )


def _validate(email: str) -> dict:
    syn = check_syntax(email)
    if not syn.ok:
        verdict = decide(Evidence(
            syntax_ok=False, syntax_reason=syn.reason, suggestion=syn.suggestion,
            domain_exists=False, dns_reason=None, provider="", provider_blocked=False,
            probe_outcome=None, probe_code=None, probe_message=None,
            catch_all=None, flags=None,
        ))
        return _to_row(verdict, "", None, None, None, None)

    fl = flags(syn.normalized)
    dns_result = resolve_domain(syn.domain)
    provider = fingerprint(dns_result.mx_hosts) if dns_result.exists else ""
    blocked = blocks_home_ip(provider)

    probe_result = None
    catch = None
    if dns_result.exists and not blocked:
        probe_result = probe(syn.normalized, dns_result.mx_hosts)
        if probe_result.outcome == "ACCEPTS":
            catch = check_catch_all(syn.domain, dns_result.mx_hosts)

    verdict = decide(Evidence(
        syntax_ok=True, syntax_reason=None, suggestion=syn.suggestion,
        domain_exists=dns_result.exists, dns_reason=dns_result.reason,
        provider=provider, provider_blocked=blocked,
        probe_outcome=probe_result.outcome if probe_result else None,
        probe_code=probe_result.code if probe_result else None,
        probe_message=probe_result.message if probe_result else None,
        catch_all=catch, flags=fl,
    ))
    return _to_row(
        verdict, provider, fl, catch,
        probe_result.code if probe_result else None,
        probe_result.message if probe_result else None,
    )


def _to_row(verdict: Verdict, provider, fl, catch, code, evidence_msg) -> dict:
    return {
        "Status": verdict.status,
        "Safe_To_Send": verdict.safe_to_send,
        "Confidence": verdict.confidence,
        "Reason": verdict.reason,
        "Provider": provider,
        "Role_Account": fl.role if fl else None,
        "Disposable": fl.disposable if fl else None,
        "Free_Provider": fl.free if fl else None,
        "Catch_All": catch,
        "SMTP_Code": code,
        "SMTP_Evidence": (evidence_msg or "")[:500] or None,
    }


def _network_sanity_check(rows: list[dict]) -> None:
    """If all collected unique domains (up to 3) all DNS-timeout, the network is down."""
    seen = []
    for row in rows:
        syn = check_syntax(row["_email"])
        if syn.ok and syn.domain not in seen:
            seen.append(syn.domain)
        if len(seen) == 3:
            break
    if len(seen) == 0:
        return
    if all(resolve_domain(d).reason == "DNS_TIMEOUT" for d in seen):
        sys.exit("ERROR: DNS is unreachable — check your internet connection. "
                 "No output written.")


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        sys.exit("Usage: python validate.py <input.xlsx>")
    in_path = Path(argv[0])
    if not in_path.exists():
        sys.exit(f"ERROR: file not found: {in_path}")
    out_path = in_path.with_name(f"{in_path.stem}_validated.xlsx")

    rows, headers = read_emails(str(in_path))
    print(f"Read {len(rows)} emails from {in_path.name}")
    _network_sanity_check(rows)

    # Group rows by domain so one server is never probed in parallel.
    def _domain(row):
        email = row["_email"]
        return email.rsplit("@", 1)[-1].lower() if "@" in email else ""

    rows_sorted = sorted(rows, key=_domain)
    groups = [list(g) for _, g in groupby(rows_sorted, key=_domain)]

    done = 0

    def _process_group(group):
        nonlocal done
        for row in group:
            row.update(validate_one(row["_email"]))
            done += 1
            print(f"[{done}/{len(rows)}] {row['_email']} -> {row['Status']}")

    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        futures = [pool.submit(_process_group, group) for group in groups]
        for future in futures:
            future.result()
        pool.shutdown(wait=True)
    except KeyboardInterrupt:
        pool.shutdown(wait=False, cancel_futures=True)
        print("\nInterrupted — writing partial results...")
        for row in rows:
            row.setdefault("Status", "TEMPORARY")
            row.setdefault("Safe_To_Send", "RETRY")
            row.setdefault("Confidence", 0)
            row.setdefault("Reason", "Run interrupted before this row was checked")

    try:
        write_results(str(out_path), rows, headers)
    except PermissionError:
        # Target is locked (commonly: open in Excel). Fall back to a
        # uniquely-named file rather than discarding a completed run.
        alt = out_path.with_name(f"{out_path.stem}_{os.getpid()}{out_path.suffix}")
        print(f"\n{out_path.name} is locked (open in Excel?) — writing {alt.name} instead")
        write_results(str(alt), rows, headers)
        out_path = alt
    print(f"\nDone. Results: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
