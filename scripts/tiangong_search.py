"""Search TianGong processes for the pending BOM materials and summarize candidates.

Requires a TianGong CLI session (tiangong-lca auth login).
Usage: python scripts/tiangong_search.py
Outputs: data/derived/tiangong/search/*.json, data/derived/tiangong/candidates.csv
"""

import csv
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/derived/tiangong"
CLI = os.environ.get("TIANGONG_CLI", "tiangong-lca")
QUERIES = {
    "M07 Brass": ["brass production", "brass rod", "copper zinc alloy"],
    "M08 Copper": ["copper wire", "copper cathode production", "copper production"],
    "M09 Nylon": ["nylon 6 production", "polyamide 6", "nylon 66 production", "polyamide 66"],
    "M10 POM": ["polyoxymethylene", "polyacetal resin", "POM resin"],
    "M11 PC": ["polycarbonate production", "polycarbonate resin"],
    "M12 Silicone": ["silicone rubber production", "silicone", "polydimethylsiloxane"],
}
GHG = re.compile(r"^(carbon dioxide|methane|nitrous oxide|dinitrogen monoxide)", re.I)


def text(node, lang="en"):
    """First text of an ILCD multilang node, preferring `lang`."""
    if node is None:
        return ""
    if isinstance(node, dict):
        node = [node]
    if isinstance(node, list):
        pick = [n for n in node if isinstance(n, dict) and n.get("@xml:lang") == lang] or node
        if not pick:
            return ""
        n = pick[0]
        return n.get("#text", "") if isinstance(n, dict) else str(n)
    return str(node)


def summarize(item):
    pds = item["json"]["processDataSet"]
    info = pds["processInformation"]["dataSetInformation"]
    name = info.get("name", {})
    full = "; ".join(t for t in (text(name.get("baseName")), text(name.get("treatmentStandardsRoutes")),
                                 text(name.get("mixAndLocationTypes"))) if t)
    geo = (pds["processInformation"].get("geography", {}).get("locationOfOperationSupplyOrProduction", {})
           .get("@location", ""))
    year = pds["processInformation"].get("time", {}).get("common:referenceYear", "")
    mv = pds.get("modellingAndValidation", {})
    dtype = mv.get("LCIMethodAndAllocation", {}).get("typeOfDataSet", "")
    exchanges = pds.get("exchanges", {}).get("exchange", [])
    if isinstance(exchanges, dict):
        exchanges = [exchanges]
    n_ghg = 0
    placeholder = False
    for e in exchanges:
        ref = e.get("referenceToFlowDataSet", {})
        fname = text(ref.get("common:shortDescription"))
        if GHG.match(fname):
            n_ghg += 1
        if "placeholder" in text(e.get("generalComment")).lower():
            placeholder = True
    review = mv.get("validation", {}).get("review", {})
    if isinstance(review, list):
        review = review[0] if review else {}
    return {
        "id": item["id"], "version": item.get("version", ""), "name": full, "geography": geo, "year": year,
        "type": dtype, "n_exchanges": len(exchanges), "n_ghg_exchanges": n_ghg,
        "has_lcia_results": "LCIAResults" in pds, "placeholder_amounts": placeholder,
        "review": review.get("@type", "") if isinstance(review, dict) else "",
        "modified_at": item.get("modified_at", ""),
    }


def main():
    (OUT / "search").mkdir(parents=True, exist_ok=True)
    rows = []
    for material, queries in QUERIES.items():
        for q in queries:
            req = OUT / "search" / f"q_{re.sub(r'[^a-z0-9]+', '_', q.lower())}.json"
            req.write_text(json.dumps({"query": q}), encoding="utf-8")
            res = subprocess.run([CLI, "search", "process", "--input", str(req), "--json"],
                                 capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                rows.append({"material": material, "query": q, "name": f"ERROR {res.stderr[:120]}"})
                continue
            (OUT / "search" / f"r_{req.stem[2:]}.json").write_text(res.stdout, encoding="utf-8")
            data = json.loads(res.stdout).get("data", [])
            for item in data:
                rec = summarize(item)
                rec.update(material=material, query=q)
                rows.append(rec)
    fields = ["material", "query", "name", "geography", "year", "type", "n_exchanges", "n_ghg_exchanges",
              "has_lcia_results", "placeholder_amounts", "review", "id", "version", "modified_at"]
    with open(OUT / "candidates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"{len(rows)} candidate rows written")


if __name__ == "__main__":
    main()
