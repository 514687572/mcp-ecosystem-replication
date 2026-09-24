"""Statically extract MCP tool definitions from published package sources.

The registry manifest describes *where* a server lives but not *what tools* it
exposes. Tool definitions only exist in the implementation, so this module
parses the downloaded package source for the registration idioms used by the
official SDKs:

  TypeScript / JavaScript
    server.tool("name", "description", schema, handler)
    server.registerTool("name", { title, description, inputSchema }, handler)
    server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [...] }))
    { name: "...", description: "...", inputSchema: {...} }

  Python
    @mcp.tool()
    @server.tool(name="...", description="...")
    types.Tool(name="...", description="...", inputSchema={...})
    Tool(name="...", description="...", input_schema={...})

Two caveats matter for the paper and are treated as findings rather than
problems: extraction is inherently partial, and the share of servers whose tools
cannot be recovered statically is itself a result about the ecosystem's
inspectability. `extraction_report` reports that share explicitly.
"""
import ast
import json
import os
import re

SOURCE_EXTENSIONS = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
}

# Note: dist/ and build/ are deliberately NOT skipped. Many published npm
# tarballs ship only the compiled output, so excluding them would drop a large
# part of the population for reasons that have nothing to do with the server.
# Minified bundles are skipped separately, where names are usually mangled.
SKIP_DIRS = {
    "node_modules", ".git", "test", "tests", "testdata",
    "__tests__", "__pycache__", ".venv", "venv", "site-packages", "docs",
    "examples", "coverage", ".github", "fixtures", "mocks",
}

SKIP_FILE_SUFFIXES = (".min.js", ".min.mjs", ".map", ".d.ts")

MAX_FILES_PER_PACKAGE = 400
MAX_FILE_BYTES = 400_000

# --- TypeScript / JavaScript -------------------------------------------------

TS_PATTERNS = [
    # server.tool("name", "description", ...)
    ("ts_server_tool", re.compile(
        r"\.\s*(?:tool|registerTool)\s*\(\s*[\"'`](?P<name>[^\"'`]{1,120})[\"'`]"
        r"\s*,\s*[\"'`](?P<description>(?:[^\"'`\\]|\\.){0,900})[\"'`]",
        re.DOTALL)),
    # server.tool("name", { description: "..." }, ...)
    ("ts_server_tool_object", re.compile(
        r"\.\s*(?:tool|registerTool)\s*\(\s*[\"'`](?P<name>[^\"'`]{1,120})[\"'`]"
        r"\s*,\s*\{(?P<body>[^{}]{0,2000}?)\}",
        re.DOTALL)),
    # bare tool object literal in a tools array
    ("ts_tool_literal", re.compile(
        r"\{\s*name\s*:\s*[\"'`](?P<name>[A-Za-z0-9_.\-]{1,120})[\"'`]"
        r"\s*,"
        r"(?P<body>[^{}]{0,2500}?)"
        r"description\s*:\s*[\"'`](?P<description>(?:[^\"'`\\]|\\.){0,900})[\"'`]",
        re.DOTALL)),
]

TS_DESCRIPTION_IN_BODY = re.compile(
    r"description\s*:\s*[\"'`](?P<description>(?:[^\"'`\\]|\\.){0,900})[\"'`]"
)
TS_SCHEMA_IN_BODY = re.compile(
    r"(inputSchema|input_schema|parameters|schema)\s*:", re.IGNORECASE
)

# --- Python ------------------------------------------------------------------

PY_DECORATOR = re.compile(
    r"@\s*(?P<obj>[A-Za-z_][\w\.]*)\s*\.\s*tool\s*\((?P<args>[^)]{0,600})\)",
    re.DOTALL,
)
PY_DEF_AFTER_DECORATOR = re.compile(
    r"\n\s*(?:async\s+)?def\s+(?P<name>[A-Za-z_][\w]*)", re.DOTALL
)
PY_DOCSTRING = re.compile(r'^\s*(?:r?"""(?P<d1>.*?)"""|\'\'\'(?P<d2>.*?)\'\'\')',
                          re.DOTALL)
# Docstring that follows a full (possibly multi-line) def signature.
PY_DOCSTRING_AFTER_DEF = re.compile(
    r":\s*(?:\r?\n\s*)?(?:r|u)?(?P<q>\"\"\"|''')(?P<body>.*?)(?P=q)",
    re.DOTALL,
)
PY_TOOL_CTOR = re.compile(
    r"\bTool\s*\((?P<body>[^)]{0,1500})\)", re.DOTALL
)
PY_KWARG = {
    "name": re.compile(r"name\s*=\s*[\"'](?P<v>[^\"']{0,160})[\"']"),
    "description": re.compile(r"description\s*=\s*[\"'](?P<v>[^\"']{0,600})[\"']"),
}


def detect_language(path, registry_type=None):
    ext = os.path.splitext(path)[1].lower()
    if ext in SOURCE_EXTENSIONS:
        return SOURCE_EXTENSIONS[ext]
    if registry_type == "pypi":
        return "python"
    if registry_type == "npm":
        return "javascript"
    return None


def iter_source_files(root, registry_type=None, limit=MAX_FILES_PER_PACKAGE):
    """Walk a package directory, skipping vendored and test trees."""
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            language = detect_language(filename, registry_type)
            if not language:
                continue
            if filename.endswith(SKIP_FILE_SUFFIXES):
                continue
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            seen += 1
            if seen > limit:
                return
            yield path, language


def _quoted(text, key):
    pattern = PY_KWARG[key]
    match = pattern.search(text or "")
    return match.group("v") if match else None


def _clean_description(text, limit=900):
    """Unescape JS/Python string escapes so the coder reads real prose."""
    if not text:
        return ""
    text = (text.replace("\\n", " ").replace("\\t", " ")
                .replace("\\r", " ").replace('\\"', '"')
                .replace("\\'", "'").replace("\\\\", "\\"))
    return " ".join(text.split())[:limit]


def extract_from_text(text, language):
    """Return a list of tool records found in one source file."""
    found = []
    if language in ("typescript", "javascript"):
        for pattern_name, pattern in TS_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groupdict()
                name = (groups.get("name") or "").strip()
                if not name:
                    continue
                description = (groups.get("description") or "").strip()
                body = groups.get("body") or ""
                if not description and body:
                    inner = TS_DESCRIPTION_IN_BODY.search(body)
                    if inner:
                        description = inner.group("description").strip()
                found.append(
                    {
                        "tool_name": name,
                        "tool_description": _clean_description(description),
                        "has_schema": bool(TS_SCHEMA_IN_BODY.search(body or text[
                            match.start():match.end() + 400]))
                        if pattern_name == "ts_tool_literal"
                        else bool(TS_SCHEMA_IN_BODY.search(body)),
                        "extraction_pattern": pattern_name,
                    }
                )
    elif language == "python":
        for match in PY_DECORATOR.finditer(text):
            args = match.group("args") or ""
            tail = text[match.end():match.end() + 4000]
            def_match = PY_DEF_AFTER_DECORATOR.search(tail)
            name = _quoted(args, "name")
            if not name and def_match:
                name = def_match.group("name")
            description = _quoted(args, "description")
            if not description and def_match:
                doc = PY_DOCSTRING_AFTER_DEF.search(tail[def_match.end():])
                if doc:
                    description = " ".join(doc.group("body").split())
            if not description:
                after = tail[def_match.end():] if def_match else ""
                doc = PY_DOCSTRING.match(after)
                if doc:
                    description = " ".join(
                        (doc.group("d1") or doc.group("d2") or "").split()
                    )
            if not name:
                continue
            if name.startswith("_"):
                # Private helpers picked up when a decorator and a later def are
                # adjacent; they are not exposed tools.
                continue
            found.append(
                {
                    "tool_name": name,
                    "tool_description": _clean_description(description),
                    "has_schema": False,
                    "extraction_pattern": "py_decorator",
                }
            )
        for match in PY_TOOL_CTOR.finditer(text):
            body = match.group("body") or ""
            name = _quoted(body, "name")
            if not name:
                continue
            found.append(
                {
                    "tool_name": name,
                    "tool_description": (_quoted(body, "description") or "")[:600],
                    "has_schema": bool(
                        re.search(r"(inputSchema|input_schema)", body)
                    ),
                    "extraction_pattern": "py_tool_ctor",
                }
            )
    return found


def extract_from_package(root, server_name, registry_type=None):
    """Extract every tool definition found under a package directory.

    The pattern-based extractor is used for every language, including Python.

    An AST-only Python path was tried and rejected on evidence: re-scoring the
    human Part A codes showed recall falling from 99.7% to 95.3% (85 missed
    tools instead of 5), because the two extractors have complementary blind
    spots rather than one dominating the other. The AST extractor is therefore
    kept in its proper role, as the independent second opinion used by
    scripts/08_validate_extraction.py, not as the production path.
    """
    records = []
    files_scanned = 0
    for path, language in iter_source_files(root, registry_type):
        files_scanned += 1
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        for record in extract_from_text(text, language):
            record.update(
                {
                    "server_name": server_name,
                    "language": language,
                    "source_file": os.path.relpath(path, root),
                }
            )
            records.append(record)
    return records, files_scanned


def dedupe_tools(records):
    """Collapse duplicate tool names within a server, keeping the richest row."""
    best = {}
    for record in records:
        key = (record.get("server_name"), record.get("tool_name"))
        current = best.get(key)
        if current is None:
            best[key] = record
            continue
        score_new = len(record.get("tool_description") or "") + int(
            bool(record.get("has_schema"))
        ) * 50
        score_old = len(current.get("tool_description") or "") + int(
            bool(current.get("has_schema"))
        ) * 50
        if score_new > score_old:
            best[key] = record
    return list(best.values())


def tool_schema_record(records):
    """Per-server summary of tool extraction outcomes."""
    by_server = {}
    for record in records:
        entry = by_server.setdefault(
            record["server_name"],
            {"server_name": record["server_name"], "tools": 0,
             "with_description": 0, "with_schema": 0, "languages": set()},
        )
        entry["tools"] += 1
        if record.get("tool_description"):
            entry["with_description"] += 1
        if record.get("has_schema"):
            entry["with_schema"] += 1
        entry["languages"].add(record.get("language"))
    rows = []
    for entry in by_server.values():
        entry = dict(entry)
        entry["languages"] = "|".join(sorted(x for x in entry["languages"] if x))
        rows.append(entry)
    return rows


def write_jsonl(records, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


# --- independent Python extractor (AST) --------------------------------------
#
# The regex extractor above is intentionally language-agnostic and therefore
# approximate. For Python we can do better: `ast` parses the file properly, so
# the two implementations disagree only where the regex is wrong. That
# disagreement rate is the closest thing to a ground-truth recall estimate that
# can be computed without a human, and it is what
# scripts/08_validate_extraction.py reports.

TOOL_DECORATOR_NAMES = {"tool", "mcp_tool", "server_tool"}


def _decorator_is_tool(decorator):
    """True when a decorator node looks like an MCP tool registration."""
    if isinstance(decorator, ast.Call):
        decorator = decorator.func
    parts = []
    while isinstance(decorator, ast.Attribute):
        parts.append(decorator.attr)
        decorator = decorator.value
    if isinstance(decorator, ast.Name):
        parts.append(decorator.id)
    if not parts:
        return False, None
    return parts[0] in TOOL_DECORATOR_NAMES, parts[0]


def _keyword_str(call, name):
    for keyword in getattr(call, "keywords", []) or []:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            if isinstance(keyword.value.value, str):
                return keyword.value.value
    return None


def extract_python_ast(text):
    """AST-based Python extraction. Returns (records, ok)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], False

    records = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                is_tool, matched = _decorator_is_tool(decorator)
                if not is_tool:
                    continue
                call = decorator if isinstance(decorator, ast.Call) else None
                name = (call and _keyword_str(call, "name")) or node.name
                if name.startswith("_") and node.name.startswith("_"):
                    continue
                description = call and _keyword_str(call, "description")
                if not description:
                    description = ast.get_docstring(node) or ""
                records.append(
                    {
                        "tool_name": name,
                        "tool_description": " ".join(description.split())[:600],
                        "has_schema": False,
                        "extraction_pattern": "py_ast_decorator",
                    }
                )
        elif isinstance(node, ast.Call):
            func = node.func
            label = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else None
            )
            if label not in ("Tool", "ToolSpec"):
                continue
            name = _keyword_str(node, "name")
            if not name:
                continue
            records.append(
                {
                    "tool_name": name,
                    "tool_description": (
                        _keyword_str(node, "description") or ""
                    )[:900],
                    "has_schema": any(
                        kw.arg in ("inputSchema", "input_schema")
                        for kw in (node.keywords or [])
                    ),
                    "extraction_pattern": "py_ast_tool_ctor",
                }
            )
    return records, True
