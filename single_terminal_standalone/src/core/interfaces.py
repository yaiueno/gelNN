"""
インターフェース定義 - データソースの抽象クラス

このモジュールでは、HILS/実機の両方に共通するインターフェースを定義します。
Strategyパターンを使用して、実装を切り替え可能にします。
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
import numpy as np


class IDataSource(ABC):
    """
    データソースの抽象基底クラス
    
    HILS（シミュレータ）と実機（AD3+Arduino）の両方がこのインターフェースを実装します。
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        デバイスに接続
        
        Returns:
            bool: 接続成功時True、失敗時False
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        デバイスから切断
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        接続状態を確認
        
        Returns:
            bool: 接続中の場合True
        """
        pass
    
    @abstractmethod
    def set_ground_truth(self, x: float, y: float) -> None:
        """
        正解位置を設定（HILS用）
        
        実機では無視されますが、HILSシミュレータでは
        この位置に基づいてインピーダンスを計算します。
        
        Args:
            x: X座標 [mm]
            y: Y座標 [mm]
        """
        pass
    
    @abstractmethod
    def get_ground_truth(self) -> Optional[Tuple[float, float]]:
        """
        現在設定されている正解位置を取得(HILS用)
        
        実機では正解位置が不明なためNoneを返し、
        HILSシミュレータでは設定されたタッチ位置を返します。
        
        Returns:
            Tuple[float, float] | None: (x, y) [mm]、または不明の場合None
        """
        pass
    
    @abstractmethod
    def measure_impedance_vector(self) -> np.ndarray:
        """
        全ペアのインピーダンスを測定
        
        Returns:
            np.ndarray: shape=(N_pairs, 2) の配列
                        各行は [Magnitude[Ω], Phase[rad]]
        
        Raises:
            RuntimeError: 測定失敗時
        """
        pass
    
    @abstractmethod
    def get_device_info(self) -> str:
        """
        デバイス情報を取得
        
        Returns:
            str: デバイス情報の文字列
        """
        pass


class MeasurementResult:
    """
    測定結果を格納するデータクラス
    """
    
    def __init__(self, 
                 impedance_vector: np.ndarray,
                 ground_truth: Tuple[float, float] = None,
                 timestamp: float = None):
        """
        Args:
            impedance_vector: インピーダンスベクトル [Magnitude, Phase] x N_pairs
            ground_truth: 正解位置 (x, y) [mm]、推論時はNone
            timestamp: タイムスタンプ（Unix時間）
        """
        self.impedance_vector = impedance_vector
        self.ground_truth = ground_truth
        self.timestamp = timestamp
    
    def get_magnitude_vector(self) -> np.ndarray:
        """
        振幅成分のみを取得
        
        Returns:
            np.ndarray: shape=(N_pairs,) の振幅ベクトル
        """
        return self.impedance_vector[:, 0]
    
    def get_phase_vector(self) -> np.ndarray:
        """
        位相成分のみを取得
        
        Returns:
            np.ndarray: shape=(N_pairs,) の位相ベクトル
        """
        return self.impedance_vector[:, 1]
    
    def to_feature_vector(self) -> np.ndarray:
        """
        機械学習用の特徴ベクトルに変換
        
        インピーダンスのダイナミックレンジが広いため、
        振幅（Magnitude）に対数変換を適用して正規化しやすくします。
        """
        magnitude = self.impedance_vector[:, 0]
        phase = self.impedance_vector[:, 1]
        
        # 対数変換 (log10)
        log_magnitude = np.log10(magnitude + 1.0)  # +1 to avoid log(0)
        
        # 結合してフラット化
        return np.concatenate([log_magnitude, phase])
