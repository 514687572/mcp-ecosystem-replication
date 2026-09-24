"""Final pre-submission check: run every gate and summarise the result.

Each gate is an independent script, so a failure names the thing to fix. This
driver only reports; it never edits.

Run: python paper/final_check.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

GATES = [
    ("journal compliance (34 items)", "paper/check_jss_compliance.py"),
    ("citation integrity", "paper/check_citations.py"),
    ("number traceability", "paper/check_numbers.py"),
    ("style metrics", "paper/ai_style_check.py"),
    ("rendered layout", "paper/check_layout.py"),
    ("result-table consistency", "paper/check_tables.py"),
]


def run(relative):
    """Run a gate; return (ok, tail of output)."""
    script = os.path.join(ROOT, relative)
    if not os.path.isfile(script):
        return None, "script missing"
    proc = subprocess.run(
        [sys.executable, script], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    return proc.returncode == 0, "\n".join(lines[-4:])


def main():
    print("=" * 78)
    print("FINAL CHECK")
    print("=" * 78)
    failed = []
    for label, script in GATES:
        ok, tail = run(script)
        if ok is None:
            status = "SKIP"
        else:
            status = "PASS" if ok else "FAIL"
        if status == "FAIL":
            failed.append(label)
        print("\n%-32s %s" % (label, status))
        for line in tail.splitlines():
            print("    %s" % line)

    # Manuscript facts worth having in the log one last time.
    pdf = os.path.join(HERE, "latex", "mcp-ecosystem.pdf")
    tex = os.path.join(HERE, "latex", "mcp-ecosystem.tex")
    if os.path.isfile(pdf) and os.path.isfile(tex):
        import fitz
        with open(tex, encoding="utf-8") as fh:
            body = fh.read()
        doc = fitz.open(pdf)
        print("\n%-32s %d pages" % ("rendered manuscript", doc.page_count))
        print("%-32s %d" % ("tables", len(re.findall(r"\\begin\{table", body))))
        print("%-32s %d" % ("figures", len(re.findall(r"\\begin\{figure", body))))
        print("%-32s %d" % ("references cited",
                            len(set(re.findall(r"\\cite[a-z]*\{([^}]*)\}", body)))))

    print("\n" + "=" * 78)
    if failed:
        print("FAILED GATES: %s" % ", ".join(failed))
        return 1
    print("all gates passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
