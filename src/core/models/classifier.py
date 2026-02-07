"""
分類モデルラッパー - 9点分類モデルの推論

学習済みの分類モデルをロードし、インピーダンスベクトルから
9点の確率を計算します。
"""

import numpy as np
import pickle
import json
import os
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class TouchClassifier:
    """
    タッチ位置分類器
    
    学習済みモデルを使って、インピーダンスベクトルから
    9点のどこがタッチされたかの確率を計算します。
    """
    
    def __init__(self, 
                 model_path: str = "models/classifier_model.pkl",
                 scaler_path: str = "models/classifier_scaler.pkl",
                 grid_path: str = "models/grid_positions.json"):
        """
        初期化
        
        Args:
            model_path: モデルファイルのパス
            scaler_path: スケーラーファイルのパス
            grid_path: グリッド位置ファイルのパス
        """
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.grid_path = grid_path
        
        self.model = None
        self.scaler = None
        self.grid_positions = None
        
        self._load_model()
    
    def _load_model(self):
        """モデルとスケーラーをロード"""
        try:
            # モデルロード
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"モデルをロード: {self.model_path}")
            
            # スケーラーロード
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            logger.info(f"スケーラーをロード: {self.scaler_path}")
            
            # グリッド位置ロード
            with open(self.grid_path, 'r') as f:
                self.grid_positions = json.load(f)
            logger.info(f"グリッド位置をロード: {self.grid_path}")
            logger.info(f"  グリッド点数: {len(self.grid_positions)}")
            
        except FileNotFoundError as e:
            logger.error(f"モデルファイルが見つかりません: {e}")
            raise
        except Exception as e:
            logger.error(f"モデルのロードに失敗: {e}")
            raise
    
    def predict_probabilities(self, impedance_vector: np.ndarray) -> np.ndarray:
        """
        インピーダンスベクトルから9点の確率を計算
        
        Args:
            impedance_vector: インピーダンスベクトル shape=(N_pairs, 2)
        
        Returns:
            np.ndarray: 各点の確率 shape=(9,)
        
        Raises:
            RuntimeError: モデルが未ロードの場合
        """
        if self.model is None or self.scaler is None:
            raise RuntimeError("モデルがロードされていません")
        
        # MeasurementResultと同じ方法で特徴量を抽出
        magnitude = impedance_vector[:, 0]
        phase = impedance_vector[:, 1]
        
        # 対数変換
        log_magnitude = np.log10(magnitude + 1.0)
        
        # 結合
        features = np.concatenate([log_magnitude, phase])
        
        # 正規化
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # 確率予測
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        return probabilities
    
    def predict_class(self, impedance_vector: np.ndarray) -> int:
        """
        最も確率の高いクラスを予測
        
        Args:
            impedance_vector: インピーダンスベクトル
        
        Returns:
            int: 予測されたクラスID (0-8)
        """
        probabilities = self.predict_probabilities(impedance_vector)
        return int(np.argmax(probabilities))
    
    def get_grid_positions(self) -> List[Tuple[float, float]]:
        """
        グリッド位置を取得
        
        Returns:
            list: [(x, y), ...] のリスト（9点）
        """
        if self.grid_positions is None:
            raise RuntimeError("グリッド位置が未ロード")
        
        return self.grid_positions
    
    def get_grid_position(self, class_id: int) -> Tuple[float, float]:
        """
        指定クラスのグリッド位置を取得
        
        Args:
            class_id: クラスID (0-8)
        
        Returns:
            tuple: (x, y) 座標
        """
        if class_id < 0 or class_id >= len(self.grid_positions):
            raise ValueError(f"無効なクラスID: {class_id}")
        
        return tuple(self.grid_positions[class_id])
    
    def is_loaded(self) -> bool:
        """
        モデルがロード済みかチェック
        
        Returns:
            bool: ロード済みの場合True
        """
        return (self.model is not None and 
                self.scaler is not None and 
                self.grid_positions is not None)
    
    def get_model_info(self) -> str:
        """
        モデル情報を取得
        
        Returns:
            str: モデル情報の文字列
        """
        if not self.is_loaded():
            return "Model not loaded"
        
        n_classes = len(self.grid_positions)
        n_features = self.model.n_features_in_
        
        return f"MLPClassifier (Classes: {n_classes}, Features: {n_features})"
