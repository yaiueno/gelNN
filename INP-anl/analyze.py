"""
analyze.py — 測定データの分析 & 統計処理
──────────────────────────────────────────────────
保存された CSV を読み込み、基本統計量を算出して分析用 CSV を出力する。

使い方:
    python analyze.py                            # 最新の full CSV を分析
    python analyze.py --file data/measurement/sample_gel_20260217_full.csv
"""

import argparse
import csv
import glob
import os
import sys

import numpy as np

from config import ANALYSIS_DIR, MEASURE_DIR


def load_csv(filepath: str) -> list[dict]:
    """CSV を読み込んで辞書リストで返す"""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append({k: float(v) for k, v in row.items()})
    return rows


def compute_statistics(rows: list[dict]) -> dict:
    """基本統計量（|Z|, θ）を算出"""
    z_vals = np.array([r["impedance_ohm"] for r in rows])
    p_vals = np.array([r["phase_deg"] for r in rows])
    f_vals = np.array([r["frequency_Hz"] for r in rows])

    stats = {
        "n_points": len(rows),
        "freq_min_Hz": float(f_vals.min()),
        "freq_max_Hz": float(f_vals.max()),
        "Z_mean_ohm": float(z_vals.mean()),
        "Z_std_ohm": float(z_vals.std()),
        "Z_min_ohm": float(z_vals.min()),
        "Z_max_ohm": float(z_vals.max()),
        "phase_mean_deg": float(p_vals.mean()),
        "phase_std_deg": float(p_vals.std()),
    }
    return stats


def find_latest_csv(directory: str, pattern: str = "*_full.csv") -> str | None:
    """指定ディレクトリ内の最新 CSV を返す"""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def print_stats(stats: dict) -> None:
    """統計量を見やすく表示"""
    print("\n┌─────────────────────────────────────────┐")
    print("│         インピーダンス分析結果           │")
    print("├─────────────────────────────────────────┤")
    print(f"│ データ点数      : {stats['n_points']:>10}            │")
    print(f"│ 周波数範囲 [Hz] : {stats['freq_min_Hz']:>10.1f} – {stats['freq_max_Hz']:<10.1f}│")
    print(f"│ |Z| 平均  [Ω]  : {stats['Z_mean_ohm']:>10.2f}            │")
    print(f"│ |Z| 標準偏差    : {stats['Z_std_ohm']:>10.2f}            │")
    print(f"│ |Z| 範囲  [Ω]  : {stats['Z_min_ohm']:>10.2f} – {stats['Z_max_ohm']:<10.2f}│")
    print(f"│ θ 平均    [deg] : {stats['phase_mean_deg']:>10.2f}            │")
    print(f"│ θ 標準偏差      : {stats['phase_std_deg']:>10.2f}            │")
    print("└─────────────────────────────────────────┘")


def main():
    parser = argparse.ArgumentParser(description="ゲルインピーダンスデータ分析")
    parser.add_argument("--file", default=None, help="分析する CSV ファイルパス")
    args = parser.parse_args()

    # ファイル決定
    if args.file:
        filepath = args.file
    else:
        filepath = find_latest_csv(MEASURE_DIR)
        if filepath is None:
            print("[ERROR] 測定データが見つかりません。先に measure.py を実行してください。")
            sys.exit(1)
        print(f"[INFO] 最新ファイルを使用: {filepath}")

    # データ読み込み & 統計
    rows = load_csv(filepath)
    stats = compute_statistics(rows)
    print_stats(stats)

    # 分析結果を CSV に出力
    base = os.path.splitext(os.path.basename(filepath))[0]
    stats_path = os.path.join(ANALYSIS_DIR, f"{base}_stats.csv")
    with open(stats_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats.keys()))
        writer.writeheader()
        writer.writerow(stats)
    print(f"[SAVE] 統計結果 → {stats_path}")


if __name__ == "__main__":
    main()
