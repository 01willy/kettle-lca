"""Render the pass-1 workflow and decision diagram (fig0) and the decision sensitivity chart (fig3).

Usage: python scripts/render_pass1_workflow.py
Inputs: results/pass1/summary.json, results/pass1/sensitivity.csv
"""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/pass1"
OUT = ROOT / "figures/pass1"
SPEC = json.loads((ROOT / "figures/figure_spec.json").read_text(encoding="utf-8"))
COL = SPEC["style"]["colors"]
FS = SPEC["style"]["font_size_pt"]
for font_file in SPEC["style"].get("font_files", []):
    font_manager.fontManager.addfont(font_file)
plt.rcParams.update({
    "font.family": [SPEC["style"]["font"], "DejaVu Sans"],
    "mathtext.fontset": "custom",
    "mathtext.rm": SPEC["style"]["font"],
    "font.size": FS["tick"],
    "svg.fonttype": "none",
    "axes.unicode_minus": False,
})

STAGE_FILL, STAGE_EDGE = "#eef3f8", COL["material"]
DECISION_FILL, DECISION_EDGE = "#ffffff", "#5f5f5f"
ALGO_FILL = "#f6f6f6"


def box(ax, x, y, w, h, title, lines, fill, edge, ls="-", title_size=10, body_size=8.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=fill, edgecolor=edge, linewidth=1.1, linestyle=ls))
    ax.text(x + 0.12, y + h - 0.16, title, ha="left", va="top", fontsize=title_size, fontweight="bold",
            color=COL["text"])
    ax.text(x + 0.12, y + h - 0.50, "\n".join(lines), ha="left", va="top", fontsize=body_size,
            color=COL["text"], linespacing=1.45)


def fig0(summary):
    W, H = 13.6, 7.3
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.text(0.15, H - 0.25, "1차 계산의 작업 흐름, 계산 알고리즘, 판단 지점", fontsize=FS["title"] + 1,
            fontweight="bold", va="top", color=COL["text"])
    ax.text(0.15, H - 0.62,
            "실선 화살표는 작업 순서, 점선은 해당 단계에서 내린 판단이다. 판단 옆 괄호는 그 판단을 바꿨을 때의 결과 변화이다.",
            fontsize=FS["annotation"] + 0.5, va="top", color="#444444")

    total = summary["gwp100_calculated_items_kg"]
    share = summary["checks"]["material_mass_share_covered"] * 100
    w, gap, x0 = 2.5, 0.22, 0.15
    xs = [x0 + i * (w + gap) for i in range(5)]
    y_stage, h_stage = 4.72, 1.55
    stages = [
        ("① 입력 정의", ["BOM 12종", "제품 723 g + 포장 137.8 g", "기능 단위: 포장된 주전자 1대", "(factory gate까지)"], "-"),
        ("② 데이터 확보", ["USLCI: Commons Merged 패키지", "(51 MB, 공정 2,511개)", "TianGong: CLI 설치 완료,",
                       "로그인 완료 대기"], "-"),
        ("③ 데이터셋 매칭", ["USLCI 매칭 6종", f"(포장 포함 질량의 {share:.1f}%)", "미계산 6종: 황동, 구리,",
                        "나일론, POM, PC, 실리콘"], "-"),
        ("④ 행렬 계산", ["공급망 전체를 연립방정식으로", "한 번에 풀이", "열 2,729개, 기본 흐름 4,944개"], "-"),
        ("⑤ 결과와 점검", [f"{total:.2f} kg CO$_2$-eq/대 (부분 결과)", "질량 수지 통과",
                       "기여 합계 = 전체 해 (통과)", "미계산 항목은 0이 아님"], "-"),
    ]
    for x, (title, lines, ls) in zip(xs, stages):
        box(ax, x, y_stage, w, h_stage, title, lines, STAGE_FILL, STAGE_EDGE, ls)
    for i in range(4):
        ax.add_patch(FancyArrowPatch((xs[i] + w + 0.01, y_stage + h_stage / 2),
                                     (xs[i + 1] - 0.01, y_stage + h_stage / 2),
                                     arrowstyle="-|>", mutation_scale=14, color="#333333", linewidth=1.3))

    decisions = {
        0: [("판단 D0 · 재료 손실", ["PP만 데이터셋 손실 3.4% 적용,", "나머지는 미반영", "(과소 추정 방향)"])],
        1: [("판단 D1 · DB 패키지", ["USLCI 단독 대신 Commons Merged", "(외부 전력 공급망 연결 확보)"])],
        2: [("판단 D2 · 데이터 없는 소재", ["0으로 두지 않고 '미계산' 표기", "(TianGong으로 보완 예정)"]),
            ("판단 D3 · 부품 가공", ["PP 사출 데이터를 수지와 가공으로", "분리, 다른 플라스틱에 proxy 적용"])],
        3: [("판단 D4 · 다중 산출 공정", ["정유 등은 제품별 열로 분리", "(초기 오류 수정: PP 수지",
                                    "117 → 2.06 kg CO$_2$-eq/kg)"]),
            ("판단 D5 · 특성화 방법", ["IPCC AR6-100, 생물기원 CO$_2$ = 0", "(AR5, Net Biogenic: 차이 0.05% 이내)"])],
        4: [("판단 D6 · 스테인리스 스크랩", ["데이터셋 부담(value of scrap) 유지", "(cut-off 적용 시 −20.3%)"]),
            ("판단 D7 · 골판지 공장 CO$_2$", ["원자료대로 화석 CO$_2$로 계산", "(생물기원 해석 시 −7.7%)"])],
    }
    h_dec, y_top = 1.05, 3.3
    for col, items in decisions.items():
        for k, (title, lines) in enumerate(items):
            y = y_top - k * (h_dec + 0.18)
            box(ax, xs[col], y, w, h_dec, title, lines, DECISION_FILL, DECISION_EDGE, ls="-",
                title_size=9.2, body_size=8.3)
        ax.plot([xs[col] + w / 2, xs[col] + w / 2], [y_stage - 0.02, y_top + h_dec + 0.02], color="#777777",
                linewidth=1.0, linestyle=(0, (3, 3)))

    y_algo, h_algo = 0.15, 0.95
    wa = (W - 0.3 - 2 * 0.22) / 3
    algo = [
        ("A s = f  (공정별 활동량)", ["A: 공정 간 투입·산출 (2,729 × 2,729), f: 주전자 1대의 수요",
                                 "희소 LU 분해로 s를 구한다 (역행렬은 만들지 않음)"]),
        ("g = B s  (배출 목록)", ["B: 공정별 배출·자원 사용 (4,944 × 2,729)", "g: 주전자 1대의 공급망 전체 배출량"]),
        ("h = c g  (지구온난화 영향)", ["c: IPCC AR6 GWP100 계수 (CO$_2$ 1, CH$_4$ 29.8, N$_2$O 273)",
                                  "h: kg CO$_2$-eq/대"]),
    ]
    ax.text(0.15, y_algo + h_algo + 0.28, "계산 알고리즘 (④ 단계의 내용)", fontsize=10, fontweight="bold",
            color=COL["text"], va="bottom")
    for i, (title, lines) in enumerate(algo):
        x = 0.15 + i * (wa + 0.22)
        box(ax, x, y_algo, wa, h_algo, title, lines, ALGO_FILL, "#999999", title_size=9.4, body_size=8.4)
        if i < 2:
            ax.add_patch(FancyArrowPatch((x + wa + 0.01, y_algo + h_algo / 2), (x + wa + 0.21, y_algo + h_algo / 2),
                                         arrowstyle="-|>", mutation_scale=12, color="#333333", linewidth=1.2))
    save(fig, "fig0_workflow_decisions")


def fig3():
    rows = list(csv.DictReader(open(RES / "sensitivity.csv", encoding="utf-8")))
    base = float(rows[0]["gwp100_kg"])
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(9.0, 3.9))
    for i, r in enumerate(rows):
        v = float(r["gwp100_kg"])
        is_base = r["scenario"] == "baseline"
        ax.barh(i, v, color=COL["material"] if is_base else COL["conversion"], height=0.6)
        pct = float(r["difference_pct"])
        diff = "기준" if is_base else (f"{pct:+.2f}%" if abs(pct) < 0.1 else f"{pct:+.1f}%")
        ax.text(v + 0.03, i, f"{v:.2f} ({diff})", va="center", fontsize=FS["annotation"], color=COL["text"])
    ax.axvline(base, color="#333333", linewidth=0.9, linestyle=(0, (3, 3)))
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["description"] for r in rows], fontsize=FS["annotation"] + 0.5)
    ax.set_xlabel("계산된 항목의 GWP100 (kg CO$_2$-eq/대)")
    ax.set_xlim(0, base * 1.22)
    ax.grid(axis="x", color=COL["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.suptitle("판단 하나를 바꿨을 때의 결과 변화 (1차 계산)", x=0.02, ha="left", fontsize=FS["title"],
                 fontweight="bold")
    fig.text(0.02, 0.875, "점선은 기준 결과이다. 미계산 항목(6개 소재, 조립, 운송)은 모든 경우에 제외되어 있다.",
             fontsize=FS["annotation"], color="#444444")
    fig.subplots_adjust(left=0.37, right=0.97, top=0.8, bottom=0.15)
    save(fig, "fig3_decision_sensitivity")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.svg")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    summary = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    fig0(summary)
    fig3()
    print("written")
