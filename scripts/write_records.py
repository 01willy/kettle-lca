"""Write mapping-decisions.csv and run-manifest.json for pass 1 from the package metadata.

Usage: python scripts/write_records.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kettle_lca.olca import Package, ref_exchange  # noqa: E402

API = "https://api.nal.usda.gov/FederalLCACommonsapi/browse/Federal_LCA_Commons/commons_merged/PROCESS/"
RETRIEVED = "2026-10-08T05:51:00Z"
RELEASE = "Commons Merged repository commit 4a8936c4f699b98c5dd5e75757a726de4adc4150"

ALTERNATIVES = {
    "M01": ("Steel; stainless 304; quarto plate (Northern America)",
            "Kettle body is formed from thin sheet; flat rolled coil is closer than quarto plate. Grade 304 assumed (grade not given in BOM)."),
    "M02": ("Recycled postconsumer polypropylene, PP, pellet; Thermoforming; rigid polypropylene part",
            "Virgin resin via the injection molding dataset; recycled content not stated in BOM."),
    "M03": ("none found besides PVC roofing membranes",
            "Only PVC resin dataset in the package."),
    "M04": ("Acrylonitrile; at plant (monomer only)",
            "Copolymer resin dataset matches the material."),
    "M05": ("Linear low-density polyethylene, LLDPE; Stretch film, LLDPE",
            "BOM states LDPE foil; LDPE resin plus generic extrusion."),
    "M06": ("Corrugated product; 100% recycled; at mill",
            "Average production chosen; recycled share not stated in BOM."),
}
QUERIES = {
    "M01": "stainless|steel", "M02": "polypropylene", "M03": "polyvinyl chloride|pvc",
    "M04": "acrylonitrile|abs", "M05": "low density polyethylene|ldpe", "M06": "corrugat|containerboard|cardboard",
    "M07": "brass|zinc", "M08": "copper", "M09": "nylon|polyamide", "M10": "polyoxymethylene|acetal|pom",
    "M11": "polycarbonate", "M12": "silicone|siloxane|silicon",
}
GAPS = {
    "M07": "No physical brass dataset; zinc datasets only. TianGong search pending.",
    "M08": "Only 'Copper; at storage Bridge; USLCI to USEEIO' (monetary, unresolved in Commons Merged). TianGong pending.",
    "M09": "Only Nylon 6/66 USEEIO bridges; grade not decided. TianGong pending.",
    "M10": "No POM dataset. TianGong pending.",
    "M11": "Only Polycarbonate USEEIO bridge. TianGong pending.",
    "M12": "No silicone dataset. TianGong pending.",
}


def main():
    pkg = Package(ROOT / "data/external/uslci/commons_merged_jsonld.zip")
    sha = json.loads((ROOT / "results/pass1/summary.json").read_text())["database"]["sha256"]
    fm = list(csv.DictReader(open(ROOT / "data/foreground_model.csv", encoding="utf-8")))
    header = next(csv.reader(open(ROOT / "docs/course/mapping-decisions.template.csv", encoding="utf-8")))
    out = []
    for r in fm:
        if not r["item_id"].startswith(("M", "C")) or r["item_id"] in ("C08", "C09", "C10"):
            continue
        row = dict.fromkeys(header, "")
        row.update(foreground_input=f"{r['item_id']} {r['bom_material']} ({r['stage']})", quantity=r["amount"],
                   unit=r["unit"], alternatives_considered=ALTERNATIVES.get(r["item_id"], ("", ""))[0],
                   selection_reason=ALTERNATIVES.get(r["item_id"], ("", ""))[1],
                   proxy_or_exact=r["status"], unresolved_gap=GAPS.get(r["item_id"], ""))
        if r["status"] != "pending":
            name = r["dataset_name"].replace(" (excluding resin input)", "")
            p = pkg.find(name)
            ref = ref_exchange(p)
            doc = p.get("processDocumentation") or {}
            row.update(database="USLCI via Federal LCA Commons Commons Merged", release=RELEASE,
                       dataset_id=p["@id"], dataset_version=p.get("version", ""), dataset_name=p["name"],
                       geography=(p.get("location") or {}).get("name", ""),
                       reference_unit=f"{ref['amount']} {ref['unit']['name']}", conversion_factor="1",
                       source_url=API + p["@id"], retrieved_at_utc=RETRIEVED, source_sha256=sha)
            if r["item_id"].startswith("C0") and "excluding resin" in r["dataset_name"]:
                row["selection_reason"] = ("Conversion = molding dataset minus 1.034 kg PP resin per kg part. "
                                           + r["note"])
            elif r["item_id"].startswith("C"):
                row["selection_reason"] = r["note"]
            row["dataset_version"] += f" (valid {(doc.get('validFrom') or '')[:4]}-{(doc.get('validUntil') or '')[:4]})"
        else:
            row.update(database="TianGong (pending)", alternatives_considered=f"USLCI query: {QUERIES[r['item_id']]}")
        out.append(row)
    with open(ROOT / "mapping-decisions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(out)

    summary = json.loads((ROOT / "results/pass1/summary.json").read_text())
    contrib = list(csv.DictReader(open(ROOT / "results/pass1/contributions.csv", encoding="utf-8")))
    manifest = json.loads((ROOT / "docs/course/run-manifest.template.json").read_text())
    manifest.update(
        student_alias="01willy", run_label="pass1 (preliminary, before independent run)",
        run_date_utc="2026-10-08", codex_model_displayed="not used; Claude Code with claude-opus-5-5",
        codex_settings_known={"tool": "Claude Code (VS Code extension)", "model": "claude-opus-5-5"},
        manufacturing_geography="not decided; pass 1 uses U.S. background data (USLCI)",
        characterization_method={"name": "IPCC (FEDEFL-mapped), category AR6-100", "version": "01.04.000",
                                 "time_horizon_years": 100,
                                 "source_url": "https://doi.org/10.23719/1529821"},
        database_releases=[{"name": "Federal LCA Commons, Commons Merged", "release": RELEASE,
                            "sha256": summary["database"]["sha256"]}],
        assumptions={
            "yield_and_losses": "PP: 1.034 kg resin per kg part from the USLCI molding dataset; other materials: losses not applied (pending).",
            "manufacturing_energy": "PP injection molding dataset for PP; PP molding conversion as proxy for ABS, nylon, POM, PC; generic extrusion for PVC and LDPE foil; metal forming, silicone molding and assembly electricity pending.",
            "allocation": "Default allocation factors stored in each multi-output dataset; processes without factors keep the burden on the reference product.",
            "recycling": "Stainless steel scrap input follows the dataset's 'value of scrap' burden; flows without providers (e.g. old corrugated containers) enter burden-free.",
            "other": "Biogenic CO2 excluded (AR6-100); AR6-100 Net Biogenic reported as an alternative."},
        reproduction_command="python scripts/run_pass1.py && python scripts/render_pass1_figures.py",
    )
    manifest["results"] = {
        "status": summary["status"],
        "ghg_kg_co2e_per_packaged_kettle": None,
        "ghg_kg_co2e_calculated_items_only": round(summary["gwp100_calculated_items_kg"], 4),
        "contributions": [{"item": c["item_id"] + " " + c["bom_material"] + " " + c["stage"],
                           "kg_co2e": round(float(c["gwp100_kg"]), 5)} for c in contrib if c["gwp100_kg"]],
        "missing_inputs": summary["pending_items"],
        "unresolved_providers": "results/pass1/unresolved_links.csv",
        "uncharacterized_flows": "not yet checked",
    }
    manifest["checks"] = {
        "units": "Exchange amounts converted to flow reference units via unit groups and flow property factors.",
        "balances": "BOM 723.00 g + 137.80 g = 860.80 g (pass).",
        "contribution_sum": "Sum of item results equals joint matrix solution (pass).",
        "double_counting": "PP resin and PP molding separated (molding minus resin input).",
    }
    (ROOT / "run-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    total = summary["gwp100_calculated_items_kg"]
    agg = {}
    for c in contrib:
        if c["gwp100_kg"]:
            a = agg.setdefault(c["bom_material"], [0.0, 0.0])
            a[0 if c["stage"] == "material" else 1] += float(c["gwp100_kg"])
    print("| 항목 | 소재 | 가공 | 합계 | 비율 |")
    for k, (m, cv) in sorted(agg.items(), key=lambda kv: -sum(kv[1])):
        print(f"| {k} | {m:.3f} | {cv:.3f} | {m + cv:.3f} | {(m + cv) / total * 100:.1f}% |")
    print("total", round(total, 4))
    for r in out:
        print(r["foreground_input"], "|", r["dataset_version"], "|", r["geography"])


if __name__ == "__main__":
    main()
