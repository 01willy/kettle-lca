"""TianGong (ILCD-JSON) process datasets: retrieval through the TianGong CLI and GWP characterization.

Retrieval requires a TianGong CLI session (`tiangong-lca auth login`). Retrieved datasets are cached
under data/external/tiangong/ (not committed); the repository records only IDs and versions.
"""

import csv
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/external/tiangong"
CLI = os.environ.get("TIANGONG_CLI", "tiangong-lca")


def text(node, lang="en"):
    if node is None:
        return ""
    if isinstance(node, dict):
        node = [node]
    pick = [n for n in node if isinstance(n, dict) and n.get("@xml:lang") == lang] or node
    if not pick:
        return ""
    return pick[0].get("#text", "") if isinstance(pick[0], dict) else str(pick[0])


def get_process(process_id, version):
    """Process dataset (processDataSet dict), from cache or the TianGong CLI."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{process_id}_{version}.json"
    if not path.exists():
        res = subprocess.run([CLI, "process", "get", "--id", process_id, "--version", version, "--json"],
                             capture_output=True, text=True, timeout=120, check=True)
        path.write_text(res.stdout, encoding="utf-8")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("data", "row", "process"):
        if isinstance(data, dict) and key in data:
            data = data[key]
    if isinstance(data, list):
        data = data[0]
    if "json" in data:
        data = data["json"]
    return data["processDataSet"]


def exchanges(pds):
    """List of (internal id, direction, amount, flow name, flow kind, flow id)."""
    ex = pds["exchanges"]["exchange"]
    ex = ex if isinstance(ex, list) else [ex]
    out = []
    for e in ex:
        ref = e["referenceToFlowDataSet"]
        uri = ref.get("@uri", "")
        kind = "elementary" if "Elementary" in uri else ("product" if "Product" in uri else
                                                           ("waste" if "Waste" in uri else "unknown"))
        out.append((str(e.get("@dataSetInternalID")), e.get("exchangeDirection"), float(e.get("meanAmount", 0)),
                    text(ref.get("common:shortDescription")), kind, ref.get("@refObjectId")))
    return out


def reference_amount(pds):
    ref = str(pds["processInformation"]["quantitativeReference"]["referenceToReferenceFlow"])
    for iid, _, amount, *_ in exchanges(pds):
        if iid == ref:
            return amount
    raise KeyError("reference exchange not found")


def load_cf_map(path=ROOT / "data/tiangong_gwp_map.csv"):
    with open(path, encoding="utf-8") as fh:
        return {r["tiangong_flow_name"].lower(): float(r["gwp100_ar6"]) for r in csv.DictReader(fh)}


def direct_gwp(pds, cf_map):
    """GWP100 of the elementary outputs per unit of reference flow; also unmatched air-emission names."""
    total, unmatched = 0.0, []
    for _, direction, amount, name, kind, _ in exchanges(pds):
        if direction != "Output" or kind == "product":
            continue
        cf = cf_map.get(name.lower())
        if cf is None:
            unmatched.append(name)
            continue
        total += cf * amount
    return total / reference_amount(pds), sorted(set(unmatched))
