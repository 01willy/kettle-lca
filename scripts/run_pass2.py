"""Pass 2: pass 1 plus TianGong copper and brass (hybrid with USLCI zinc and TianGong China grid).

Usage: python scripts/run_pass2.py   (requires a TianGong CLI session for the first retrieval)
Outputs: results/pass2/contributions.csv, summary.json
"""

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kettle_lca import tiangong as tg  # noqa: E402
from kettle_lca.olca import Package, System, ref_exchange  # noqa: E402

OUT = ROOT / "results/pass2"
COPPER = ("affec622-8421-4bf1-8abf-3b38a85e24da", "01.01.000")
BRASS = ("6bf04663-ad5b-4897-bc56-c3fce1e2ad9d", "01.01.000")
GRID = ("f697c94d-80ff-4043-abf3-77156e5a4b8e", "01.01.012")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cf = tg.load_cf_map()
    cu = tg.get_process(*COPPER)
    cu_gwp, _ = tg.direct_gwp(cu, cf)                      # kg CO2-eq per kg refined copper
    grid = tg.get_process(*GRID)
    grid_gwp = tg.direct_gwp(grid, cf)[0] * 3.6            # per kWh (reference 3.6 MJ)
    br = tg.get_process(*BRASS)
    ref = tg.reference_amount(br)
    inputs = {name: amount / ref for _, d, amount, name, _, _ in tg.exchanges(br) if d == "Input"}
    direct = tg.direct_gwp(br, cf)[0]
    cathode = inputs["Cathode copper"]
    zinc = inputs["Electrolysis Zinc"]
    recycled = inputs["Recycled Copper"]
    elec_kwh = next(v for k, v in inputs.items() if k.startswith("Alternating current")) / 3.6
    pkg = Package(ROOT / "data/external/uslci/commons_merged_jsonld.zip")
    S = System(pkg)
    cats = {c["name"]: c for c in pkg.data["lcia_categories"].values()}
    c_out, c_in = S.cf_vectors(cats["AR6-100"])
    zn = pkg.find("Zinc; special high grade")
    s = S.solve({S.column(zn): 1.0 / pkg.ref_amount(ref_exchange(zn))})
    zn_gwp = float(c_out @ (S.B_out @ s) + c_in @ (S.B_in @ s))
    brass_parts = {"plant direct emissions (TianGong)": direct, "cathode copper (TianGong)": cathode * cu_gwp,
                   "zinc: not calculated (USLCI dataset gives an implausible 0.003 kg CO2-eq/kg)": 0.0,
                   "electricity, China grid (TianGong)": elec_kwh * grid_gwp,
                   "recycled copper (cut-off)": 0.0}
    brass_gwp = sum(brass_parts.values())

    rows = list(csv.DictReader(open(ROOT / "results/pass1/contributions.csv", encoding="utf-8")))
    for r in rows:
        if r["item_id"] == "M08":
            r.update(status="sourced", gwp100_kg=f"{0.015 * cu_gwp:.6f}", dataset_name="TianGong: primary copper production (CN, 2019)",
                     dataset_id=COPPER[0], dataset_version=COPPER[1], geography="CN")
        if r["item_id"] == "M07":
            r.update(status="hybrid (zinc not calculated)", gwp100_kg=f"{0.02025 * brass_gwp:.6f}",
                     dataset_name="TianGong: brass plate and strip H62 (CN-JX, 2023) + TianGong copper + USLCI zinc + TianGong CN grid",
                     dataset_id=BRASS[0], dataset_version=BRASS[1], geography="CN")
    with open(OUT / "contributions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    p1 = json.loads((ROOT / "results/pass1/summary.json").read_text(encoding="utf-8"))
    total = sum(float(r["gwp100_kg"]) for r in rows if r["gwp100_kg"])
    covered_g = p1["checks"]["material_mass_covered_g"] + 15.0 + 20.25
    summary = {
        "run": "pass2", "status": "partial: nylon, POM, PC, silicone and several conversion steps not calculated (not zero)",
        "gwp100_calculated_items_kg": total, "material_mass_covered_g": round(covered_g, 2),
        "material_mass_share_covered": round(covered_g / 860.8, 4),
        "tiangong": {"copper_kgco2e_per_kg": cu_gwp, "brass_kgco2e_per_kg": brass_gwp, "brass_breakdown_per_kg": brass_parts,
                     "china_grid_kgco2e_per_kwh": grid_gwp, "brass_inputs_per_kg": {"cathode copper": cathode, "zinc": zinc,
                     "recycled copper": recycled, "electricity_kwh": elec_kwh}, "uslci_zinc_kgco2e_per_kg": zn_gwp,
                     "datasets": {"copper": COPPER, "brass": BRASS, "grid": GRID}},
        "pending_items": [r["item_id"] + " " + r["bom_material"] + " (" + r["stage"] + ")" for r in rows if not r["gwp100_kg"]],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("gwp100_calculated_items_kg", "material_mass_share_covered")}, indent=1))
    print(json.dumps(summary["tiangong"], indent=1)[:900])


if __name__ == "__main__":
    main()
