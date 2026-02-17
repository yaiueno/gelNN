"""
設定ファイル - シングルモード用の必要最小限の設定

このモジュールでは、単一端子押圧検出に必要な設定を管理します。
"""

import os

# ========================================
# システムモード設定
# ========================================

# True: 実機（AD3 単体）を使用
# False: HILSシミュレータを使用
USE_REAL_HARDWARE = True

# ========================================
# インピーダンス測定設定
# ========================================

# 測定周波数 [Hz]
MEASUREMENT_FREQUENCY = 1000.0

# 測定電圧振幅 [V]
MEASUREMENT_AMPLITUDE = 0.1

# 測定するペアの定義 (Source_Ch, Sink_Ch)
# シングルモードでは1ペアのみ使用
MEASUREMENT_PAIRS = [
    (0, 1),  # Pair 0: A→B
    (0, 3),  # Pair 1: A→D
    (1, 2),  # Pair 2: B→C
    (1, 3),  # Pair 3: B→D
    (2, 3),  # Pair 4: C→D
    (0, 2),  # Pair 5: A→C
]

# 端子名マッピング
TERMINAL_NAMES = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
}

# ========================================
# HILS シミュレータ設定
# ========================================

# イオンゲルのサイズ [mm]
GEL_WIDTH = 100.0
GEL_HEIGHT = 100.0

# 端子位置 [mm] (X, Y)
TERMINAL_POSITIONS = {
    "A": (0.0, 0.0),
    "B": (100.0, 0.0),
    "C": (100.0, 100.0),
    "D": (0.0, 100.0),
}

# 距離減衰モデルのパラメータ
BASE_IMPEDANCE = 1000.0  # 基本インピーダンス [Ω]
DISTANCE_FACTOR = 50.0   # 距離係数 [Ω/mm]

# ノイズレベル（標準偏差の割合）
NOISE_LEVEL = 0.01  # 1%

# ========================================
# 機械学習設定
# ========================================

# 学習データの保存先（このフォルダからの相対パス）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(_BASE_DIR, "data")
MODEL_DIR = os.path.join(_BASE_DIR, "models")

# ニューラルネットワーク設定
HIDDEN_LAYER_SIZES = (32, 16)
MAX_ITERATIONS = 1000
RANDOM_STATE = 42

# ========================================
# ログ設定
# ========================================

LOG_LEVEL = "INFO"
LOG_DIR = os.path.join(_BASE_DIR, "logs")

# ========================================
# HILSサーバー設定
# ========================================

HILS_SERVER_HOST = "localhost"
HILS_SERVER_PORT = 8765
HILS_SERVER_URL = f"ws://{HILS_SERVER_HOST}:{HILS_SERVER_PORT}"

# HILSサーバーモード（True: サーバー経由, False: ローカル計算）
USE_HILS_SERVER = False  # スタンドアロンではデフォルトOFF

# ========================================
# 周波数設定
# ========================================

FREQUENCY_CONFIG_FILE = os.path.join(_BASE_DIR, "frequency_config.json")


def load_optimal_frequency():
    """
    最適周波数を設定ファイルから読み込む
    
    Returns:
        float: 最適周波数 [Hz]
    """
    import json
    from pathlib import Path
    
    config_path = Path(FREQUENCY_CONFIG_FILE)
    
    if not config_path.exists():
        return MEASUREMENT_FREQUENCY
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            optimal_freq = config_data.get('optimal_frequency', MEASUREMENT_FREQUENCY)
            return float(optimal_freq)
    except Exception as e:
        import logging
        logging.warning(f"周波数設定の読み込みに失敗: {e}")
        return MEASUREMENT_FREQUENCY


def get_frequency_analysis_info():
    """
    周波数分析の詳細情報を取得
    
    Returns:
        dict: 周波数分析情報（存在しない場合はNone）
    """
    import json
    from pathlib import Path
    
    config_path = Path(FREQUENCY_CONFIG_FILE)
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.warning(f"周波数設定の読み込みに失敗: {e}")
        return None
