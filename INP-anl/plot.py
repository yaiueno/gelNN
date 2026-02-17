"""
plot.py — リリース / プレス比較 Bode プロット（|Z| & θ）
──────────────────────────────────────────────────
測定データを「リリース (1-3回目)」「プレス (4-6回目)」に分けて
重ね描きし、圧縮による差分を可視化する。

生成グラフ:
  1. リリース全回 Bode プロット
  2. プレス全回 Bode プロット
  3. リリース vs プレス 比較 Bode プロット（平均 ± 標準偏差の帯付き）

使い方:
    python plot.py                                # data/ 内を自動検出
    python plot.py --name sample_gel              # サンプル名で絞り込み
    python plot.py --name sample_gel --show       # ウィンドウ表示
"""

import argparse
import csv
import glob
import os
import sys
from typing import Sequence

import matplotlib
import matplotlib.figure as mpl_figure
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = "MS Gothic"  # 日本語フォント (Windows)
matplotlib.rcParams["axes.unicode_minus"] = False

from config import ANALYSIS_DIR, GRAPH_DIR, MEASURE_DIR, timestamp


# ─── ユーティリティ ──────────────────────────────
def load_csv(filepath: str) -> dict[str, np.ndarray]:
    """CSV → NumPy 配列に変換"""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        data: dict[str, list[float]] = {k: [] for k in fieldnames}
        for row in reader:
            for k, v in row.items():
                data[k].append(float(v))
    return {k: np.array(v) for k, v in data.items()}


def find_files(directory: str, pattern: str) -> list[str]:
    """パターンにマッチするファイルを更新日順で返す"""
    files = glob.glob(os.path.join(directory, pattern))
    return sorted(files, key=os.path.getmtime)


def find_latest(directory: str, pattern: str) -> str | None:
    files = find_files(directory, pattern)
    return files[-1] if files else None


# ─── 色パレット ──────────────────────────────────
RELEASE_COLORS = ["#2563EB", "#3B82F6", "#60A5FA"]   # 青系 (リリース)
PRESS_COLORS   = ["#DC2626", "#EF4444", "#F87171"]   # 赤系 (プレス)
RELEASE_PHASE  = ["#1D4ED8", "#2563EB", "#3B82F6"]
PRESS_PHASE    = ["#B91C1C", "#DC2626", "#EF4444"]


# ─── 個別グループ Bode プロット ───────────────────
def plot_group_bode(
    datasets: list[dict[str, np.ndarray]],
    labels: list[str],
    title: str,
    colors_z: list[str],
    colors_p: list[str],
) -> mpl_figure.Figure:
    """
    複数回の測定データを重ねた Bode プロット。
    上段: |Z| vs 周波数  （対数-対数）
    下段: θ   vs 周波数  （対数-リニア）
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    for i, (d, lbl) in enumerate(zip(datasets, labels)):
        cz = colors_z[i % len(colors_z)]
        cp = colors_p[i % len(colors_p)]
        marker = ["o", "s", "D", "^", "v", "P"][i % 6]

        ax1.loglog(
            d["frequency_Hz"], d["impedance_ohm"],
            f"{marker}-", color=cz, markersize=3, linewidth=1.0,
            label=f"|Z| {lbl}", alpha=0.85,
        )
        ax2.semilogx(
            d["frequency_Hz"], d["phase_deg"],
            f"{marker}-", color=cp, markersize=3, linewidth=1.0,
            label=f"θ {lbl}", alpha=0.85,
        )

    ax1.set_ylabel("|Z|  [Ω]", fontsize=12)
    ax1.grid(True, which="both", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right", fontsize=9)

    ax2.set_xlabel("周波数  [Hz]", fontsize=12)
    ax2.set_ylabel("位相角 θ  [deg]", fontsize=12)
    ax2.grid(True, which="both", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper right", fontsize=9)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# ─── リリース vs プレス 比較プロット ──────────────
def plot_release_vs_press(
    release_sets: list[dict[str, np.ndarray]],
    press_sets: list[dict[str, np.ndarray]],
) -> mpl_figure.Figure:
    """
    リリースとプレスの平均を太線で描画し、
    標準偏差の範囲を半透明の帯 (fill_between) で可視化する。
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    fig.suptitle("リリース vs プレス — Bode プロット比較", fontsize=14, fontweight="bold")

    def _stats(datasets: list[dict[str, np.ndarray]], key: str):
        """共通周波数に対する平均・標準偏差を算出（周波数は最初のセットを基準）"""
        arrays = [d[key] for d in datasets]
        stacked = np.vstack(arrays)
        return stacked.mean(axis=0), stacked.std(axis=0)

    freq = release_sets[0]["frequency_Hz"]

    # ── リリース統計 ──
    z_mean_r, z_std_r = _stats(release_sets, "impedance_ohm")
    p_mean_r, p_std_r = _stats(release_sets, "phase_deg")

    # ── プレス統計 ──
    z_mean_p, z_std_p = _stats(press_sets, "impedance_ohm")
    p_mean_p, p_std_p = _stats(press_sets, "phase_deg")

    # --- |Z| ---
    ax1.loglog(freq, z_mean_r, "o-", color="#2563EB", linewidth=2, markersize=3,
               label="リリース (平均)")
    ax1.fill_between(freq, z_mean_r - z_std_r, z_mean_r + z_std_r,
                     color="#2563EB", alpha=0.15, label="リリース (±1σ)")

    ax1.loglog(freq, z_mean_p, "s-", color="#DC2626", linewidth=2, markersize=3,
               label="プレス (平均)")
    ax1.fill_between(freq, z_mean_p - z_std_p, z_mean_p + z_std_p,
                     color="#DC2626", alpha=0.15, label="プレス (±1σ)")

    # 個別ラインも薄く描画
    for i, d in enumerate(release_sets):
        ax1.loglog(d["frequency_Hz"], d["impedance_ohm"], "-",
                   color="#93C5FD", linewidth=0.5, alpha=0.5,
                   label=f"R{i+1}" if i == 0 else None)
    for i, d in enumerate(press_sets):
        ax1.loglog(d["frequency_Hz"], d["impedance_ohm"], "-",
                   color="#FCA5A5", linewidth=0.5, alpha=0.5,
                   label=f"P{i+1}" if i == 0 else None)

    ax1.set_ylabel("|Z|  [Ω]", fontsize=12)
    ax1.grid(True, which="both", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right", fontsize=8, ncol=2)

    # --- θ ---
    ax2.semilogx(freq, p_mean_r, "o-", color="#1D4ED8", linewidth=2, markersize=3,
                 label="リリース (平均)")
    ax2.fill_between(freq, p_mean_r - p_std_r, p_mean_r + p_std_r,
                     color="#1D4ED8", alpha=0.15, label="リリース (±1σ)")

    ax2.semilogx(freq, p_mean_p, "s-", color="#B91C1C", linewidth=2, markersize=3,
                 label="プレス (平均)")
    ax2.fill_between(freq, p_mean_p - p_std_p, p_mean_p + p_std_p,
                     color="#B91C1C", alpha=0.15, label="プレス (±1σ)")

    for i, d in enumerate(release_sets):
        ax2.semilogx(d["frequency_Hz"], d["phase_deg"], "-",
                     color="#93C5FD", linewidth=0.5, alpha=0.5)
    for i, d in enumerate(press_sets):
        ax2.semilogx(d["frequency_Hz"], d["phase_deg"], "-",
                     color="#FCA5A5", linewidth=0.5, alpha=0.5)

    ax2.set_xlabel("周波数  [Hz]", fontsize=12)
    ax2.set_ylabel("位相角 θ  [deg]", fontsize=12)
    ax2.grid(True, which="both", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper right", fontsize=8, ncol=2)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# ─── 差分プロット ────────────────────────────────
def plot_diff(
    release_sets: list[dict[str, np.ndarray]],
    press_sets: list[dict[str, np.ndarray]],
) -> mpl_figure.Figure:
    """
    プレス - リリース の差分（ΔZ, Δθ）を可視化する。
    差分のゼロラインを基準に変化量を明示。
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    fig.suptitle("プレス − リリース 差分 (Δ)", fontsize=14, fontweight="bold")

    freq = release_sets[0]["frequency_Hz"]

    z_r = np.vstack([d["impedance_ohm"] for d in release_sets]).mean(axis=0)
    z_p = np.vstack([d["impedance_ohm"] for d in press_sets]).mean(axis=0)
    p_r = np.vstack([d["phase_deg"] for d in release_sets]).mean(axis=0)
    p_p = np.vstack([d["phase_deg"] for d in press_sets]).mean(axis=0)

    dz = z_p - z_r   # ΔZ
    dp = p_p - p_r    # Δθ
    dz_pct = dz / z_r * 100  # 変化率 [%]

    # ── ΔZ ──
    ax1.semilogx(freq, dz, "o-", color="#7C3AED", markersize=3, linewidth=1.5,
                 label="Δ|Z| = Press − Release")
    ax1.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax1.set_ylabel("Δ|Z|  [Ω]", fontsize=12)
    ax1.grid(True, which="both", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right", fontsize=9)

    # 変化率を右軸に
    ax1r = ax1.twinx()
    ax1r.semilogx(freq, dz_pct, "--", color="#A78BFA", linewidth=0.8, alpha=0.6)
    ax1r.set_ylabel("変化率  [%]", fontsize=10, color="#A78BFA")
    ax1r.tick_params(axis="y", labelcolor="#A78BFA")

    # ── Δθ ──
    ax2.semilogx(freq, dp, "s-", color="#0891B2", markersize=3, linewidth=1.5,
                 label="Δθ = Press − Release")
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_xlabel("周波数  [Hz]", fontsize=12)
    ax2.set_ylabel("Δθ  [deg]", fontsize=12)
    ax2.grid(True, which="both", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper right", fontsize=9)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# ─── メイン ──────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ゲルインピーダンス リリース/プレス比較プロット")
    parser.add_argument("--name", default="sample_gel", help="サンプル名で絞り込み")
    parser.add_argument("--release-count", type=int, default=3,
                        help="前半何回をリリースとするか (default=3)")
    parser.add_argument("--show", action="store_true", help="ウィンドウ表示する")
    args = parser.parse_args()

    # ── ファイル収集 ──
    # 新命名規則 (release/press ラベル付き) を先に探す
    release_files = sorted(find_files(MEASURE_DIR, f"{args.name}_release_*_full.csv"))
    press_files   = sorted(find_files(MEASURE_DIR, f"{args.name}_press_*_full.csv"))

    # ラベル無し旧命名 → タイムスタンプ順で前半=release, 後半=press に自動分割
    if not release_files or not press_files:
        all_full = sorted(find_files(MEASURE_DIR, f"{args.name}_*_full.csv"))
        if len(all_full) < 2:
            print(f"[ERROR] full CSV が 2 件以上見つかりません (pattern: {args.name}_*_full.csv)")
            print(f"        MEASURE_DIR: {MEASURE_DIR}")
            sys.exit(1)

        n_release = args.release_count
        release_files = all_full[:n_release]
        press_files   = all_full[n_release:]
        print(f"[INFO] ラベル無し CSV を検出 → 前半 {n_release} 件=リリース, "
              f"後半 {len(press_files)} 件=プレス として分割")

    print(f"[INFO] リリースデータ: {len(release_files)} ファイル")
    for f in release_files:
        print(f"       {os.path.basename(f)}")
    print(f"[INFO] プレスデータ:   {len(press_files)} ファイル")
    for f in press_files:
        print(f"       {os.path.basename(f)}")

    release_data = [load_csv(f) for f in release_files]
    press_data   = [load_csv(f) for f in press_files]

    ts = timestamp()

    # ── 1. リリース全回 Bode プロット ──
    fig1 = plot_group_bode(
        release_data,
        [f"R{i+1}" for i in range(len(release_data))],
        "リリース — Bode プロット (各回重ね描き)",
        RELEASE_COLORS, RELEASE_PHASE,
    )
    p1 = os.path.join(GRAPH_DIR, f"bode_release_{args.name}_{ts}.png")
    fig1.savefig(p1, dpi=150)
    print(f"[SAVE] {p1}")

    # ── 2. プレス全回 Bode プロット ──
    fig2 = plot_group_bode(
        press_data,
        [f"P{i+1}" for i in range(len(press_data))],
        "プレス — Bode プロット (各回重ね描き)",
        PRESS_COLORS, PRESS_PHASE,
    )
    p2 = os.path.join(GRAPH_DIR, f"bode_press_{args.name}_{ts}.png")
    fig2.savefig(p2, dpi=150)
    print(f"[SAVE] {p2}")

    # ── 3. リリース vs プレス 比較 ──
    fig3 = plot_release_vs_press(release_data, press_data)
    p3 = os.path.join(GRAPH_DIR, f"bode_comparison_{args.name}_{ts}.png")
    fig3.savefig(p3, dpi=150)
    print(f"[SAVE] {p3}")

    # ── 4. 差分プロット ──
    fig4 = plot_diff(release_data, press_data)
    p4 = os.path.join(GRAPH_DIR, f"bode_diff_{args.name}_{ts}.png")
    fig4.savefig(p4, dpi=150)
    print(f"[SAVE] {p4}")

    if args.show:
        plt.show()

    print("[DONE] グラフ生成完了 (4枚)")


if __name__ == "__main__":
    main()
