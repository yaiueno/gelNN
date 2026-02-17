"""
ゲルインピーダンス測定 — 共通設定
Analog Discovery 3 + WaveForms SDK (dwf)
"""

import os
from datetime import datetime

# ─── 測定パラメータ ───────────────────────────────
FREQ_START = 1000          # 開始周波数 [Hz]
FREQ_STOP  = 1_000_000   # 終了周波数 [Hz]
FREQ_STEPS = 100           # 周波数ステップ数（対数スケール）
REFERENCE_RESISTANCE = 1e3  # 基準抵抗 [Ω]
AMPLITUDE  = 1.0          # 励振振幅 [V]
OFFSET     = 0.0          # DCオフセット [V]

# ─── データ保存 ──────────────────────────────────
DATA_DIR       = os.path.join(os.path.dirname(__file__), "data")
MEASURE_DIR    = os.path.join(DATA_DIR, "measurement")   # 測定用データ
ANALYSIS_DIR   = os.path.join(DATA_DIR, "analysis")       # 分析用データ
GRAPH_DIR      = os.path.join(os.path.dirname(__file__), "graphs")

for d in [MEASURE_DIR, ANALYSIS_DIR, GRAPH_DIR]:
    os.makedirs(d, exist_ok=True)


def timestamp() -> str:
    """ファイル名用のタイムスタンプ"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
