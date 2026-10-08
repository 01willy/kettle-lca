"""Report figures (pass 2), paper style. Plotting only; inputs come from results/.

Usage: python scripts/render_report_figures.py
Outputs: figures/report/fig{1..4}_*.pdf and .png
"""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R1, R2 = ROOT / "results/pass1", ROOT / "results/pass2"
OUT = ROOT / "figures/report"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": ["Liberation Sans", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "lines.linewidth": 0.8,
    "pdf.fonttype": 42, "svg.fonttype": "none", "axes.unicode_minus": False,
    "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
})
INK, MUTED, GRID = "#1a1a1a", "#666666", "#e6e6e6"
C_USLCI, C_USLCI_CONV = "#2b5d8a", "#9db8d2"
C_TG, C_TG_LIGHT = "#b8641e", "#e8b98c"
C_NC = "#d4d4d4"
GROUPS = [  # composition groups: (label, materials, color)
    ("Stainless steel", ["Stainless steel"], "#2b5d8a"),
    ("Polypropylene", ["Polypropylene (PP)"], "#6f9cc4"),
    ("Cardboard", ["Cardboard packaging"], "#a8916c"),
    ("ABS, PVC, LDPE", ["Acrylonitrile-butadiene-styrene (ABS)", "Polyvinyl chloride (PVC)", "LDPE packaging foil"],
     "#8faf86"),
    ("Copper, brass", ["Copper", "Brass"], C_TG),
    ("Nylon, POM, PC, silicone", ["Nylon, grade unspecified", "Polyoxymethylene (POM)", "Polycarbonate (PC)",
                                  "Silicone"], C_NC),
]
SHORT = {"Stainless steel": "Stainless steel", "Polypropylene (PP)": "Polypropylene",
         "Polyvinyl chloride (PVC)": "PVC", "Acrylonitrile-butadiene-styrene (ABS)": "ABS",
         "LDPE packaging foil": "LDPE foil", "Cardboard packaging": "Cardboard", "Brass": "Brass",
         "Copper": "Copper", "Nylon, grade unspecified": "Nylon", "Polyoxymethylene (POM)": "POM",
         "Polycarbonate (PC)": "PC", "Silicone": "Silicone"}
CO2EQ = r"kg CO$_2$-eq"


def load():
    bom = {r["material"]: float(r["finished_mass_g"])
           for r in csv.DictReader(open(ROOT / "data/kettle-bom.csv", encoding="utf-8"))}
    rows = list(csv.DictReader(open(R2 / "contributions.csv", encoding="utf-8")))
    items = {m: {"mass": g, "mat": None, "conv": None, "conv_status": None, "src": None} for m, g in bom.items()}
    for r in rows:
        m = r["bom_material"]
        if m not in items or r["stage"] not in ("material", "conversion"):
            continue
        v = float(r["gwp100_kg"]) if r["gwp100_kg"] else None
        if r["stage"] == "material":
            items[m]["mat"] = v
            items[m]["src"] = "TianGong" if r["item_id"] in ("M07", "M08") else ("USLCI" if v is not None else None)
        else:
            items[m]["conv"] = v
            items[m]["conv_status"] = r["status"]
    summary = json.loads((R2 / "summary.json").read_text(encoding="utf-8"))
    return items, summary


def style(ax, grid_axis="x"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)


def panel(fig, x, y, label):
    fig.text(x, y, label, fontsize=9, fontweight="bold", va="top", ha="left", color=INK)


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 1 method overview
def fig1(items, summary):
    fig = plt.figure(figsize=(7.2, 2.55))
    xs = [0.115, 0.3, 0.49, 0.675, 0.865]
    w, y0, h = 0.135, 0.33, 0.47

    # 1 bill of materials
    ax = fig.add_axes([xs[0] - w / 2 + 0.01, y0, w - 0.01, h])
    order = sorted(items, key=lambda m: -items[m]["mass"])
    colors = [C_TG if items[m]["src"] == "TianGong" else (C_USLCI if items[m]["src"] == "USLCI" else C_NC)
              for m in order]
    ax.bar(range(len(order)), [items[m]["mass"] for m in order], color=colors, width=0.75,
           hatch=None, linewidth=0)
    ax.set_xticks([])
    ax.set_yticks([0, 200, 400])
    ax.set_ylabel("Mass (g)", labelpad=1)
    ax.set_xlim(-0.8, len(order) - 0.2)
    style(ax, "y")

    # 2 background databases
    ax = fig.add_axes([xs[1] - w / 2, y0, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for cx, name, sub, col in ((0.27, "USLCI", "2,511\nprocesses", C_USLCI), (0.75, "TianGong", "129\ncandidates", C_TG)):
        ax.add_patch(Rectangle((cx - 0.2, 0.22), 0.4, 0.5, facecolor="white", edgecolor=col, linewidth=0.9))
        ax.add_patch(Ellipse((cx, 0.22), 0.4, 0.12, facecolor="white", edgecolor=col, linewidth=0.9))
        ax.add_patch(Rectangle((cx - 0.19, 0.22), 0.38, 0.0, facecolor="white", edgecolor="white"))
        ax.add_patch(Ellipse((cx, 0.72), 0.4, 0.12, facecolor=col, edgecolor=col, linewidth=0.9, alpha=0.9))
        ax.text(cx, 0.47, sub, ha="center", va="center", fontsize=5.8, color=INK, linespacing=1.1)
        ax.text(cx, 0.93, name, ha="center", va="center", fontsize=6.5, color=col, fontweight="bold")

    # 3 dataset matching
    ax = fig.add_axes([xs[2] - w / 2 + 0.05, y0 - 0.02, w - 0.035, h + 0.04])
    status = {  # material: (USLCI, TianGong); u=used, r=candidate rejected, x=no dataset, n=not searched
        "Stainless steel": "un", "Polypropylene (PP)": "un", "Cardboard packaging": "un",
        "Polyvinyl chloride (PVC)": "un", "Acrylonitrile-butadiene-styrene (ABS)": "un",
        "LDPE packaging foil": "un", "Copper": "ru", "Brass": "xu", "Nylon, grade unspecified": "rx",
        "Polyoxymethylene (POM)": "xx", "Polycarbonate (PC)": "rr", "Silicone": "xx"}
    names = list(status)
    for i, m in enumerate(names):
        y = len(names) - 1 - i
        for j, s in enumerate(status[m]):
            col = C_USLCI if j == 0 else C_TG
            if s == "u":
                ax.plot(j, y, "o", ms=3.6, color=col)
            elif s == "r":
                ax.plot(j, y, "o", ms=3.6, mfc="white", mec=col, mew=0.7)
            elif s == "x":
                ax.plot(j, y, "x", ms=3.2, color="#999999", mew=0.7)
            else:
                ax.plot(j, y, "_", ms=3.2, color="#bbbbbb", mew=0.7)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([SHORT[m] for m in names][::-1], fontsize=5.6)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["USLCI", "TianGong"], fontsize=5.8)
    ax.xaxis.tick_top()
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(-0.7, len(names) - 0.3)
    ax.tick_params(length=0, pad=1.5)
    for side in ax.spines.values():
        side.set_visible(False)

    # 4 matrix LCA (real sparsity pattern of A)
    pat = np.load(R2 / "technosphere_pattern.npz")
    ax = fig.add_axes([xs[3] - w / 2 + 0.01, y0, w - 0.02, h])
    ax.scatter(pat["col"], pat["row"], s=0.04, color=C_USLCI, linewidths=0, rasterized=True)
    n = int(pat["n"])
    ax.set_xlim(0, n)
    ax.set_ylim(n, 0)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.6)
        s.set_color(MUTED)
    ax.text(0.5, 1.06, r"$A\,s = f$", transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5)

    # 5 result
    ax = fig.add_axes([xs[4] - 0.03, y0, 0.06, h])
    bottom = 0.0
    for label, mats, col in GROUPS:
        v = sum((items[m]["mat"] or 0) + (items[m]["conv"] or 0) for m in mats)
        if v <= 0:
            continue
        ax.bar(0, v, bottom=bottom, color=col if col != C_NC else "#b9a3cf", width=0.7, linewidth=0.3,
               edgecolor="white")
        bottom += v
    ax.set_xlim(-0.6, 0.6)
    ax.set_xticks([])
    ax.set_ylim(0, 3.6)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_ylabel(CO2EQ, labelpad=1)
    style(ax, None)
    ax.text(0.55, bottom, f"{summary['gwp100_calculated_items_kg']:.2f}", ha="left", va="center", fontsize=6.5)

    # stage labels, arrows, decision markers
    labels = [("Bill of materials", "12 inputs, 860.8 g"),
              ("Background data", "Commons Merged · TianGong CLI"),
              ("Dataset matching", "8 of 12 inputs matched"),
              ("Matrix LCA", f"A: {n:,} × {n:,}; g = B s; h = c g"),
              ("GWP100", "per packaged kettle")]
    for x, (t1, t2) in zip(xs, labels):
        fig.text(x, 0.17, t1, ha="center", fontsize=7.2, fontweight="bold", color=INK)
        fig.text(x, 0.08, t2, ha="center", fontsize=6.3, color=MUTED)
    for a, b in zip(xs[:-1], xs[1:]):
        fig.add_artist(FancyArrowPatch((a + 0.072, y0 + h / 2), (b - 0.08, y0 + h / 2), transform=fig.transFigure,
                                       arrowstyle="-|>", mutation_scale=7, color="#444444", linewidth=0.8))
    decisions = [(0, "D0"), (1, "D1"), (2, "D2 D3 D8"), (3, "D4 D5"), (4, "D6 D7")]
    for i, txt in decisions:
        fig.text(xs[i], 0.93, txt, ha="center", va="center", fontsize=6.2, color=INK,
                 bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#888888", linewidth=0.5))
    save(fig, "fig1_method_overview")


# ---------------------------------------------------------------- Fig. 2 results
def fig2(items, summary):
    fig = plt.figure(figsize=(7.2, 3.9))
    # a: composition of mass vs GWP
    ax = fig.add_axes([0.13, 0.74, 0.84, 0.17])
    mass_total = sum(it["mass"] for it in items.values())
    gwp_total = summary["gwp100_calculated_items_kg"]
    for row, key in ((1, "mass"), (0, "gwp")):
        left = 0.0
        for label, mats, col in GROUPS:
            if key == "mass":
                v = sum(items[m]["mass"] for m in mats) / mass_total
            else:
                v = sum((items[m]["mat"] or 0) + (items[m]["conv"] or 0) for m in mats) / gwp_total
            if v <= 0:
                continue
            hatch = "////" if col == C_NC and key == "mass" else None
            face = col if not (col == C_NC and key == "gwp") else "#b9a3cf"
            ax.barh(row, v, left=left, color=face, height=0.62, edgecolor="white", linewidth=0.6, hatch=hatch)
            if v > 0.055:
                txt_col = "white" if face in ("#2b5d8a", C_TG) else INK
                ax.text(left + v / 2, row, f"{v * 100:.0f}%", ha="center", va="center", fontsize=6.3, color=txt_col)
            left += v
    ax.set_yticks([0, 1])
    ax.set_yticklabels([f"GWP100\n({gwp_total:.2f} {CO2EQ.replace('kg ', 'kg ')})", f"Mass\n({mass_total:.1f} g)"],
                       fontsize=6.5)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"])
    style(ax, None)
    ax.tick_params(axis="y", length=0)
    handles = [Rectangle((0, 0), 1, 1, facecolor=c if c != C_NC else "#d4d4d4", hatch="////" if c == C_NC else None,
                         edgecolor="white") for _, _, c in GROUPS]
    handles.append(Rectangle((0, 0), 1, 1, facecolor="#b9a3cf", edgecolor="white"))
    fig.legend(handles, [g[0] for g in GROUPS[:-1]] + ["Nylon, POM, PC, silicone (n.c.)", "Molding of n.c. plastics"],
               loc="upper center", bbox_to_anchor=(0.55, 1.0), ncol=7, frameon=False, fontsize=5.9,
               handlelength=1.2, columnspacing=0.9, handletextpad=0.4)
    panel(fig, 0.01, 0.985, "a")

    # b: per-item GWP100
    ax = fig.add_axes([0.13, 0.09, 0.62, 0.53])
    calc = [m for m in items if items[m]["mat"] is not None]
    pend = [m for m in items if items[m]["mat"] is None]
    order = sorted(pend, key=lambda m: items[m]["mass"]) + sorted(calc, key=lambda m: (items[m]["mat"] + (items[m]["conv"] or 0)))
    for i, m in enumerate(order):
        it = items[m]
        tg = it["src"] == "TianGong"
        mat, conv = it["mat"] or 0.0, it["conv"] or 0.0
        if it["mat"] is not None:
            ax.barh(i, mat, color=C_TG if tg else C_USLCI, height=0.62, linewidth=0)
        if conv:
            ax.barh(i, conv, left=mat, color=C_USLCI_CONV, height=0.62, linewidth=0)
        label = f"{mat + conv:.3f}" if it["mat"] is not None else (f"n.c. (molding {conv:.3f})" if conv else "n.c.")
        if it["mat"] is not None and it["conv_status"] in (None, "pending"):
            label += "  (forming n.c.)" if m == "Stainless steel" else ("  (converting n.c.)" if m == "Cardboard packaging" else "")
        ax.text(mat + conv + 0.02, i, label, va="center", fontsize=6.2, color=INK if it["mat"] is not None else MUTED)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([SHORT[m] for m in order])
    ax.axhline(len(pend) - 0.5, color="#aaaaaa", linewidth=0.5, linestyle=(0, (2, 2)))
    ax.set_xlabel(f"GWP100 ({CO2EQ} per kettle)")
    ax.set_xlim(0, 1.75)
    style(ax, "x")
    ax.tick_params(axis="y", length=0)
    ax.legend([Rectangle((0, 0), 1, 1, color=C_USLCI), Rectangle((0, 0), 1, 1, color=C_TG),
               Rectangle((0, 0), 1, 1, color=C_USLCI_CONV)],
              ["Material, USLCI", "Material, TianGong", "Part conversion, USLCI"], loc="lower right",
              frameon=False, fontsize=6.2, handlelength=1.2)
    panel(fig, 0.01, 0.66, "b")

    # b inset text: mass intensity
    ax2 = fig.add_axes([0.79, 0.09, 0.19, 0.53])
    for i, m in enumerate(order):
        it = items[m]
        if it["mat"] is None:
            continue
        intensity = (it["mat"] + (it["conv"] or 0)) / (it["mass"] / 1000)
        ax2.plot(intensity, i, "o", ms=3, color=C_TG if it["src"] == "TianGong" else C_USLCI)
    ax2.set_ylim(ax.get_ylim())
    ax2.set_yticks([])
    ax2.set_xlim(0, 9)
    ax2.set_xlabel(f"Intensity ({CO2EQ} kg$^{{-1}}$)")
    style(ax2, "x")
    ax2.spines["left"].set_visible(False)
    save(fig, "fig2_results")


# ---------------------------------------------------------------- Fig. 3 supply-chain hot spots
PROC = {
    "Steel; stainless 304; flat rolled coil": "Stainless 304 coil, direct",
    "Steel; stainless 304; scrap": "Stainless 304 scrap ('value of scrap')",
    "Containerboard; at mill": "Containerboard mill",
    "Propylene; at plant": "Propylene plant",
    "Natural gas; for ethylene combusted in industrial boiler; at hydrocracker": "Natural gas boiler, ethylene cracker",
    "Natural gas combustion; external combustion boilers, industrial, natural gas, > 100 million Btu/hr, "
    "low NOx burners; at boiler": "Natural gas industrial boiler",
    "Natural gas combustion; pipeline reciprocating engine, uncontrolled; at reciprocating engine":
        "Pipeline compressor engine",
    "Electricity - COAL - Midcontinent Independent System Operator, Inc.": "Coal power, MISO region",
    "Natural gas; onshore, unconventional; at well": "Natural gas extraction",
    "Natural gas combustion; reciprocating engine, oil and gas field, uncontrolled, pre-processing gas; "
    "at reciprocating engine": "Oil and gas field engine",
}


def fig3(summary):
    rows = list(csv.DictReader(open(R1 / "process_contributions.csv", encoding="utf-8")))[:10]
    total = summary["gwp100_calculated_items_kg"]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    fig.subplots_adjust(left=0.3, right=0.95, top=0.95, bottom=0.17)
    vals = [float(r["gwp100_kg"]) for r in rows][::-1]
    labs = [PROC.get(r["process"], r["process"][:40]) for r in rows][::-1]
    ax.barh(range(len(vals)), vals, color=C_USLCI, height=0.62, linewidth=0)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.3f} ({v / total * 100:.1f}%)", va="center", fontsize=6.2)
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(labs)
    ax.set_xlabel(f"Direct emissions of the process, GWP100 ({CO2EQ} per kettle)")
    ax.set_xlim(0, 1.0)
    style(ax, "x")
    ax.tick_params(axis="y", length=0)
    save(fig, "fig3_hotspots")


# ---------------------------------------------------------------- Fig. 4 decisions and gases
def fig4(summary):
    sens = list(csv.DictReader(open(R2 / "sensitivity.csv", encoding="utf-8")))
    base = float(sens[0]["gwp100_kg"])
    alt = sens[1:]
    fig = plt.figure(figsize=(7.2, 2.4))
    ax = fig.add_axes([0.25, 0.2, 0.42, 0.72])
    for i, r in enumerate(alt[::-1]):
        v = float(r["gwp100_kg"])
        if abs(v - base) > 0.02:
            ax.annotate("", xy=(v, i), xytext=(base, i),
                        arrowprops=dict(arrowstyle="-|>", color=C_USLCI, lw=0.8, mutation_scale=6,
                                        shrinkA=0, shrinkB=1.5))
        ax.plot(v, i, "o", ms=3.2, color=C_USLCI)
        pct = float(r["difference_pct"])
        txt = (f"{pct:+.1f}%" if abs(pct) >= 0.1 else f"{pct:+.2f}%").replace("-", "\u2212")
        ax.text(min(v, base) - 0.03, i, txt, ha="right", va="center", fontsize=6.2)
    ax.axvline(base, color=INK, linewidth=0.7)
    ax.text(base + 0.015, len(alt) - 0.45, f"Baseline {base:.2f}", ha="left", va="bottom", fontsize=6.2)
    ax.set_yticks(range(len(alt)))
    ax.set_yticklabels([f"{r['decision']}  {r['label']}".replace("CO2", "CO$_2$") for r in alt[::-1]])
    ax.set_xlim(2.0, 3.5)
    ax.set_ylim(-0.6, len(alt) - 0.1)
    ax.set_xlabel(f"GWP100 of calculated items ({CO2EQ} per kettle)")
    style(ax, "x")
    ax.tick_params(axis="y", length=0)
    panel(fig, 0.01, 0.98, "a")

    gas = list(csv.DictReader(open(R2 / "gas_breakdown.csv", encoding="utf-8")))
    ax = fig.add_axes([0.78, 0.2, 0.19, 0.72])
    names = {"CO2 (fossil)": r"CO$_2$ (fossil)", "CH4": r"CH$_4$", "N2O": r"N$_2$O", "Other": "Other"}
    vals = [float(g["gwp100_kg"]) for g in gas]
    ax.bar(range(len(vals)), vals, color=[C_USLCI, "#6f9cc4", "#9db8d2", "#cccccc"], width=0.65, linewidth=0)
    for i, (g, v) in enumerate(zip(gas, vals)):
        ax.text(i, max(v, 0) + 0.05, f"{float(g['share']) * 100:.1f}%".replace("-", "\u2212"), ha="center",
                va="bottom", fontsize=6.0)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels([names[g["gas"]] for g in gas], rotation=0, fontsize=6.0)
    ax.set_ylabel(f"GWP100 ({CO2EQ})")
    ax.set_ylim(0, 3.4)
    style(ax, "y")
    panel(fig, 0.71, 0.98, "b")
    save(fig, "fig4_decisions_gases")


if __name__ == "__main__":
    items, summary = load()
    fig1(items, summary)
    fig2(items, summary)
    fig3(summary)
    fig4(summary)
    print("written:", sorted(p.name for p in OUT.iterdir()))
