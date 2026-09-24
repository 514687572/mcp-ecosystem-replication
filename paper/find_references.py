"""Search Crossref for real works to cite, and print verified metadata.

Nothing is written from memory: the script prints title, authors, venue, year,
volume, pages and DOI exactly as the record returns them, so the bibliography
can be assembled from verified rows only.
"""
import json
import sys
import time

import requests

TOPICS = [
    "Model Context Protocol large language model tools",
    "LLM agent tool selection benchmark",
    "tool calling large language model empirical",
    "npm ecosystem dependency evolution empirical study",
    "PyPI package ecosystem empirical study",
    "API documentation quality empirical study developers",
    "software package registry mining study",
    "agent security tool use prompt injection",
    "MCP server security analysis",
    "JSON schema API design quality",
    "software supply chain transparency SBOM",
    "large language model agent evaluation framework",
    "plugin ecosystem empirical study",
    "chatbot plugin safety evaluation",
    "open source project abandonment sustainability",
]


def search(term, rows=4):
    session = requests.Session()
    session.trust_env = False
    session.proxies = {"http": None, "https": None}
    for attempt in range(3):
        try:
            r = session.get(
                "https://api.crossref.org/works",
                params={"query.bibliographic": term, "rows": rows,
                        "filter": "from-pub-date:2015-01-01,type:journal-article",
                        "mailto": "chenjunan.aiden@gmail.com"},
                timeout=45,
            )
            r.raise_for_status()
            return r.json()["message"]["items"]
        except Exception:
            time.sleep(4)
    return []


def main():
    out = []
    for term in TOPICS:
        items = search(term)
        print("\n### %s  (%d hits)" % (term, len(items)))
        for it in items:
            title = " ".join(it.get("title") or [])
            if not title:
                continue
            authors = " and ".join(
                ("%s, %s" % (a.get("family", ""), a.get("given", ""))).strip(", ")
                for a in (it.get("author") or [])[:8]
            )
            venue = (it.get("container-title") or [""])[0]
            year = ((it.get("published") or {}).get("date-parts")
                    or [[None]])[0][0]
            row = {
                "query": term, "title": title, "authors": authors,
                "venue": venue, "year": year, "volume": it.get("volume"),
                "issue": it.get("issue"), "pages": it.get("page"),
                "doi": it.get("DOI"),
            }
            out.append(row)
            print("  [%s] %s" % (year, title[:88]))
            print("       %s | %s" % (venue[:60], row["doi"]))
            print("       %s" % authors[:120])
        time.sleep(1.5)
    with open("paper/reference_candidates.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nwrote paper/reference_candidates.json (%d rows)" % len(out))


if __name__ == "__main__":
    sys.exit(main())
