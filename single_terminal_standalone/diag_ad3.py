"""
AD3 診断スクリプト - 接続確認 & データロギング

Analog Discovery 3 に接続し、インピーダンス測定の生データを
ログファイルに記録して接続状態を確認します。

Usage:
    python diag_ad3.py
"""

import sys
import os
import time
import csv
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ========================================
# 1. SDK ロード確認
# ========================================
print("=" * 60)
print("AD3 診断スクリプト")
print("=" * 60)

try:
    from ctypes import *
    print("[OK] ctypes ロード成功")
except ImportError as e:
    print(f"[NG] ctypes ロード失敗: {e}")
    sys.exit(1)

try:
    from src.hardware.dwfconstants import *
    print("[OK] dwfconstants ロード成功")
except ImportError as e:
    print(f"[NG] dwfconstants ロード失敗: {e}")
    sys.exit(1)

try:
    if sys.platform.startswith("win"):
        dwf = cdll.dwf
    elif sys.platform.startswith("darwin"):
        dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
    else:
        dwf = cdll.LoadLibrary("libdwf.so")
    print("[OK] WaveForms DWF SDK ロード成功")
except Exception as e:
    print(f"[NG] WaveForms DWF SDK ロード失敗: {e}")
    print("     → WaveForms ソフトウェアがインストールされているか確認してください")
    sys.exit(1)

# SDK バージョン
version = create_string_buffer(32)
dwf.FDwfGetVersion(version)
print(f"     SDK Version: {version.value.decode()}")

# ========================================
# 2. デバイス検出 & 接続
# ========================================
print()
print("-" * 60)
print("デバイス接続テスト")
print("-" * 60)

# 接続されているデバイス数
cDevice = c_int()
dwf.FDwfEnum(c_int(0), byref(cDevice))
print(f"検出されたデバイス数: {cDevice.value}")

if cDevice.value == 0:
    print("[NG] デバイスが見つかりません！")
    print("     → USB ケーブルが接続されているか確認")
    print("     → WaveForms アプリで認識されるか確認")
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    err_msg = szerr.value.decode()
    if err_msg:
        print(f"     SDK エラー: {err_msg}")
    sys.exit(1)

# デバイス情報表示
for i in range(cDevice.value):
    deviceName = create_string_buffer(64)
    dwf.FDwfEnumDeviceName(c_int(i), deviceName)
    serialNum = create_string_buffer(32)
    dwf.FDwfEnumSN(c_int(i), serialNum)
    print(f"  Device {i}: {deviceName.value.decode()} (SN: {serialNum.value.decode()})")

# デバイスオープン（占有中なら全クローズしてリトライ）
hdwf = c_int()
print("\nデバイスを開いています...")
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

if hdwf.value == 0:
    print("  最初のオープン失敗 → 全デバイスをクローズしてリトライ...")
    dwf.FDwfDeviceCloseAll()
    time.sleep(1.0)
    dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

if hdwf.value == 0:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(f"[NG] デバイスオープン失敗: {szerr.value.decode()}")
    print("     → WaveForms アプリが開いていれば閉じてください")
    sys.exit(1)

print(f"[OK] デバイスオープン成功 (Handle: {hdwf.value})")

# ========================================
# 3. インピーダンスアナライザ設定
# ========================================
print()
print("-" * 60)
print("インピーダンスアナライザ設定")
print("-" * 60)

FREQ = 1000.0   # Hz
AMP = 0.1       # V
REF_R = 10000.0 # Ω

print(f"  測定周波数:   {FREQ} Hz")
print(f"  励起振幅:     {AMP} V")
print(f"  リファレンスR: {REF_R} Ω")

dwf.FDwfAnalogImpedanceModeSet(hdwf, c_int(8))
dwf.FDwfAnalogImpedanceReferenceSet(hdwf, c_double(REF_R))
dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(FREQ))
dwf.FDwfAnalogImpedanceAmplitudeSet(hdwf, c_double(AMP))

# 設定適用 & 安定化待ち
dwf.FDwfAnalogImpedanceConfigure(hdwf, c_int(0))
print("  設定適用中... (0.5秒待機)")
time.sleep(0.5)
print("[OK] 設定完了")

# ========================================
# 4. 単発測定テスト（固定周波数）
# ========================================
print()
print("-" * 60)
print(f"単発測定テスト ({FREQ} Hz)")
print("-" * 60)


def measure_impedance(hdwf_handle):
    """1回のインピーダンス測定を実行"""
    dwf.FDwfAnalogImpedanceConfigure(hdwf_handle, c_int(1))

    sts = c_byte()
    timeout_count = 0
    while True:
        dwf.FDwfAnalogImpedanceStatus(hdwf_handle, byref(sts))
        if sts.value == 2:  # DwfStateDone
            break
        time.sleep(0.01)
        timeout_count += 1
        if timeout_count > 500:
            return None, None, None, None

    # R と X を個別に取得 (正しい3引数方式)
    resistance = c_double()
    reactance = c_double()
    impedance = c_double()
    phase_val = c_double()

    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf_handle, DwfAnalogImpedanceResistance, byref(resistance)
    )
    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf_handle, DwfAnalogImpedanceReactance, byref(reactance)
    )
    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf_handle, DwfAnalogImpedanceImpedance, byref(impedance)
    )
    dwf.FDwfAnalogImpedanceStatusMeasure(
        hdwf_handle, DwfAnalogImpedanceImpedancePhase, byref(phase_val)
    )

    return resistance.value, reactance.value, impedance.value, phase_val.value


# ウォームアップ（最初の数回は捨てる）
print("ウォームアップ中 (3回測定)...")
for _ in range(3):
    measure_impedance(hdwf)
    time.sleep(0.05)

# 本測定 10回
print()
print(f"{'#':>3}  {'R [Ω]':>12}  {'X [Ω]':>12}  {'|Z| [Ω]':>12}  {'Phase [rad]':>12}  {'Phase [°]':>10}")
print("-" * 72)

results = []
all_zero = True

for i in range(10):
    r, x, z, ph = measure_impedance(hdwf)
    if r is None:
        print(f"{i+1:3}  *** タイムアウト ***")
        continue

    import math
    z_calc = math.sqrt(r**2 + x**2)
    ph_calc = math.atan2(x, r)
    phase_deg = math.degrees(ph_calc)

    if abs(r) > 0.001 or abs(x) > 0.001:
        all_zero = False

    print(f"{i+1:3}  {r:12.2f}  {x:12.2f}  {z:12.2f}  {ph_calc:12.6f}  {phase_deg:10.2f}")
    results.append({
        'n': i + 1,
        'R': r,
        'X': x,
        'Z_sdk': z,
        'Z_calc': z_calc,
        'phase_rad': ph_calc,
        'phase_deg': phase_deg,
    })
    time.sleep(0.05)

print()
if all_zero:
    print("[警告] R, X が全てゼロ付近です！")
    print("       → プローブが正しく接続されているか確認してください")
    print("       → W1+/1+ と 1-/GND 間に測定対象があるか確認")
else:
    print("[OK] 測定値が得られています")

# ========================================
# 5. 周波数スイープテスト (2kHz - 20kHz)
# ========================================
print()
print("-" * 60)
print("周波数スイープテスト (2 kHz - 20 kHz, 20点)")
print("-" * 60)

import numpy as np

sweep_freqs = np.logspace(np.log10(2000), np.log10(20000), 20)
sweep_results = []

print(f"{'Freq [Hz]':>10}  {'R [Ω]':>12}  {'X [Ω]':>12}  {'|Z| [Ω]':>12}  {'Phase [°]':>10}")
print("-" * 64)

for freq in sweep_freqs:
    dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(float(freq)))
    time.sleep(0.005)

    r, x, z, ph = measure_impedance(hdwf)
    if r is None:
        print(f"{freq:10.0f}  *** タイムアウト ***")
        continue

    z_calc = math.sqrt(r**2 + x**2)
    ph_calc = math.atan2(x, r)
    phase_deg = math.degrees(ph_calc)

    print(f"{freq:10.0f}  {r:12.2f}  {x:12.2f}  {z_calc:12.2f}  {phase_deg:10.2f}")
    sweep_results.append({
        'freq_hz': float(freq),
        'R': r,
        'X': x,
        'Z': z_calc,
        'phase_deg': phase_deg,
    })

# 周波数を元に戻す
dwf.FDwfAnalogImpedanceFrequencySet(hdwf, c_double(FREQ))

# X ピーク検出
if sweep_results:
    abs_x_vals = [abs(s['X']) for s in sweep_results]
    peak_idx = abs_x_vals.index(max(abs_x_vals))
    peak_entry = sweep_results[peak_idx]
    print()
    print(f"X ピーク検出: {peak_entry['freq_hz']:.0f} Hz, "
          f"X={peak_entry['X']:.1f} Ω, |Z|={peak_entry['Z']:.1f} Ω")

# ========================================
# 6. ログファイル保存
# ========================================
print()
print("-" * 60)
print("ログ保存")
print("-" * 60)

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# 固定周波数ログ
log_file1 = os.path.join(log_dir, f"diag_fixed_{timestamp}.csv")
with open(log_file1, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['n', 'R', 'X', 'Z_sdk', 'Z_calc', 'phase_rad', 'phase_deg'])
    w.writeheader()
    w.writerows(results)
print(f"[OK] 固定周波数ログ: {log_file1}")

# スイープログ
log_file2 = os.path.join(log_dir, f"diag_sweep_{timestamp}.csv")
with open(log_file2, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['freq_hz', 'R', 'X', 'Z', 'phase_deg'])
    w.writeheader()
    w.writerows(sweep_results)
print(f"[OK] スイープログ: {log_file2}")

# ========================================
# 7. 切断
# ========================================
print()
dwf.FDwfDeviceClose(hdwf)
print("[OK] デバイス切断")

# ========================================
# 判定サマリ
# ========================================
print()
print("=" * 60)
print("診断結果サマリ")
print("=" * 60)

if not results:
    print("  [NG] 測定データなし")
elif all_zero:
    print("  [NG] 全測定値がゼロ → プローブ接続を確認")
else:
    r_vals = [s['R'] for s in results]
    x_vals = [s['X'] for s in results]
    z_vals = [s['Z_calc'] for s in results]
    print(f"  R 範囲: {min(r_vals):.1f} ~ {max(r_vals):.1f} Ω")
    print(f"  X 範囲: {min(x_vals):.1f} ~ {max(x_vals):.1f} Ω")
    print(f"  |Z| 範囲: {min(z_vals):.1f} ~ {max(z_vals):.1f} Ω")

    if abs(max(r_vals) - min(r_vals)) < 0.1 and abs(max(x_vals) - min(x_vals)) < 0.1:
        print("  [OK] 測定値が安定しています")
    else:
        print("  [INFO] 測定値にばらつきがあります（接触不良の可能性）")

    if sweep_results:
        all_x_zero = all(abs(s['X']) < 0.01 for s in sweep_results)
        if all_x_zero:
            print("  [NG] スイープの X が全てゼロ → 接続かインピーダンス設定を確認")
        else:
            print(f"  [OK] スイープ X ピーク: {peak_entry['freq_hz']:.0f} Hz ({peak_entry['X']:.1f} Ω)")

print()
print("診断完了。ログは logs/ フォルダに保存されました。")
