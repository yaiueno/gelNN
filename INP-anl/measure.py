"""
measure.py — Analog Discovery 3 インピーダンスアナライザーによるゲル測定
──────────────────────────────────────────────────
WaveForms SDK (dwf) を使い、周波数スイープを実行して
|Z|, θ, Rs, Xs を CSV に保存する。

※ diag_ad3.py で動作確認済みのフローに準拠

使い方:
    python measure.py                       # デフォルト: sample_gel
    python measure.py --name pva_gel_5pct   # サンプル名を指定
    python measure.py --name pva --rounds 6 # 6 回連続測定 (1-3: release, 4-6: press)
    python measure.py --name pva --rounds 6 --release 3 --press 3
"""

import argparse
import csv
import math
import os
import sys
import time

import numpy as np

# プロジェクトルート（gelNN）をパスに追加して dwfconstants を読めるようにする
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ── WaveForms SDK ──
from ctypes import (
    byref,
    c_byte,
    c_double,
    c_int,
    cdll,
    create_string_buffer,
)

from src.hardware.dwfconstants import *  # noqa: F403, F401  (DwfAnalogImpedance* 定数)

# OS に応じた DWF ライブラリのロード
if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

# SDK バージョン表示
_ver = create_string_buffer(32)
dwf.FDwfGetVersion(_ver)
print(f"[INFO] WaveForms SDK v{_ver.value.decode()}")

from config import (
    AMPLITUDE,
    ANALYSIS_DIR,
    FREQ_START,
    FREQ_STEPS,
    FREQ_STOP,
    MEASURE_DIR,
    OFFSET,
    REFERENCE_RESISTANCE,
    timestamp,
)


# ────────────────────────────────────────────────
# デバイス接続
# ────────────────────────────────────────────────
def open_device() -> c_int:
    """Analog Discovery 3 を開く（失敗時は全クローズしてリトライ）"""
    # デバイス列挙
    cDevice = c_int()
    dwf.FDwfEnum(c_int(0), byref(cDevice))
    print(f"[INFO] 検出デバイス数: {cDevice.value}")

    if cDevice.value == 0:
        print("[ERROR] デバイスが見つかりません。USB 接続を確認してください。")
        sys.exit(1)

    for i in range(cDevice.value):
        name = create_string_buffer(64)
        sn = create_string_buffer(32)
        dwf.FDwfEnumDeviceName(c_int(i), name)
        dwf.FDwfEnumSN(c_int(i), sn)
        print(f"  Device {i}: {name.value.decode()} (SN: {sn.value.decode()})")

    # オープン
    hdwf = c_int()
    print("[INFO] デバイスを開いています…")
    dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

    if hdwf.value == 0:
        print("[WARN] 最初のオープン失敗 → 全デバイスをクローズしてリトライ…")
        dwf.FDwfDeviceCloseAll()
        time.sleep(1.0)
        dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

    if hdwf.value == 0:
        szerr = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(szerr)
        print(f"[ERROR] デバイスを開けません: {szerr.value.decode()}")
        print("       → WaveForms アプリが開いていれば閉じてください")
        sys.exit(1)

    print(f"[INFO] デバイス接続成功 (Handle: {hdwf.value})")
    return hdwf


# ────────────────────────────────────────────────
# インピーダンスアナライザー設定
# ────────────────────────────────────────────────
def configure_impedance(hdwf: c_int) -> None:
    """インピーダンスアナライザーの設定（diag_ad3.py 準拠）"""
    # モード設定: 8 = W1-C1-DUT-C2-R-GND
    dwf.FDwfAnalogImpedanceModeSet(hdwf, c_int(8))
    # 基準抵抗
    dwf.FDwfAnalogImpedanceReferenceSet(hdwf, c_double(REFERENCE_RESISTANCE))
    # 初回周波数（スイープ開始前のデフォルト）
    dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(FREQ_START))
    # 励振振幅
    dwf.FDwfAnalogImpedanceAmplitudeSet(hdwf, c_double(AMPLITUDE))
    # DCオフセット
    if OFFSET != 0.0:
        dwf.FDwfAnalogImpedanceOffsetSet(hdwf, c_double(OFFSET))

    # 設定を適用（まだ測定は開始しない）
    dwf.FDwfAnalogImpedanceConfigure(hdwf, c_int(0))
    time.sleep(0.5)  # 安定化待ち

    print(f"[INFO] 設定完了: Mode=8, Ref={REFERENCE_RESISTANCE}Ω, "
          f"Amp={AMPLITUDE}V, Freq={FREQ_START}–{FREQ_STOP}Hz")


# ────────────────────────────────────────────────
# 単一周波数での測定（diag_ad3.py の measure_impedance 準拠）
# ────────────────────────────────────────────────
def measure_single(hdwf: c_int) -> tuple | None:
    """1 回のインピーダンス測定を実行。タイムアウト時は None を返す。"""
    dwf.FDwfAnalogImpedanceConfigure(hdwf, c_int(1))

    sts = c_byte()
    for _ in range(500):
        dwf.FDwfAnalogImpedanceStatus(hdwf, byref(sts))
        if sts.value == 2:  # DwfStateDone
            break
        time.sleep(0.01)
    else:
        return None  # タイムアウト

    resistance = c_double()
    reactance = c_double()
    impedance = c_double()
    phase_val = c_double()

    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf, DwfAnalogImpedanceResistance, byref(resistance)  # noqa: F405
    )
    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf, DwfAnalogImpedanceReactance, byref(reactance)  # noqa: F405
    )
    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf, DwfAnalogImpedanceImpedance, byref(impedance)  # noqa: F405
    )
    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf, DwfAnalogImpedanceImpedancePhase, byref(phase_val)  # noqa: F405
    )

    return resistance.value, reactance.value, impedance.value, phase_val.value


# ────────────────────────────────────────────────
# 周波数スイープ
# ────────────────────────────────────────────────
def sweep(hdwf: c_int, warmup: int = 3) -> list[dict]:
    """周波数スイープを実行し、各周波数のデータを返す"""
    freqs = np.logspace(
        math.log10(FREQ_START),
        math.log10(FREQ_STOP),
        FREQ_STEPS,
    )

    # ウォームアップ（最初の数回は捨てる）
    print(f"[INFO] ウォームアップ中 ({warmup}回)…")
    for _ in range(warmup):
        measure_single(hdwf)
        time.sleep(0.05)

    results: list[dict] = []
    total = len(freqs)

    for i, f in enumerate(freqs):
        # 周波数設定
        dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(float(f)))
        time.sleep(0.005)  # セトリング

        meas = measure_single(hdwf)
        if meas is None:
            print(f"\n[WARN] タイムアウト: f={f:.1f} Hz — スキップ")
            continue

        r, x, z, ph = meas
        phase_deg = math.degrees(ph)

        row = {
            "frequency_Hz": float(f),
            "impedance_ohm": z,
            "phase_deg": phase_deg,
            "resistance_ohm": r,
            "reactance_ohm": x,
        }
        results.append(row)

        pct = (i + 1) / total * 100
        print(f"\r[SWEEP] {pct:5.1f}%  f={f:>10.1f} Hz  |Z|={z:>10.2f} Ω  θ={phase_deg:>7.2f}°", end="")

    print()  # 改行
    return results


def save_csv(rows: list[dict], filepath: str) -> None:
    """測定結果を CSV に保存"""
    fieldnames = [
        "frequency_Hz",
        "impedance_ohm",
        "phase_deg",
        "resistance_ohm",
        "reactance_ohm",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[SAVE] {filepath}")


def split_dataset(rows: list[dict], ratio: float = 0.8):
    """データセットを測定用と分析用に分割する（ratio: 測定用の割合）"""
    n = len(rows)
    n_measure = int(n * ratio)

    # 周波数順をシャッフルせず、等間隔にサンプリングして分割
    indices_analysis = set(
        np.linspace(0, n - 1, n - n_measure, dtype=int).tolist()
    )
    measure_data  = [r for i, r in enumerate(rows) if i not in indices_analysis]
    analysis_data = [r for i, r in enumerate(rows) if i in indices_analysis]

    return measure_data, analysis_data


# ────────────────────────────────────────────────
# メインエントリ
# ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ゲルインピーダンス測定")
    parser.add_argument("--name", default="sample_gel", help="サンプル名")
    parser.add_argument("--rounds", type=int, default=6, help="連続測定回数 (default=6)")
    parser.add_argument("--release", type=int, default=3,
                        help="リリース測定回数（前半, default=3）")
    parser.add_argument("--press", type=int, default=3,
                        help="プレス測定回数（後半, default=3）")
    parser.add_argument(
        "--ratio", type=float, default=0.8,
        help="測定用データの割合 (0-1, default=0.8)",
    )
    args = parser.parse_args()

    # rounds が明示指定されていなければ release + press に合わせる
    total_rounds = args.rounds
    if total_rounds < args.release + args.press:
        total_rounds = args.release + args.press
        print(f"[INFO] rounds を {total_rounds} に自動調整 (release={args.release} + press={args.press})")

    hdwf = open_device()
    configure_impedance(hdwf)

    try:
        for r in range(1, total_rounds + 1):
            # ラベル判定: 前半 = release, 後半 = press
            if r <= args.release:
                label = "release"
                label_disp = "リリース"
            else:
                label = "press"
                label_disp = "プレス"

            print(f"\n{'='*50}")
            print(f"  測定 {r}/{total_rounds}: {args.name} [{label_disp} #{r}]")
            print(f"{'='*50}")

            # プレス開始時にユーザーへ通知
            if r == args.release + 1:
                print("\n" + "!" * 50)
                print("  ★ ここからプレス測定です。ゲルを押してください。")
                print("!" * 50)
                input("  準備ができたら Enter を押してください… ")

            rows = sweep(hdwf)

            if not rows:
                print("[ERROR] 測定データが得られませんでした")
                continue

            # フルデータ保存（ラベル付き）
            ts = timestamp()
            full_path = os.path.join(
                MEASURE_DIR, f"{args.name}_{label}_r{r}_{ts}_full.csv"
            )
            save_csv(rows, full_path)

            # 測定用 / 分析用に分割して保存
            meas, anl = split_dataset(rows, ratio=args.ratio)
            save_csv(
                meas,
                os.path.join(MEASURE_DIR, f"{args.name}_{label}_r{r}_{ts}_meas.csv"),
            )
            save_csv(
                anl,
                os.path.join(ANALYSIS_DIR, f"{args.name}_{label}_r{r}_{ts}_anl.csv"),
            )

            print(f"[INFO] 全{len(rows)}点 → 測定用{len(meas)}点 / 分析用{len(anl)}点")
            print(f"[INFO] ラベル: {label_disp}")

            if r < total_rounds:
                print("[INFO] 次の測定まで 3 秒待機…")
                time.sleep(3)

    finally:
        dwf.FDwfDeviceClose(hdwf)
        print("[INFO] デバイスを閉じました")


if __name__ == "__main__":
    main()
