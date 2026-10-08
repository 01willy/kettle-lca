"""Render pass-1 figures from results/pass1 (no calculation here).

Usage: python scripts/render_pass1_figures.py
"""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/pass1"
OUT = ROOT / "figures/pass1"
SPEC = json.loads((ROOT / "figures/figure_spec.json").read_text(encoding="utf-8"))
COL = SPEC["style"]["colors"]
for font_file in SPEC["style"].get("font_files", []):
    font_manager.fontManager.addfont(font_file)
FS = SPEC["style"]["font_size_pt"]

plt.rcParams.update({
    "font.family": SPEC["style"]["font"],
    "font.size": FS["tick"],
    "axes.titlesize": FS["title"],
    "axes.labelsize": FS["axis_label"],
    "axes.edgecolor": "#666666",
    "axes.linewidth": 0.8,
    "xtick.color": COL["text"],
    "ytick.color": COL["text"],
    "svg.fonttype": "none",
    "axes.unicode_minus": False,
})

SHORT = {
    "Stainless steel": "Stainless steel (304)",
    "Polypropylene (PP)": "Polypropylene (PP)",
    "Polyvinyl chloride (PVC)": "PVC",
    "Acrylonitrile-butadiene-styrene (ABS)": "ABS",
    "LDPE packaging foil": "LDPE foil (pack.)",
    "Cardboard packaging": "Cardboard (pack.)",
    "Brass": "Brass",
    "Copper": "Copper",
    "Nylon, grade unspecified": "Nylon (grade n/a)",
    "Polyoxymethylene (POM)": "POM",
    "Polycarbonate (PC)": "PC",
    "Silicone": "Silicone",
}


def load_items():
    rows = list(csv.DictReader(open(RES / "contributions.csv", encoding="utf-8")))
    bom = {r["material"]: float(r["finished_mass_g"])
           for r in csv.DictReader(open(ROOT / "data/kettle-bom.csv", encoding="utf-8"))}
    items = {}
    for r in rows:
        if r["stage"] not in ("material", "conversion"):
            continue
        name = r["bom_material"]
        if name not in bom:
            continue  # combined conversion rows (e.g. brass and copper) are pending and not plotted
        it = items.setdefault(name, {"mass_g": bom.get(name, 0.0), "material": None, "conversion": None,
                                     "conversion_status": None})
        val = float(r["gwp100_kg"]) if r["gwp100_kg"] else None
        it[r["stage"]] = val
        if r["stage"] == "conversion":
            it["conversion_status"] = r["status"]
    return items


def fig1(summary):
    items = load_items()
    calc = sorted([k for k, v in items.items() if v["material"] is not None],
                  key=lambda k: items[k]["material"] + (items[k]["conversion"] or 0.0))
    pend = sorted([k for k, v in items.items() if v["material"] is None],
                  key=lambda k: -items[k]["mass_g"])
    order = pend[::-1] + calc  # bottom-to-top
    y = range(len(order))
    fig, (ax_m, ax_g) = plt.subplots(1, 2, figsize=(9.0, 5.4), sharey=True,
                                     gridspec_kw={"width_ratios": [1, 1.6], "wspace": 0.06})
    for i, k in enumerate(order):
        it = items[k]
        done = it["material"] is not None
        ax_m.barh(i, it["mass_g"], color=COL["mass"] if done else COL["pending"], height=0.62)
        ax_m.text(it["mass_g"] + 6, i, f"{it['mass_g']:.1f}", va="center", ha="right",
                  fontsize=FS["annotation"], color=COL["text"])
        if done:
            mat = it["material"]
            conv = it["conversion"] or 0.0
            ax_g.barh(i, mat, color=COL["material"], height=0.62)
            if conv:
                ax_g.barh(i, conv, left=mat, color=COL["conversion"], height=0.62)
            ax_g.text(mat + conv + 0.02, i, f"{mat + conv:.3f}", va="center", fontsize=FS["annotation"],
                      color=COL["text"])
        else:
            conv = it["conversion"]
            note = "소재 미계산 (TianGong 매칭 대기)"
            if conv:
                ax_g.barh(i, conv, color=COL["conversion"], height=0.62)
                note = f"가공 {conv:.3f} · " + note
            ax_g.text((conv or 0.0) + 0.02, i, note, va="center", fontsize=FS["annotation"],
                      color="#666666", style="italic")
    ax_m.set_yticks(list(y))
    ax_m.set_yticklabels([SHORT.get(k, k) for k in order])
    ax_m.invert_xaxis()
    ax_m.set_xlabel("완제품 질량 (g/대)")
    ax_g.set_xlabel("GWP100 (kg CO$_2$-eq/대)")
    ax_m.set_xlim(420, 0)
    ax_g.set_xlim(0, 1.75)
    for ax in (ax_m, ax_g):
        ax.grid(axis="x", color=COL["grid"], linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    ax_g.tick_params(axis="y", length=0)
    ax_m.axhline(len(pend) - 0.5, color="#999999", linewidth=0.8, linestyle=(0, (3, 3)))
    ax_g.axhline(len(pend) - 0.5, color="#999999", linewidth=0.8, linestyle=(0, (3, 3)))
    ax_m.legend([plt.Rectangle((0, 0), 1, 1, color=COL["mass"]),
                 plt.Rectangle((0, 0), 1, 1, color=COL["pending"])],
                ["소재 GWP 계산됨", "소재 GWP 미계산"], loc="lower left", frameon=False,
                fontsize=FS["annotation"])
    ax_g.legend([plt.Rectangle((0, 0), 1, 1, color=COL["material"]),
                 plt.Rectangle((0, 0), 1, 1, color=COL["conversion"])],
                ["소재 생산 (USLCI)", "부품 가공"], loc="lower right", frameon=False,
                fontsize=FS["annotation"])
    total = summary["gwp100_calculated_items_kg"]
    share = summary["checks"]["material_mass_share_covered"] * 100
    fig.suptitle("항목별 질량과 GWP100 기여 (1차 계산, USLCI 기준)", x=0.08, ha="left", fontsize=FS["title"],
                 fontweight="bold")
    fig.text(0.08, 0.905,
             f"계산된 항목 합계 {total:.2f} kg CO$_2$-eq/대 · 포장 포함 질량의 {share:.1f}% 반영 · "
             "점선 아래 6개 소재는 미계산이며 0이 아니다",
             fontsize=FS["annotation"], color="#444444")
    fig.subplots_adjust(left=0.17, right=0.98, top=0.86, bottom=0.11)
    save(fig, "fig1_item_contribution")


PROCESS_LABEL = {
    "Steel; stainless 304; flat rolled coil": "Stainless 304 coil production (direct)",
    "Steel; stainless 304; scrap": "Stainless 304 scrap input ('value of scrap')",
    "Containerboard; at mill": "Containerboard mill",
    "Propylene; at plant": "Propylene production",
    "Natural gas; for ethylene combusted in industrial boiler; at hydrocracker":
        "Natural gas boiler at ethylene cracker",
    "Natural gas combustion; external combustion boilers, industrial, natural gas, > 100 million Btu/hr, "
    "low NOx burners; at boiler": "Natural gas industrial boiler, large (100+ MMBtu/h)",
    "Natural gas combustion; pipeline reciprocating engine, uncontrolled; at reciprocating engine":
        "Natural gas pipeline compressor engine",
    "Electricity - COAL - Midcontinent Independent System Operator, Inc.": "Coal power, MISO grid region",
    "Natural gas; onshore, unconventional; at well": "Natural gas extraction, onshore unconventional",
    "Natural gas combustion; reciprocating engine, oil and gas field, uncontrolled, pre-processing gas; "
    "at reciprocating engine": "Natural gas engine, oil and gas field",
}


def fig2(summary):
    rows = list(csv.DictReader(open(RES / "process_contributions.csv", encoding="utf-8")))[:10]
    total = summary["gwp100_calculated_items_kg"]
    labels, vals = [], []
    for r in rows:
        name = PROCESS_LABEL.get(r["process"], r["process"])
        if len(name) > 58:
            name = name[:55].rstrip(" ,;") + "…"
        labels.append(name)
        vals.append(float(r["gwp100_kg"]))
    labels, vals = labels[::-1], vals[::-1]
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    ax.barh(range(len(vals)), vals, color=COL["material"], height=0.62)
    for i, v in enumerate(vals):
        ax.text(v + 0.012, i, f"{v:.3f} ({v / total * 100:.1f}%)", va="center", fontsize=FS["annotation"],
                color=COL["text"])
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(labels, fontsize=FS["annotation"])
    ax.set_xlabel("공정 직접 배출의 GWP100 (kg CO$_2$-eq/대)")
    ax.set_xlim(0, max(vals) * 1.25)
    ax.grid(axis="x", color=COL["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.suptitle("공급망 공정별 직접 배출 상위 10개 (1차 계산)", x=0.02, ha="left", fontsize=FS["title"],
                 fontweight="bold")
    fig.text(0.02, 0.9, f"괄호 안은 계산된 항목 합계 {total:.2f} kg CO$_2$-eq/대에 대한 비율이다",
             fontsize=FS["annotation"], color="#444444")
    fig.subplots_adjust(left=0.36, right=0.97, top=0.84, bottom=0.13)
    save(fig, "fig2_process_drivers")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.svg")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    summary = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    fig1(summary)
    fig2(summary)
    print("written:", sorted(p.name for p in OUT.iterdir()))
