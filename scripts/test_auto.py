"""
自動テストスクリプト - HILSシステムの動作確認

既存のコードを変更せずに、ランダム位置でデータ収集・学習・推論を行い、
詳細なログを出力してシステムの動作を検証します。
"""

import os
import sys

# プロジェクトルートをPythonパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import logging
from datetime import datetime
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from src.core.factory import DataSourceFactory
from src.core.interfaces import MeasurementResult
from src.utils import config

# ログ設定
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_random_positions(n_positions: int, seed: int = 42) -> list:
    """
    ランダムな位置を生成
    
    Args:
        n_positions: 生成する位置の数
        seed: 乱数シード
    
    Returns:
        list: [(x, y), ...] の位置リスト
    """
    np.random.seed(seed)
    positions = []
    
    for i in range(n_positions):
        x = np.random.uniform(10, config.GEL_WIDTH - 10)
        y = np.random.uniform(10, config.GEL_HEIGHT - 10)
        positions.append((x, y))
    
    logger.info(f"生成した位置数: {n_positions}")
    return positions


def collect_data(data_source, positions: list, samples_per_position: int = 10) -> list:
    """
    各位置でデータを収集
    
    Args:
        data_source: データソース（HILS or 実機）
        positions: 収集する位置のリスト
        samples_per_position: 1位置あたりのサンプル数
    
    Returns:
        list: MeasurementResult のリスト
    """
    training_data = []
    
    logger.info("=" * 60)
    logger.info("データ収集開始")
    logger.info("=" * 60)
    
    for idx, (x, y) in enumerate(positions):
        logger.info(f"\n位置 {idx+1}/{len(positions)}: ({x:.2f}, {y:.2f}) mm")
        
        # 正解位置を設定
        data_source.set_ground_truth(x, y)
        
        position_impedances = []
        
        for sample_idx in range(samples_per_position):
            # インピーダンス測定
            impedance_vector = data_source.measure_impedance_vector()
            
            result = MeasurementResult(
                impedance_vector=impedance_vector,
                ground_truth=(x, y),
                timestamp=datetime.now().timestamp()
            )
            
            training_data.append(result)
            position_impedances.append(impedance_vector)
            
            # 最初のサンプルの詳細を表示
            if sample_idx == 0:
                logger.info(f"  サンプル {sample_idx+1}: インピーダンス値（Magnitude）:")
                for pair_idx, (mag, phase) in enumerate(impedance_vector):
                    pair_info = config.MEASUREMENT_PAIRS[pair_idx]
                    logger.info(f"    Pair {pair_idx} ({pair_info[0]}→{pair_info[1]}): {mag:.2f} Ω, {phase:.4f} rad")
        
        # この位置での統計情報
        position_impedances = np.array(position_impedances)
        mean_mag = position_impedances[:, :, 0].mean(axis=0)
        std_mag = position_impedances[:, :, 0].std(axis=0)
        
        logger.info(f"  平均インピーダンス: {mean_mag}")
        logger.info(f"  標準偏差: {std_mag}")
    
    logger.info(f"\n合計収集データ数: {len(training_data)}")
    return training_data


def train_model(training_data: list):
    """
    モデルを学習
    
    Args:
        training_data: 学習データ
    
    Returns:
        tuple: (model, scaler)
    """
    logger.info("\n" + "=" * 60)
    logger.info("モデル学習開始")
    logger.info("=" * 60)
    
    # 特徴量とラベルを抽出
    X = np.array([result.to_feature_vector() for result in training_data])
    y = np.array([result.ground_truth for result in training_data])
    
    logger.info(f"特徴量の形状: {X.shape}")
    logger.info(f"ラベルの形状: {y.shape}")
    logger.info(f"特徴量の範囲: min={X.min():.4f}, max={X.max():.4f}")
    
    # 正規化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    logger.info(f"正規化後の範囲: min={X_scaled.min():.4f}, max={X_scaled.max():.4f}")
    
    # モデル学習
    model = MLPRegressor(
        hidden_layer_sizes=config.HIDDEN_LAYER_SIZES,
        max_iter=config.MAX_ITERATIONS,
        random_state=config.RANDOM_STATE,
        verbose=True
    )
    
    logger.info(f"ニューラルネットワーク構造: 入力={X.shape[1]} → {config.HIDDEN_LAYER_SIZES} → 出力=2")
    
    model.fit(X_scaled, y)
    
    logger.info(f"学習完了: 反復回数={model.n_iter_}")
    logger.info(f"最終損失: {model.loss_:.6f}")
    
    return model, scaler


def test_inference(data_source, model, scaler, test_positions: list):
    """
    推論テスト
    
    Args:
        data_source: データソース
        model: 学習済みモデル
        scaler: スケーラー
        test_positions: テストする位置のリスト
    """
    logger.info("\n" + "=" * 60)
    logger.info("推論テスト開始")
    logger.info("=" * 60)
    
    errors = []
    
    for idx, (true_x, true_y) in enumerate(test_positions):
        logger.info(f"\nテスト {idx+1}/{len(test_positions)}")
        logger.info(f"正解位置: ({true_x:.2f}, {true_y:.2f}) mm")
        
        # 正解位置を設定してインピーダンス測定
        data_source.set_ground_truth(true_x, true_y)
        impedance_vector = data_source.measure_impedance_vector()
        
        result = MeasurementResult(impedance_vector=impedance_vector)
        
        # 特徴量抽出と正規化
        X = result.to_feature_vector().reshape(1, -1)
        X_scaled = scaler.transform(X)
        
        # 推論
        prediction = model.predict(X_scaled)[0]
        pred_x, pred_y = prediction
        
        # 誤差計算
        error = np.sqrt((pred_x - true_x)**2 + (pred_y - true_y)**2)
        errors.append(error)
        
        logger.info(f"推定位置: ({pred_x:.2f}, {pred_y:.2f}) mm")
        logger.info(f"誤差: {error:.2f} mm")
        logger.info(f"インピーダンス（最初の3ペア）: {impedance_vector[:3, 0]}")
    
    # 統計情報
    logger.info("\n" + "=" * 60)
    logger.info("推論結果サマリー")
    logger.info("=" * 60)
    logger.info(f"平均誤差: {np.mean(errors):.2f} mm")
    logger.info(f"中央値誤差: {np.median(errors):.2f} mm")
    logger.info(f"最大誤差: {np.max(errors):.2f} mm")
    logger.info(f"最小誤差: {np.min(errors):.2f} mm")
    logger.info(f"標準偏差: {np.std(errors):.2f} mm")


def main():
    """メイン関数"""
    logger.info("=" * 60)
    logger.info("HILS自動テストスクリプト")
    logger.info("=" * 60)
    logger.info(f"モード: {DataSourceFactory.get_mode_name()}")
    logger.info(f"ノイズレベル: {config.NOISE_LEVEL * 100:.1f}%")
    logger.info(f"ニューラルネットワーク: {config.HIDDEN_LAYER_SIZES}")
    
    # データソース接続
    data_source = DataSourceFactory.create()
    if not data_source.connect():
        logger.error("データソースへの接続に失敗しました")
        return
    
    logger.info(f"接続成功: {data_source.get_device_info()}")
    
    try:
        # 1. 学習用の位置を生成（3x3グリッド + ランダム）
        training_positions = []
        
        # グリッド位置（3x3）
        for i in range(3):
            for j in range(3):
                x = 20 + i * 30
                y = 20 + j * 30
                training_positions.append((x, y))
        
        # ランダム位置を追加
        random_positions = generate_random_positions(n_positions=6, seed=42)
        training_positions.extend(random_positions)
        
        logger.info(f"\n学習用位置数: {len(training_positions)}")
        
        # 2. データ収集
        training_data = collect_data(
            data_source, 
            training_positions, 
            samples_per_position=10
        )
        
        # 3. モデル学習
        model, scaler = train_model(training_data)
        
        # 4. テスト用の位置を生成
        test_positions = generate_random_positions(n_positions=10, seed=123)
        
        # 5. 推論テスト
        test_inference(data_source, model, scaler, test_positions)
        
    finally:
        data_source.disconnect()
        logger.info("\nテスト完了")


if __name__ == "__main__":
    main()
