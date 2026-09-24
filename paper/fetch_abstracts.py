"""Fetch abstracts for the works used in the Discussion comparison.

The Discussion claims that a finding agrees with, or departs from, prior work.
Those claims must be grounded in what the prior work actually reports, so the
abstracts are fetched and stored here rather than paraphrased from memory.
"""
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))

DOIS = {
    "decan2019": "10.1007/s10664-017-9589-y",
    "abdalkareem2020": "10.1007/s10664-019-09792-9",
    "cogo2021downgrades": "10.1109/tse.2019.2952130",
    "cogo2021sameday": "10.1007/s10664-021-09980-6",
    "samaana2025": "10.1007/s10664-025-10648-8",
    "li2023yanked": "10.1109/tse.2022.3152148",
    "fan2020apidoc": "10.1007/s11432-019-9880-8",
    "meng2019apidoc": "10.1145/3358931.3358937",
    "hora2016apievolution": "10.1007/s11219-016-9344-4",
    "li2022ossara": "10.1109/ms.2022.3163011",
    "khan2026promptinjection": "10.3390/computers15090570",
    "yagoubi2026agentleak": "10.1109/access.2026.3704541",
    "javastreams2023": "10.1002/spe.3213",
    "readme2024": "10.1002/spe.3390",
}


def inv_to_text(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def main():
    session = requests.Session()
    session.trust_env = False
    session.proxies = {"http": None, "https": None}
    out = {}
    for key, doi in DOIS.items():
        data = None
        for attempt in range(3):
            try:
                r = session.get("https://api.openalex.org/works/doi:" + doi,
                                timeout=45, headers={"User-Agent": "mcp-study"})
                if r.status_code == 200:
                    data = r.json()
                    break
            except Exception:
                pass
            time.sleep(4)
        if not data:
            print("### %s  FETCH FAILED" % key)
            continue
        abstract = inv_to_text(data.get("abstract_inverted_index"))
        out[key] = {"doi": doi, "title": data.get("title"),
                    "abstract": abstract}
        print("\n### %s" % key)
        print("    %s" % (data.get("title") or "")[:100])
        print("    %s" % (abstract[:900] or "(no abstract indexed)"))
        time.sleep(1)
    path = os.path.join(HERE, "reference_abstracts.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nwrote %s (%d abstracts)" % (path, len(out)))


if __name__ == "__main__":
    sys.exit(main())
