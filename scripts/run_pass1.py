"""Pass 1: GWP100 of one packaged BC1 kettle from the USLCI (Commons Merged) package.

Usage: python scripts/run_pass1.py
Inputs : data/kettle-bom.csv, data/foreground_model.csv,
         data/external/uslci/commons_merged_jsonld.zip
Outputs: results/pass1/*.csv, *.json
"""

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kettle_lca.olca import Package, System, ref_exchange  # noqa: E402

PACKAGE = ROOT / "data/external/uslci/commons_merged_jsonld.zip"
OUT = ROOT / "results/pass1"
METHOD = "IPCC"
BASE_CATEGORY = "AR6-100"
ALT_CATEGORY = "AR6-100 Net Biogenic"
MOLDING = "Injection molding; rigid polypropylene part"
PP_RESIN = "Polypropylene, PP; virgin resin"
RESIN_PER_PART = 1.034  # kg PP resin per kg molded part, from the USLCI molding dataset


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pkg = Package(PACKAGE)
    system = System(pkg)
    cats = {c["name"]: c for c in pkg.data["lcia_categories"].values()}
    cf = {name: system.cf_vectors(cats[name]) for name in (BASE_CATEGORY, ALT_CATEGORY)}

    def unit_demand(name):
        p = pkg.find(name)
        return {system.column(p): 1.0 / pkg.ref_amount(ref_exchange(p))}, p

    def demand_for(row):
        """Demand vector (column -> amount) for one foreground row."""
        amount = float(row["amount"])
        name = row["dataset_name"]
        if name.endswith("(excluding resin input)"):
            part, _ = unit_demand(MOLDING)
            resin, _ = unit_demand(PP_RESIN)
            d = {j: v * amount for j, v in part.items()}
            for j, v in resin.items():
                d[j] = d.get(j, 0.0) - v * amount * RESIN_PER_PART
            return d
        d, _ = unit_demand(name)
        return {j: v * amount for j, v in d.items()}

    rows = list(csv.DictReader(open(ROOT / "data/foreground_model.csv", encoding="utf-8")))
    total_demand = {}
    contributions = []
    for row in rows:
        rec = {k: row[k] for k in ("item_id", "bom_material", "stage", "amount", "unit", "dataset_name", "status")}
        if row["status"] == "pending" or not row["dataset_name"]:
            rec.update(gwp100_kg=None, gwp100_net_biogenic_kg=None, dataset_id="", dataset_version="", geography="")
            contributions.append(rec)
            continue
        d = demand_for(row)
        s = system.solve(d)
        for name, key in ((BASE_CATEGORY, "gwp100_kg"), (ALT_CATEGORY, "gwp100_net_biogenic_kg")):
            c_out, c_in = cf[name]
            rec[key] = float(c_out @ (system.B_out @ s) + c_in @ (system.B_in @ s))
        base_name = MOLDING if row["dataset_name"].endswith("(excluding resin input)") else row["dataset_name"]
        p = pkg.find(base_name)
        rec.update(dataset_id=p["@id"], dataset_version=p.get("version", ""),
                   geography=(p.get("location") or {}).get("name", ""))
        contributions.append(rec)
        for j, v in d.items():
            total_demand[j] = total_demand.get(j, 0.0) + v

    # Whole-system result for checks, process contributions and unresolved links.
    s_total = system.solve(total_demand)
    c_out, c_in = cf[BASE_CATEGORY]
    total_matrix = float(c_out @ (system.B_out @ s_total) + c_in @ (system.B_in @ s_total))
    total_items = sum(r["gwp100_kg"] for r in contributions if r["gwp100_kg"] is not None)
    by_column = system.impacts_by_column(s_total, c_out, c_in)
    order = np.argsort(-np.abs(by_column))
    with open(OUT / "process_contributions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "process", "product", "geography", "gwp100_kg", "share_of_calculated_total"])
        for rank, j in enumerate(order[:25], 1):
            pid, fid = system.techflows[j]
            p = pkg.processes[pid]
            w.writerow([rank, p["name"], pkg.flows.get(fid, {}).get("name", fid),
                        (p.get("location") or {}).get("name", ""), f"{by_column[j]:.6f}",
                        f"{by_column[j] / total_matrix:.4f}"])
    unres = system.U @ s_total
    with open(OUT / "unresolved_links.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["flow", "reason", "amount_in_supply_chain", "unit"])
        for i in np.argsort(-np.abs(unres))[:40]:
            if abs(unres[i]) < 1e-12:
                continue
            fid, name, reason = system.unresolved_keys[i]
            unit = (pkg.flows.get(fid, {}).get("flowProperties") or [{}])[0]
            w.writerow([name, reason, f"{unres[i]:.6g}", pkg.flows.get(fid, {}).get("refUnit", "")])

    fields = ["item_id", "bom_material", "stage", "amount", "unit", "status", "gwp100_kg",
              "gwp100_net_biogenic_kg", "dataset_name", "dataset_id", "dataset_version", "geography"]
    with open(OUT / "contributions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in contributions:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})

    bom = list(csv.DictReader(open(ROOT / "data/kettle-bom.csv", encoding="utf-8")))
    mass = {"Kettle": 0.0, "Packaging": 0.0}
    for b in bom:
        mass[b["scope"]] += float(b["finished_mass_g"])
    materials = [r for r in contributions if r["stage"] == "material"]
    calc_mass = sum(float(r["amount"]) for r in materials if r["gwp100_kg"] is not None and r["item_id"] != "M02")
    calc_mass += 0.35025  # PP parts (resin amount includes the 3.4 % molding loss)
    checks = {
        "bom_mass_g": {"kettle": mass["Kettle"], "packaging": mass["Packaging"],
                        "expected": [723.0, 137.8],
                        "pass": abs(mass["Kettle"] - 723.0) < 1e-9 and abs(mass["Packaging"] - 137.8) < 1e-9},
        "contribution_sum_kg": {"sum_of_items": total_items, "joint_matrix_solution": total_matrix,
                                 "pass": abs(total_items - total_matrix) < 1e-9 * max(1.0, abs(total_matrix))},
        "material_mass_covered_g": round(calc_mass * 1000, 2),
        "material_mass_share_covered": round(calc_mass * 1000 / 860.8, 4),
        "unresolved_exchanges_in_package": len(system.unresolved),
        "multi_output_columns": len(system.techflows) - len({pid for pid, _ in system.techflows}),
    }
    summary = {
        "run": "pass1",
        "status": "partial: pending items are not calculated and are not zero",
        "declared_unit": "One manufactured and packaged BC1 1 L plastic electric kettle at the factory gate",
        "database": {"name": "Federal LCA Commons, Commons Merged (includes USLCI)",
                     "api_token": "repository_Federal_LCA_Commons@commons_merged@4a8936c4f699b98c5dd5e75757a726de4adc4150",
                     "file": str(PACKAGE.relative_to(ROOT)), "sha256": sha256(PACKAGE)},
        "method": {"name": METHOD, "category": BASE_CATEGORY,
                   "alternative_category": ALT_CATEGORY, "unit": "kg CO2 eq"},
        "gwp100_calculated_items_kg": total_items,
        "gwp100_net_biogenic_calculated_items_kg": sum(
            r["gwp100_net_biogenic_kg"] for r in contributions if r["gwp100_net_biogenic_kg"] is not None),
        "pending_items": [r["item_id"] + " " + r["bom_material"] + " (" + r["stage"] + ")"
                          for r in contributions if r["gwp100_kg"] is None],
        "checks": checks,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
