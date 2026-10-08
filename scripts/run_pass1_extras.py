"""Pass 1 extras: decision sensitivity and greenhouse-gas breakdown (processing only).

Usage: python scripts/run_pass1_extras.py
Outputs: results/pass1/sensitivity.csv, results/pass1/gas_breakdown.csv
"""

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kettle_lca.olca import Package, System, ref_exchange  # noqa: E402

OUT = ROOT / "results/pass1"
MOLDING = "Injection molding; rigid polypropylene part"
PP_RESIN = "Polypropylene, PP; virgin resin"


def main():
    pkg = Package(ROOT / "data/external/uslci/commons_merged_jsonld.zip")
    S = System(pkg)
    cats = {c["name"]: c for c in pkg.data["lcia_categories"].values()}

    def col(name):
        p = pkg.find(name)
        return S.column(p), 1.0 / pkg.ref_amount(ref_exchange(p))

    demand = {}
    for r in csv.DictReader(open(ROOT / "data/foreground_model.csv", encoding="utf-8")):
        if r["status"] == "pending" or not r["dataset_name"]:
            continue
        a = float(r["amount"])
        if r["dataset_name"].endswith("(excluding resin input)"):
            j, k = col(MOLDING); demand[j] = demand.get(j, 0) + k * a
            j, k = col(PP_RESIN); demand[j] = demand.get(j, 0) - k * a * 1.034
        else:
            j, k = col(r["dataset_name"]); demand[j] = demand.get(j, 0) + k * a
    s = S.solve(demand)
    c_out, c_in = S.cf_vectors(cats["AR6-100"])
    base = float(c_out @ (S.B_out @ s) + c_in @ (S.B_in @ s))
    per_col = S.impacts_by_column(s, c_out, c_in)

    def col_of(name):
        return S.column(pkg.find(name))

    scrap = float(per_col[col_of("Steel; stainless 304; scrap")])
    # Containerboard mill: second fossil-CO2 exchange (1.248 kg/kg) reinterpreted as biogenic.
    cb = pkg.find("Containerboard; at mill")
    cb_amount = s[S.column(cb)] * pkg.ref_amount(ref_exchange(cb))
    co2 = sorted(e["amount"] for e in cb["exchanges"]
                 if e["flow"].get("flowType") == "ELEMENTARY_FLOW" and e["flow"]["name"] == "Carbon dioxide"
                 and "emission/air" in (e["flow"].get("category") or ""))
    cb_bio = float(cb_amount * co2[-1])
    c_out_n, c_in_n = S.cf_vectors(cats["AR6-100 Net Biogenic"])
    net_bio = float(c_out_n @ (S.B_out @ s) + c_in_n @ (S.B_in @ s))
    c_out_5, c_in_5 = S.cf_vectors(cats["AR5-100"])
    ar5 = float(c_out_5 @ (S.B_out @ s) + c_in_5 @ (S.B_in @ s))
    rows = [
        ("baseline", "기준 결과 (pass 1)", base),
        ("scrap_cutoff", "스테인리스 스크랩 무부담 (cut-off)", base - scrap),
        ("board_biogenic", "골판지 공장 CO2 1.248 kg/kg를 생물기원으로 해석", base - cb_bio),
        ("both", "위 두 판단 동시 적용", base - scrap - cb_bio),
        ("method_ar5", "특성화 방법 IPCC AR5-100", ar5),
        ("method_net_biogenic", "특성화 범주 AR6-100 Net Biogenic", net_bio),
    ]
    with open(OUT / "sensitivity.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "description", "gwp100_kg", "difference_kg", "difference_pct"])
        for key, desc, val in rows:
            w.writerow([key, desc, f"{val:.6f}", f"{val - base:.6f}", f"{(val - base) / base * 100:.2f}"])

    # Greenhouse-gas breakdown of the baseline.
    g_out, g_in = S.B_out @ s, S.B_in @ s
    groups = {}
    for i, fid in enumerate(S.elem_ids):
        v = c_out[i] * g_out[i] + c_in[i] * g_in[i]
        if v == 0:
            continue
        name = pkg.flows[fid]["name"] if fid in pkg.flows else fid
        key = ("CO2 (fossil)" if name == "Carbon dioxide" else
               "CH4" if name.startswith("Methane") and name in ("Methane", "Methane, fossil", "Methane, biogenic") else
               "N2O" if name == "Nitrous oxide" else "Other (halocarbons etc.)")
        groups[key] = groups.get(key, 0.0) + v
    with open(OUT / "gas_breakdown.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["gas", "gwp100_kg", "share"])
        for k, v in sorted(groups.items(), key=lambda kv: -kv[1]):
            w.writerow([k, f"{v:.6f}", f"{v / base:.4f}"])
    print(open(OUT / "sensitivity.csv", encoding="utf-8").read())
    print(open(OUT / "gas_breakdown.csv", encoding="utf-8").read())


if __name__ == "__main__":
    main()
