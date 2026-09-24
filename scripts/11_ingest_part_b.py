"""Step 11 — ingest the human Part B (security) codes.

Input : the coded worksheet returned by the coder (results/validation/T2.txt)
Output: results/validation/part_b_codes.csv       normalised copy
        results/validation/part_b_summary.csv     headline metrics for RQ2
        results/validation/part_b_crosstabs.csv   credential-handling cross-tabs
        results/validation/part_b_by_transport.csv

Values the coder added that are not in the codebook enumeration (x402,
prepaid_credit, read_only, ...) are preserved verbatim rather than coerced:
they are findings about the ecosystem, not coding errors.
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")

CREDENTIAL_AUTH = {"api_key", "oauth", "bearer_token", "basic", "jwt", "hmac",
                   "env_var", "browser_session"}
PAYMENT_AUTH = {"x402", "prepaid_credit"}


def classify_evidence(text):
    """Reduce the free-text evidence column to a comparable source category."""
    text = (text or "").strip()
    if not text:
        return "none"
    if text.startswith("env vars:"):
        return "manifest_env_vars"
    if text.startswith("描述:"):
        return "manifest_description"
    if "无 auth 声明" in text:
        return "no_statement"
    if text.startswith("本地"):
        return "local_configuration"
    return "other"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", default=os.path.join(OUT_DIR, "T2.txt"))
    args = parser.parse_args()

    config.load()
    with open(args.codes, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    normalised = []
    for row in rows:
        row = {k: (v or "").strip() for k, v in row.items()}
        family = (
            "credential"
            if row["auth_mechanism"] in CREDENTIAL_AUTH
            else "payment"
            if row["auth_mechanism"] in PAYMENT_AUTH
            else row["auth_mechanism"] or "unknown"
        )
        normalised.append(
            {
                "item_id": row["item_id"],
                "server_name": row["server_name"],
                "transport_class": row["transport_class"],
                "auth_mechanism": row["auth_mechanism"],
                "auth_family": family,
                "auth_evidence": row["auth_evidence"],
                "auth_evidence_source": classify_evidence(row["auth_evidence"]),
                "requires_user_secret": row["requires_user_secret"],
                "secret_documented_as_secret": row["secret_documented_as_secret"],
                "scope_breadth": row["scope_breadth"],
                "destructive_capability": row["destructive_capability"],
                "write_capability": row["write_capability"],
                "readme_warns_about_risk": row["readme_warns_about_risk"],
                "notes": row.get("notes", ""),
            }
        )

    codes_path = os.path.join(OUT_DIR, "part_b_codes.csv")
    with open(codes_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(normalised[0].keys()))
        writer.writeheader()
        writer.writerows(normalised)

    total = len(normalised)

    def count(predicate):
        return sum(1 for r in normalised if predicate(r))

    def pct(n):
        return round(100.0 * n / total, 1) if total else 0.0

    known_auth = count(lambda r: r["auth_mechanism"] not in ("", "unclear"))
    cred_auth = count(lambda r: r["auth_family"] == "credential")
    pay_auth = count(lambda r: r["auth_family"] == "payment")
    needs_secret = count(lambda r: r["requires_user_secret"] == "yes")
    needs_secret_not_flagged = count(
        lambda r: r["requires_user_secret"] == "yes"
        and r["secret_documented_as_secret"] == "no"
    )
    needs_secret_unclear_flag = count(
        lambda r: r["requires_user_secret"] == "yes"
        and r["secret_documented_as_secret"] == "unclear"
    )
    writes = count(lambda r: r["write_capability"] == "yes")
    destructive = count(lambda r: r["destructive_capability"] == "yes")
    broad = count(lambda r: r["scope_breadth"] == "broad")

    summary = [
        ("servers coded", total),
        ("authentication mechanism identified", known_auth),
        ("authentication mechanism identified (%)", pct(known_auth)),
        ("authentication mechanism unclear (%)",
         pct(count(lambda r: r["auth_mechanism"] == "unclear"))),
        ("no authentication required", count(lambda r: r["auth_mechanism"] == "none")),
        ("credential-based authentication", cred_auth),
        ("payment-based gate (x402 / prepaid credit)", pay_auth),
        ("requires the user to supply a secret", needs_secret),
        ("... of those: secret NOT flagged as secret", needs_secret_not_flagged),
        ("... of those: secret flag left unclear", needs_secret_unclear_flag),
        ("servers with write capability", writes),
        ("servers with destructive capability", destructive),
        ("servers with broad scope", broad),
        ("broad scope AND write capability",
         count(lambda r: r["scope_breadth"] == "broad"
               and r["write_capability"] == "yes")),
    ]
    summary_path = os.path.join(OUT_DIR, "part_b_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)

    def crosstab(column):
        values = sorted({r[column] for r in normalised})
        counts = {v: count(lambda r, v=v: r[column] == v) for v in values}
        return values, counts

    crosstabs = []
    for column in ("auth_mechanism", "scope_breadth", "write_capability",
                   "destructive_capability", "auth_evidence_source",
                   "secret_documented_as_secret", "requires_user_secret"):
        values, counts = crosstab(column)
        for value in values:
            crosstabs.append({
                "field": column,
                "value": value,
                "servers": counts[value],
                "share_pct": pct(counts[value]),
            })
    crosstab_path = os.path.join(OUT_DIR, "part_b_crosstabs.csv")
    with open(crosstab_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["field", "value", "servers", "share_pct"])
        writer.writeheader()
        writer.writerows(crosstabs)

    by_transport = []
    for transport in sorted({r["transport_class"] for r in normalised}):
        subset = [r for r in normalised if r["transport_class"] == transport]
        if not subset:
            continue
        n = len(subset)
        by_transport.append({
            "transport_class": transport,
            "servers": n,
            "share_pct": pct(n),
            "auth_identified_pct": round(
                100.0 * sum(1 for r in subset
                            if r["auth_mechanism"] not in ("", "unclear")) / n, 1),
            "no_auth_pct": round(
                100.0 * sum(1 for r in subset
                            if r["auth_mechanism"] == "none") / n, 1),
            "needs_secret_pct": round(
                100.0 * sum(1 for r in subset
                            if r["requires_user_secret"] == "yes") / n, 1),
            "write_capability_pct": round(
                100.0 * sum(1 for r in subset
                            if r["write_capability"] == "yes") / n, 1),
            "broad_scope_pct": round(
                100.0 * sum(1 for r in subset
                            if r["scope_breadth"] == "broad") / n, 1),
        })
    transport_path = os.path.join(OUT_DIR, "part_b_by_transport.csv")
    with open(transport_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(by_transport[0].keys()))
        writer.writeheader()
        writer.writerows(by_transport)

    for metric, value in summary:
        print("  %-52s %s" % (metric, value))
    print("\nauthentication mechanisms:")
    values, counts = crosstab("auth_mechanism")
    for value in values:
        print("  %-24s %3d  (%.1f%%)" % (value, counts[value], pct(counts[value])))
    print("\nwrote results/validation/part_b_{codes,summary,crosstabs,by_transport}.csv")


if __name__ == "__main__":
    main()
