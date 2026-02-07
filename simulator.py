"""
HILSシミュレータ - ハードウェアなしでテスト可能なシミュレータ

物理モデルに基づいてインピーダンスを計算し、
実機なしでもデータ収集・学習・推論のテストができます。
"""

import numpy as np
import time
from typing import Tuple, Optional
import logging

from interfaces import IDataSource
import config

logger = logging.getLogger(__name__)


class HILSSimulatorSource(IDataSource):
    """
    HILS（Hardware-In-the-Loop Simulation）シミュレータ
    
    距離減衰モデルとノイズを用いて、タッチ位置に応じた
    インピーダンスをシミュレートします。
    """
    
    def __init__(self):
        """初期化"""
        self._connected = False
        self._ground_truth_x = 50.0  # デフォルト位置 [mm]
        self._ground_truth_y = 50.0
        
        # 端子位置を取得
        self.terminal_positions = config.TERMINAL_POSITIONS
        
        logger.info("HILSシミュレータを初期化しました")
    
    def connect(self) -> bool:
        """
        シミュレータに接続（常に成功）
        
        Returns:
            bool: 常にTrue
        """
        self._connected = True
        logger.info("HILSシミュレータに接続しました")
        return True
    
    def disconnect(self) -> None:
        """シミュレータから切断"""
        self._connected = False
        logger.info("HILSシミュレータから切断しました")
    
    def is_connected(self) -> bool:
        """
        接続状態を確認
        
        Returns:
            bool: 接続中の場合True
        """
        return self._connected
    
    def set_ground_truth(self, x: float, y: float) -> None:
        """
        正解位置を設定
        
        この位置に基づいてインピーダンスを計算します。
        
        Args:
            x: X座標 [mm]
            y: Y座標 [mm]
        """
        self._ground_truth_x = x
        self._ground_truth_y = y
        logger.debug(f"正解位置を設定: ({x:.2f}, {y:.2f}) mm")
    
    def get_ground_truth(self) -> Tuple[float, float]:
        """
        現在設定されている正解位置を取得
        
        Returns:
            Tuple[float, float]: (x, y) [mm]
        """
        return (self._ground_truth_x, self._ground_truth_y)
    
    def measure_impedance_vector(self) -> np.ndarray:
        """
        全ペアのインピーダンスを測定（シミュレート）
        
        Returns:
            np.ndarray: shape=(N_pairs, 2) の配列
                        各行は [Magnitude[Ω], Phase[rad]]
        
        Raises:
            RuntimeError: 未接続時
        """
        if not self._connected:
            raise RuntimeError("シミュレータが接続されていません")
        
        # タッチ位置
        touch_pos = np.array([self._ground_truth_x, self._ground_truth_y])
        
        # 各ペアのインピーダンスを計算
        impedances = []
        
        for source_ch, sink_ch in config.MEASUREMENT_PAIRS:
            # 端子名を取得
            source_name = config.TERMINAL_NAMES[source_ch]
            sink_name = config.TERMINAL_NAMES[sink_ch]
            
            # 端子位置
            source_pos = np.array(self.terminal_positions[source_name])
            sink_pos = np.array(self.terminal_positions[sink_name])
            
            # 距離減衰モデルでインピーダンスを計算
            magnitude = self._calculate_impedance(touch_pos, source_pos, sink_pos)
            
            # 位相はランダムに設定（簡易モデル）
            phase = np.random.uniform(-np.pi/4, np.pi/4)
            
            impedances.append([magnitude, phase])
        
        impedance_vector = np.array(impedances)
        
        logger.debug(f"インピーダンス測定完了: {impedance_vector.shape}")
        
        return impedance_vector
    
    def _calculate_impedance(self, 
                            touch_pos: np.ndarray, 
                            source_pos: np.ndarray, 
                            sink_pos: np.ndarray) -> float:
        """
        距離減衰モデルでインピーダンスを計算
        
        修正モデル:
        - 距離に対する感度を向上
        - 指数関数的な減衰を導入して、近くのタッチをより強く反映
        
        Args:
            touch_pos: タッチ位置 [mm]
            source_pos: Source端子位置 [mm]
            sink_pos: Sink端子位置 [mm]
        
        Returns:
            float: インピーダンス振幅 [Ω]
        """
        # Source-Sink間の直線経路からの距離
        line_vec = sink_pos - source_pos
        line_length = np.linalg.norm(line_vec)
        
        if line_length < 1e-6:
            distance = np.linalg.norm(touch_pos - source_pos)
        else:
            # 線分への距離
            t = np.dot(touch_pos - source_pos, line_vec) / (line_length ** 2)
            t = np.clip(t, 0, 1)
            closest_point = source_pos + t * line_vec
            distance = np.linalg.norm(touch_pos - closest_point)
            
        # 2つの端子からの直接距離も考慮（端子付近の感度アップ）
        dist_source = np.linalg.norm(touch_pos - source_pos)
        dist_sink = np.linalg.norm(touch_pos - sink_pos)
        min_terminal_dist = min(dist_source, dist_sink)
        
        # ハイブリッド距離: 経路からの距離 + 端子への近接度
        effective_dist = distance * 0.7 + min_terminal_dist * 0.3
        
        # 距離に応じてインピーダンスを変化させる（感度調整）
        # 近くにあるほどインピーダンス低下
        # 指数的変化: Z = Base + Scale * (1 - exp(-dist/decay))
        decay_constant = 30.0  # 減衰距離定数 [mm]
        
        impedance_change = config.DISTANCE_FACTOR * 100.0 * (1.0 - np.exp(-effective_dist / decay_constant))
        impedance = config.BASE_IMPEDANCE + impedance_change
        
        # ノイズ付加
        noise = np.random.normal(0, config.NOISE_LEVEL * impedance)
        impedance += noise
        
        return max(impedance, 100.0)
    
    def get_device_info(self) -> str:
        """
        デバイス情報を取得
        
        Returns:
            str: デバイス情報の文字列
        """
        return f"HILS Simulator (Model: Distance Attenuation, Noise: {config.NOISE_LEVEL*100:.1f}%)"
