"""Step 18 — assemble the public replication package.

Builds replication/mcp-ecosystem-replication/ from the working tree. The script
is the definition of what is public: running it again reproduces the package
exactly, so the inclusion policy is auditable rather than remembered.

What goes in:  code, configuration, documentation, the seeded sample records,
               every generated result table, the validation worksheets and
               evidence packs, and the manuscript source.
What stays out: the raw registry harvest (the upstream registry is its
               authoritative copy and the file is 131 MB), the HTTP cache,
               credentials, and anything derived from them.
"""
import hashlib
import os
import shutil
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

ROOT = config.PROJECT_ROOT
DEST = os.path.join(ROOT, "replication", "mcp-ecosystem-replication")

INCLUDE_DIRS = [
    ("config", "config"),
    ("src", "src"),
    ("scripts", "scripts"),
    ("docs", "docs"),
    ("results/tables", "results/tables"),
    ("results/validation", "results/validation"),
    ("results/figures", "results/figures"),
    ("paper", "paper"),
    ("data/interim", "data/interim"),
]

# Files whose presence would break the package's own statements, or that are
# internal working documents rather than replication material.
#
#   .env, registry.jsonl        credentials and the raw snapshot
#   HUMAN_TASKS.md              the author's own task list; it quotes a leaked
#                               token prefix and is superseded by the codebooks
#   ACCEPTANCE_ASSESSMENT.md    internal submission strategy: acceptance odds,
#                               venue alternatives, author-profile discussion
#   STYLE_NOTES.md              internal editing notes; the manuscript carries
#                               its own generative-AI declaration
#   SUBMISSION.md               the author's upload checklist
EXCLUDE_NAMES = {
    ".env", "registry.jsonl", "__pycache__", "reference_candidates.json",
    "style_after.json", "style_before.json", "HUMAN_TASKS.md",
    "ACCEPTANCE_ASSESSMENT.md", "STYLE_NOTES.md", "SUBMISSION.md",
    # Elsevier's CAS bundle. These are the publisher's copyrighted files, they
    # are not ours to redistribute, and a reader who wants to rebuild the PDF
    # obtains them from the journal's own template download.
    "cas-common.sty", "cas-dc.cls", "cas-dc-sample.tex", "cas-refs.bib",
    "cas-model2-names.bst", "cas-sc.cls", "cas-sc-sample.tex",
}
EXCLUDE_SUFFIXES = (".pyc", ".aux", ".log", ".blg", ".out", ".bbl", ".abs",
                    ".synctex.gz")

# Text files are normalised to LF before hashing. Without this the manifest
# matches the Windows working tree but not a fresh clone: .gitattributes
# normalises the repository to LF, so every hash would change on checkout and
# the verification step shipped with the package would fail for every user.
TEXT_SUFFIXES = (".py", ".md", ".csv", ".tex", ".bib", ".yaml", ".yml",
                 ".json", ".jsonl", ".cff", ".txt", ".ps1", ".sty", ".cls",
                 ".bst", ".gitattributes", ".gitignore")


def normalise_line_endings(path):
    if not path.endswith(TEXT_SUFFIXES):
        return
    with open(path, "rb") as fh:
        data = fh.read()
    if b"\r\n" not in data:
        return
    with open(path, "wb") as fh:
        fh.write(data.replace(b"\r\n", b"\n"))


def keep(path):
    name = os.path.basename(path)
    if name in EXCLUDE_NAMES:
        return False
    if path.endswith(EXCLUDE_SUFFIXES):
        return False
    if os.path.basename(os.path.dirname(path)) == "__pycache__":
        return False
    return True


def sha256(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def clear_dir(path):
    """Empty a directory without removing the directory itself.

    Two Windows behaviours make this the safer choice. A previous `git init`
    inside the package leaves read-only objects that plain rmtree refuses to
    delete, and Windows can hold a transient handle on a directory after a
    killed process, which makes removing the directory fail even when every
    file inside it is gone. Clearing the contents sidesteps both, and the
    package's own contents are what the manifest enumerates.

    Read-only bits are cleared first. Failures raise rather than pass: a silent
    failure leaves a half-deleted package, which is how a manifest can end up
    listing a file that no longer exists.

    `.git` is preserved. This directory doubles as the working copy that gets
    pushed to the public repository, so clearing it wholesale would destroy the
    very thing the caller is about to commit from.
    """
    if not os.path.isdir(path):
        return
    keep = os.path.abspath(os.path.join(path, ".git"))

    def protected(target):
        target = os.path.abspath(target)
        return target == keep or target.startswith(keep + os.sep)

    # Files, top-down, pruning .git so the walk never descends into it.
    for dirpath, dirnames, filenames in os.walk(path, topdown=True):
        dirnames[:] = [d for d in dirnames
                       if not protected(os.path.join(dirpath, d))]
        for name in filenames:
            target = os.path.join(dirpath, name)
            try:
                os.chmod(target, stat.S_IWRITE)
            except OSError:
                pass
            os.unlink(target)

    # Now the directories are empty; remove them bottom-up, still skipping .git.
    for dirpath, dirnames, _ in os.walk(path, topdown=False):
        if protected(dirpath):
            continue
        for name in dirnames:
            target = os.path.join(dirpath, name)
            if protected(target) or not os.path.isdir(target):
                continue
            if not os.listdir(target):
                os.rmdir(target)


def main():
    clear_dir(DEST)
    if not os.path.isdir(DEST):
        os.makedirs(DEST)

    copied = []
    for src_rel, dst_rel in INCLUDE_DIRS:
        src_root = os.path.join(ROOT, src_rel)
        if not os.path.isdir(src_root):
            continue
        for dirpath, dirnames, filenames in os.walk(src_root):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "cache")]
            for filename in filenames:
                src = os.path.join(dirpath, filename)
                if not keep(src):
                    continue
                rel = os.path.relpath(src, ROOT)
                dst = os.path.join(DEST, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                normalise_line_endings(dst)
                copied.append(rel)

    # Identity files for the repository.
    for name in ("README.md", "CITATION.cff", "LICENSE", "LICENSE-DATA.md",
                 "DATA_SCOPE.md", "ZENODO_METADATA.md", ".gitignore",
                 ".gitattributes", "requirements.txt"):
        src = os.path.join(ROOT, "replication", "templates", name)
        if os.path.isfile(src):
            dst = os.path.join(DEST, name)
            shutil.copy2(src, dst)
            normalise_line_endings(dst)

    workflow = os.path.join(ROOT, "replication", "templates", "reproduce.yml")
    if os.path.isfile(workflow):
        wf_dir = os.path.join(DEST, ".github", "workflows")
        os.makedirs(wf_dir, exist_ok=True)
        shutil.copy2(workflow, os.path.join(wf_dir, "reproduce.yml"))
        normalise_line_endings(os.path.join(wf_dir, "reproduce.yml"))

    # Manifest of every file shipped, so the deposit is verifiable.
    rows = []
    for dirpath, dirnames, filenames in os.walk(DEST):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, DEST).replace("\\", "/")
            if rel == "MANIFEST.csv":
                continue
            rows.append((rel, os.path.getsize(full), sha256(full)))
    rows.sort()
    with open(os.path.join(DEST, "MANIFEST.csv"), "w", encoding="utf-8",
              newline="") as fh:
        fh.write("path,bytes,sha256\n")
        for rel, size, digest in rows:
            fh.write("%s,%d,%s\n" % (rel, size, digest))

    total = sum(r[1] for r in rows)
    print("package: %s" % DEST)
    print("  files : %d" % len(rows))
    print("  bytes : %.1f MB" % (total / 1024.0 / 1024.0))
    print("  excluded: data/raw (registry snapshot), data/cache, .env, "
          "build intermediates")
    for prefix in ("results/tables", "results/validation", "scripts", "paper",
                   "docs", "src"):
        n = sum(1 for r in rows if r[0].startswith(prefix))
        print("    %-22s %4d files" % (prefix, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
