"""Pass 2 extras for the report (processing only).

Outputs (results/pass2/):
  technosphere_pattern.npz  nonzero pattern of A, reverse Cuthill-McKee order
  gas_breakdown.csv         GWP100 by greenhouse gas (USLCI part + TianGong items)
  sensitivity.csv           result change when one decision is changed (pass-2 baseline)
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse.csgraph import reverse_cuthill_mckee

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kettle_lca import tiangong as tg  # noqa: E402
from kettle_lca.olca import Package, System  # noqa: E402

OUT = ROOT / "results/pass2"


def gases(pds, cf):
    """GWP100 per reference unit, split by gas name."""
    out = {}
    ref = tg.reference_amount(pds)
    for _, direction, amount, name, kind, _ in tg.exchanges(pds):
        if direction != "Output" or kind == "product" or name.lower() not in cf:
            continue
        key = "CO2 (fossil)" if name.lower().startswith("carbon dioxide") else (
            "CH4" if name.lower().startswith("methane") else ("N2O" if "nitrous" in name.lower() else "Other"))
        out[key] = out.get(key, 0.0) + cf[name.lower()] * amount / ref
    return out


def main():
    s2 = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    pkg = Package(ROOT / "data/external/uslci/commons_merged_jsonld.zip")
    S = System(pkg)
    A = S.A.tocsr()
    pattern = (A + A.T).tocsr()
    perm = reverse_cuthill_mckee(pattern, symmetric_mode=True)
    Ap = A[perm][:, perm].tocoo()
    np.savez_compressed(OUT / "technosphere_pattern.npz", row=Ap.row, col=Ap.col, n=A.shape[0], nnz=A.nnz)

    cf = tg.load_cf_map()
    t = s2["tiangong"]
    cu = gases(tg.get_process(*t["datasets"]["copper"]), cf)
    br_direct = gases(tg.get_process(*t["datasets"]["brass"]), cf)
    grid = gases(tg.get_process(*t["datasets"]["grid"]), cf)
    inp = t["brass_inputs_per_kg"]
    total = {}
    for r in csv.DictReader(open(ROOT / "results/pass1/gas_breakdown.csv", encoding="utf-8")):
        key = r["gas"] if r["gas"] in ("CO2 (fossil)", "CH4", "N2O") else "Other"
        total[key] = total.get(key, 0.0) + float(r["gwp100_kg"])
    for gas, v in cu.items():
        total[gas] = total.get(gas, 0.0) + 0.015 * v + 0.02025 * inp["cathode copper"] * v
    for gas, v in br_direct.items():
        total[gas] = total.get(gas, 0.0) + 0.02025 * v
    for gas, v in grid.items():
        total[gas] = total.get(gas, 0.0) + 0.02025 * inp["electricity_kwh"] * 3.6 * v
    base = s2["gwp100_calculated_items_kg"]
    with open(OUT / "gas_breakdown.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["gas", "gwp100_kg", "share"])
        for k in ("CO2 (fossil)", "CH4", "N2O", "Other"):
            w.writerow([k, f"{total.get(k, 0.0):.6f}", f"{total.get(k, 0.0) / base:.4f}"])

    # Decision changes act on USLCI datasets only; their absolute effect is unchanged from pass 1.
    p1 = {r["scenario"]: r for r in csv.DictReader(open(ROOT / "results/pass1/sensitivity.csv", encoding="utf-8"))}
    labels = {
        "scrap_cutoff": ("D6", "Stainless scrap burden-free (cut-off)"),
        "board_biogenic": ("D7", "Board-mill CO2 treated as biogenic"),
        "both": ("D6+D7", "Both changes"),
        "method_ar5": ("D5", "IPCC AR5 GWP100"),
        "method_net_biogenic": ("D5", "AR6 GWP100, net biogenic"),
    }
    with open(OUT / "sensitivity.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "decision", "label", "gwp100_kg", "difference_kg", "difference_pct"])
        w.writerow(["baseline", "", "Baseline (pass 2)", f"{base:.6f}", "0", "0"])
        for key, (dec, label) in labels.items():
            d = float(p1[key]["difference_kg"])
            w.writerow([key, dec, label, f"{base + d:.6f}", f"{d:.6f}", f"{d / base * 100:.2f}"])
    print("done", {k: round(v, 4) for k, v in total.items()}, "base", round(base, 4))


if __name__ == "__main__":
    main()
