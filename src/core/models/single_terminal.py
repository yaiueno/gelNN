"""
単一端子押圧検出器 - 1端子のタッチ有無を判定

既存の IDataSource を利用して1ペアのインピーダンスを測定し、
ベースライン（非押圧時）との差分から押圧状態を判定します。
"""

import numpy as np
import time
import logging
from typing import Optional, Tuple, List
from collections import deque

from src.core.interfaces import IDataSource
from src.utils import config

logger = logging.getLogger(__name__)


class SingleTerminalDetector:
    """
    単一端子の押圧検出器

    指定した1測定ペアのインピーダンスを監視し、
    ベースライン(非タッチ時)からの変化量で押圧を判定します。
    """

    def __init__(self, data_source: IDataSource, pair_index: int = 0):
        """
        初期化

        Args:
            data_source: IDataSource 実装（実機 or HILS）
            pair_index: 使用する測定ペアのインデックス (config.MEASUREMENT_PAIRS 内)
        """
        self.data_source = data_source
        self.pair_index = pair_index

        # ベースライン（非押圧時のインピーダンス）
        self._baseline_magnitude: Optional[float] = None
        self._baseline_phase: Optional[float] = None
        self._baseline_std: float = 0.0  # 標準偏差（ノイズ幅）

        # 検出しきい値
        # ベースラインからの変動がこの倍率 × 標準偏差を超えたら押圧とみなす
        self._threshold_sigma: float = 3.0
        # 絶対しきい値（ベースライン振幅の何%変化で押圧とみなすか）
        self._threshold_ratio: float = 0.05  # 5%

        # 履歴バッファ（グラフ描画用）
        self._history_maxlen = 200
        self._magnitude_history: deque = deque(maxlen=self._history_maxlen)
        self._phase_history: deque = deque(maxlen=self._history_maxlen)
        self._time_history: deque = deque(maxlen=self._history_maxlen)
        self._press_history: deque = deque(maxlen=self._history_maxlen)

        # キャリブレーション用バッファ
        self._calibration_samples: List[float] = []
        self._calibration_phase_samples: List[float] = []

        # 状態
        self._is_pressed = False
        self._current_magnitude = 0.0
        self._current_phase = 0.0
        self._start_time = time.time()

        # ペア情報
        pair = config.MEASUREMENT_PAIRS[self.pair_index]
        src_name = config.TERMINAL_NAMES.get(pair[0], str(pair[0]))
        snk_name = config.TERMINAL_NAMES.get(pair[1], str(pair[1]))
        self._pair_label = f"{src_name}→{snk_name}"

        logger.info(f"SingleTerminalDetector: ペア {self.pair_index} ({self._pair_label}) で初期化")

    # =========================================
    # プロパティ
    # =========================================

    @property
    def pair_label(self) -> str:
        """使用中の測定ペア名"""
        return self._pair_label

    @property
    def is_calibrated(self) -> bool:
        """キャリブレーション済みかどうか"""
        return self._baseline_magnitude is not None

    @property
    def is_pressed(self) -> bool:
        """現在押圧されているか"""
        return self._is_pressed

    @property
    def current_magnitude(self) -> float:
        """最新のインピーダンス振幅 [Ω]"""
        return self._current_magnitude

    @property
    def current_phase(self) -> float:
        """最新の位相 [rad]"""
        return self._current_phase

    @property
    def baseline_magnitude(self) -> Optional[float]:
        """ベースラインインピーダンス [Ω]"""
        return self._baseline_magnitude

    @property
    def deviation_ratio(self) -> float:
        """ベースラインからの偏差率 (0.0=変化なし, 1.0=100%変化)"""
        if self._baseline_magnitude is None or self._baseline_magnitude == 0:
            return 0.0
        return abs(self._current_magnitude - self._baseline_magnitude) / self._baseline_magnitude

    @property
    def threshold_sigma(self) -> float:
        return self._threshold_sigma

    @threshold_sigma.setter
    def threshold_sigma(self, value: float):
        self._threshold_sigma = max(1.0, value)

    @property
    def threshold_ratio(self) -> float:
        return self._threshold_ratio

    @threshold_ratio.setter
    def threshold_ratio(self, value: float):
        self._threshold_ratio = max(0.01, min(1.0, value))

    # =========================================
    # キャリブレーション
    # =========================================

    def start_calibration(self) -> None:
        """キャリブレーション開始（バッファクリア）"""
        self._calibration_samples.clear()
        self._calibration_phase_samples.clear()
        logger.info("キャリブレーション開始: サンプル収集を開始します")

    def add_calibration_sample(self) -> Tuple[float, float]:
        """
        キャリブレーション用サンプルを1つ取得して追加

        Returns:
            (magnitude, phase): 測定値
        """
        magnitude, phase = self._measure_single()
        self._calibration_samples.append(magnitude)
        self._calibration_phase_samples.append(phase)
        logger.debug(f"キャリブレーションサンプル #{len(self._calibration_samples)}: "
                     f"{magnitude:.2f}Ω, {phase:.4f}rad")
        return magnitude, phase

    def finish_calibration(self, min_samples: int = 5) -> bool:
        """
        キャリブレーション完了: ベースラインを確定

        Args:
            min_samples: 最低サンプル数

        Returns:
            bool: 成功時 True
        """
        n = len(self._calibration_samples)
        if n < min_samples:
            logger.warning(f"サンプル不足: {n}/{min_samples}")
            return False

        self._baseline_magnitude = float(np.mean(self._calibration_samples))
        self._baseline_phase = float(np.mean(self._calibration_phase_samples))
        self._baseline_std = float(np.std(self._calibration_samples))

        logger.info(f"キャリブレーション完了: baseline={self._baseline_magnitude:.2f}Ω "
                    f"± {self._baseline_std:.2f}Ω ({n}サンプル)")
        return True

    def set_baseline_manual(self, magnitude: float, std: float = 0.0) -> None:
        """
        ベースラインを手動設定

        Args:
            magnitude: ベースラインインピーダンス [Ω]
            std: 標準偏差 [Ω]
        """
        self._baseline_magnitude = magnitude
        self._baseline_std = std
        logger.info(f"ベースラインを手動設定: {magnitude:.2f}±{std:.2f}Ω")

    # =========================================
    # 測定・判定
    # =========================================

    def update(self) -> Tuple[bool, float, float]:
        """
        1回の測定と押圧判定を実行

        Returns:
            (is_pressed, magnitude, phase)
        """
        magnitude, phase = self._measure_single()
        self._current_magnitude = magnitude
        self._current_phase = phase

        # 押圧判定
        self._is_pressed = self._judge_press(magnitude)

        # 履歴記録
        elapsed = time.time() - self._start_time
        self._magnitude_history.append(magnitude)
        self._phase_history.append(phase)
        self._time_history.append(elapsed)
        self._press_history.append(self._is_pressed)

        return self._is_pressed, magnitude, phase

    def _measure_single(self) -> Tuple[float, float]:
        """
        指定ペアの1回測定

        Returns:
            (magnitude, phase)
        """
        impedance_vector = self.data_source.measure_impedance_vector()
        magnitude = impedance_vector[self.pair_index, 0]
        phase = impedance_vector[self.pair_index, 1]
        return float(magnitude), float(phase)

    def _judge_press(self, magnitude: float) -> bool:
        """
        押圧判定

        以下のいずれかを満たせば「押圧」と判定:
        1. ベースラインからの変動が threshold_sigma × 標準偏差 を超える
        2. ベースラインからの変動率が threshold_ratio を超える

        Args:
            magnitude: 測定したインピーダンス振幅 [Ω]

        Returns:
            bool: 押圧と判定された場合 True
        """
        if self._baseline_magnitude is None:
            return False

        deviation = abs(magnitude - self._baseline_magnitude)

        # 方法1: σベース
        if self._baseline_std > 0:
            if deviation > self._threshold_sigma * self._baseline_std:
                return True

        # 方法2: 比率ベース
        if self._baseline_magnitude > 0:
            ratio = deviation / self._baseline_magnitude
            if ratio > self._threshold_ratio:
                return True

        return False

    # =========================================
    # 履歴データ取得
    # =========================================

    def get_magnitude_history(self) -> Tuple[List[float], List[float]]:
        """
        振幅履歴を取得

        Returns:
            (times, magnitudes)
        """
        return list(self._time_history), list(self._magnitude_history)

    def get_press_history(self) -> Tuple[List[float], List[bool]]:
        """
        押圧履歴を取得

        Returns:
            (times, press_states)
        """
        return list(self._time_history), list(self._press_history)

    def clear_history(self) -> None:
        """履歴クリア"""
        self._magnitude_history.clear()
        self._phase_history.clear()
        self._time_history.clear()
        self._press_history.clear()
        self._start_time = time.time()

    # =========================================
    # 情報取得
    # =========================================

    def get_status_dict(self) -> dict:
        """
        現在の状態を辞書で取得（GUI表示用）

        Returns:
            dict: 状態情報
        """
        return {
            "pair_label": self._pair_label,
            "pair_index": self.pair_index,
            "is_calibrated": self.is_calibrated,
            "is_pressed": self._is_pressed,
            "current_magnitude": self._current_magnitude,
            "current_phase": self._current_phase,
            "baseline_magnitude": self._baseline_magnitude,
            "baseline_std": self._baseline_std,
            "deviation_ratio": self.deviation_ratio,
            "threshold_sigma": self._threshold_sigma,
            "threshold_ratio": self._threshold_ratio,
        }
