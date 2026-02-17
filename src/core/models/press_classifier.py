"""
押圧分類NNモデル - 単一端子の押圧有無を判定する二値分類器

インピーダンス特徴量から「押されている / 押されていない」を判定する
MLPClassifier を学習・保存・ロード・推論するラッパークラスです。

特徴量モード:
  - 2D: [log10(mag+1), phase]                     (従来互換)
  - Sweep(10D): peak_freq, peak_mag, peak_phase,  (スペクトル特徴量)
                z_mean (low/mid/high),
                x_mean (low/mid/high), x_slope
"""

import numpy as np
import pickle
import os
import logging
from typing import Tuple, Optional, List, Dict
from datetime import datetime

from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from src.utils import config

logger = logging.getLogger(__name__)

# デフォルトの保存パス
_DEFAULT_MODEL_DIR = config.MODEL_DIR
_MODEL_FILE = "press_classifier_model.pkl"
_SCALER_FILE = "press_classifier_scaler.pkl"
_DATA_FILE = "press_training_data.npz"


# スイープ特徴量のキー順序 (10次元)
SWEEP_FEATURE_KEYS = [
    'peak_freq', 'peak_magnitude', 'peak_phase',
    'z_mean_low', 'z_mean_mid', 'z_mean_high',
    'x_mean_low', 'x_mean_mid', 'x_mean_high',
    'x_slope',
]


class PressClassifierModel:
    """
    押圧二値分類NN

    特徴量:
      2D: [log10(magnitude+1), phase]
      Sweep(10D): [log10(peak_freq), log10(peak_mag+1), peak_phase,
                   log10(z_low+1), log10(z_mid+1), log10(z_high+1),
                   x_low, x_mid, x_high, x_slope]
    ラベル: 0 = 非押圧, 1 = 押圧
    """

    def __init__(self, model_dir: str = _DEFAULT_MODEL_DIR, use_sweep: bool = False):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

        self.model: Optional[MLPClassifier] = None
        self.scaler: Optional[StandardScaler] = None

        # スイープモード（3D特徴量）
        self.use_sweep = use_sweep

        # 学習データバッファ
        self._X_buf: List[np.ndarray] = []   # shape=(2,) or (3,)
        self._y_buf: List[int] = []           # 0 or 1

        # 学習メトリクス
        self.train_accuracy: float = 0.0
        self.test_accuracy: float = 0.0
        self.n_train_samples: int = 0

    # =========================================
    # データ追加
    # =========================================

    def add_sample(self, magnitude: float, phase: float, label: int,
                    sweep_features: Optional[Dict] = None) -> None:
        """
        学習サンプルを1つ追加

        Args:
            magnitude: インピーダンス振幅 [Ω]
            phase: 位相 [rad]
            label: 0=非押圧, 1=押圧
            sweep_features: extract_sweep_features() の戻り値 dict (スイープモード時)
        """
        feat = self._to_features(magnitude, phase, sweep_features)
        self._X_buf.append(feat)
        self._y_buf.append(label)

    def add_samples_batch(self, magnitudes: np.ndarray, phases: np.ndarray, label: int,
                          sweep_features_list: Optional[List[Dict]] = None) -> None:
        """
        同一ラベルのサンプルをバッチ追加

        Args:
            magnitudes: shape=(N,)
            phases: shape=(N,)
            label: 0 or 1
            sweep_features_list: スイープ特徴量 dict のリスト (オプション)
        """
        for i, (m, p) in enumerate(zip(magnitudes, phases)):
            sf = sweep_features_list[i] if sweep_features_list is not None else None
            self.add_sample(float(m), float(p), label, sweep_features=sf)

    def get_sample_counts(self) -> Tuple[int, int]:
        """(非押圧サンプル数, 押圧サンプル数)"""
        y = np.array(self._y_buf)
        n0 = int(np.sum(y == 0))
        n1 = int(np.sum(y == 1))
        return n0, n1

    def clear_samples(self) -> None:
        """学習バッファをクリア"""
        self._X_buf.clear()
        self._y_buf.clear()

    @property
    def total_samples(self) -> int:
        return len(self._y_buf)

    # =========================================
    # 特徴量変換
    # =========================================

    def _to_features(self, magnitude: float, phase: float,
                      sweep_features: Optional[Dict] = None) -> np.ndarray:
        """
        特徴ベクトルに変換

        2D:  [log10(mag+1), phase]
        10D: [log10(peak_freq), log10(peak_mag+1), peak_phase,
              log10(z_low+1), log10(z_mid+1), log10(z_high+1),
              x_low, x_mid, x_high, x_slope]
        """
        if self.use_sweep and sweep_features is not None:
            sf = sweep_features
            return np.array([
                np.log10(sf['peak_freq']),
                np.log10(sf['peak_magnitude'] + 1.0),
                sf['peak_phase'],
                np.log10(sf['z_mean_low'] + 1.0),
                np.log10(sf['z_mean_mid'] + 1.0),
                np.log10(sf['z_mean_high'] + 1.0),
                sf['x_mean_low'],
                sf['x_mean_mid'],
                sf['x_mean_high'],
                sf['x_slope'],
            ])
        else:
            return np.array([np.log10(magnitude + 1.0), phase])

    # =========================================
    # 学習
    # =========================================

    def train(self,
              hidden_layers: Tuple[int, ...] = (16, 8),
              max_iter: int = 2000,
              test_ratio: float = 0.2) -> dict:
        """
        バッファ内データで MLPClassifier を学習

        Args:
            hidden_layers: 隠れ層
            max_iter: 最大反復
            test_ratio: テスト分割率

        Returns:
            dict: {"train_acc", "test_acc", "n_train", "n_test"}
        """
        if len(self._y_buf) < 4:
            raise ValueError(f"サンプル不足: {len(self._y_buf)} (最低4必要)")

        X = np.array(self._X_buf)
        y = np.array(self._y_buf)

        # ラベルが片方しかないとsplitが困る
        unique = np.unique(y)
        if len(unique) < 2:
            raise ValueError(f"両クラスのサンプルが必要です (現在ラベル={unique})")

        # スケーラー
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # 分割
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_ratio,
            random_state=config.RANDOM_STATE, stratify=y
        )

        # モデル
        self.model = MLPClassifier(
            hidden_layer_sizes=hidden_layers,
            max_iter=max_iter,
            random_state=config.RANDOM_STATE,
            early_stopping=True,
            validation_fraction=0.15,
        )
        self.model.fit(X_train, y_train)

        self.train_accuracy = float(self.model.score(X_train, y_train))
        self.test_accuracy = float(self.model.score(X_test, y_test))
        self.n_train_samples = len(y_train)

        result = {
            "train_acc": self.train_accuracy,
            "test_acc": self.test_accuracy,
            "n_train": len(y_train),
            "n_test": len(y_test),
        }
        logger.info(f"学習完了: {result}")
        return result

    # =========================================
    # 推論
    # =========================================

    def predict(self, magnitude: float, phase: float,
                sweep_features: Optional[Dict] = None) -> Tuple[int, float]:
        """
        押圧判定

        Args:
            magnitude: |Z| [Ω]
            phase: [rad]
            sweep_features: extract_sweep_features() の戻り値 dict (スイープモード時)

        Returns:
            (label, confidence)  label: 0 or 1, confidence: 押圧確率
        """
        if self.model is None or self.scaler is None:
            raise RuntimeError("モデルが未学習/未ロードです")

        feat = self._to_features(magnitude, phase, sweep_features).reshape(1, -1)
        feat_scaled = self.scaler.transform(feat)
        proba = self.model.predict_proba(feat_scaled)[0]

        # クラス1 (押圧) の確率
        press_idx = list(self.model.classes_).index(1)
        confidence = float(proba[press_idx])
        label = 1 if confidence >= 0.5 else 0

        return label, confidence

    # =========================================
    # 保存 / ロード
    # =========================================

    def save(self) -> str:
        """モデル・スケーラー・データを保存。保存先ディレクトリを返す"""
        if self.model is None or self.scaler is None:
            raise RuntimeError("保存するモデルがありません")

        model_path = os.path.join(self.model_dir, _MODEL_FILE)
        scaler_path = os.path.join(self.model_dir, _SCALER_FILE)
        data_path = os.path.join(self.model_dir, _DATA_FILE)
        meta_path = os.path.join(self.model_dir, "press_classifier_meta.pkl")

        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        with open(scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)

        # メタ情報（スイープモード等）
        meta = {"use_sweep": self.use_sweep}
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)

        # 学習データも保存しておく（追加学習用）
        if self._X_buf:
            np.savez(data_path,
                     X=np.array(self._X_buf),
                     y=np.array(self._y_buf))

        logger.info(f"モデルを保存しました: {self.model_dir} (sweep={self.use_sweep})")
        return self.model_dir

    def load(self) -> bool:
        """保存済みモデルをロード。成功で True"""
        model_path = os.path.join(self.model_dir, _MODEL_FILE)
        scaler_path = os.path.join(self.model_dir, _SCALER_FILE)
        meta_path = os.path.join(self.model_dir, "press_classifier_meta.pkl")

        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            logger.warning("保存済みモデルが見つかりません")
            return False

        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            with open(scaler_path, "rb") as f:
                self.scaler = pickle.load(f)

            # メタ情報
            if os.path.exists(meta_path):
                with open(meta_path, "rb") as f:
                    meta = pickle.load(f)
                self.use_sweep = meta.get("use_sweep", False)
            else:
                # 旧形式: 特徴量次元から推定
                self.use_sweep = (self.scaler.n_features_in_ > 2)

            logger.info(f"モデルをロードしました (sweep={self.use_sweep})")

            # 学習データもあればロード
            data_path = os.path.join(self.model_dir, _DATA_FILE)
            if os.path.exists(data_path):
                data = np.load(data_path)
                self._X_buf = list(data["X"])
                self._y_buf = list(data["y"].astype(int))
                logger.info(f"学習データもロード: {len(self._y_buf)} samples")

            return True
        except Exception as e:
            logger.error(f"モデルロード失敗: {e}")
            return False

    def is_ready(self) -> bool:
        """推論可能かどうか"""
        return self.model is not None and self.scaler is not None

    @property
    def feature_names(self) -> List[str]:
        """現在の特徴量名リスト"""
        if self.use_sweep:
            return [
                "log10(peak_freq)", "log10(peak_mag+1)", "peak_phase",
                "log10(z_low+1)", "log10(z_mid+1)", "log10(z_high+1)",
                "x_low", "x_mid", "x_high", "x_slope",
            ]
        return ["log10(mag+1)", "phase"]

    def get_info(self) -> str:
        if not self.is_ready():
            return "Model not loaded"
        n0, n1 = self.get_sample_counts()
        mode = "3D-sweep" if self.use_sweep else "2D"
        return (f"MLP({mode})  train={self.train_accuracy:.1%}  "
                f"test={self.test_accuracy:.1%}  "
                f"n=({n0}+{n1})")
