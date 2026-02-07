"""
学習スクリプト - 9点分類モデルの学習

3x3グリッド（9点）でデータを収集し、分類モデルを学習します。
学習したモデルは models/ ディレクトリに保存されます。
"""

import numpy as np
import pickle
import json
import os
import argparse
import logging
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from factory import DataSourceFactory
from interfaces import MeasurementResult
import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def define_grid_positions(grid_size: int = 3) -> list:
    """
    グリッド位置を定義
    
    Args:
        grid_size: グリッドのサイズ（3 = 3x3）
    
    Returns:
        list: [(x, y), ...] の位置リスト（9点）
    """
    positions = []
    step_x = config.GEL_WIDTH / (grid_size + 1)
    step_y = config.GEL_HEIGHT / (grid_size + 1)
    
    for row in range(grid_size):
        for col in range(grid_size):
            x = step_x * (col + 1)
            y = step_y * (row + 1)
            positions.append((x, y))
    
    logger.info(f"グリッド位置を定義: {grid_size}x{grid_size} = {len(positions)}点")
    for idx, (x, y) in enumerate(positions):
        logger.info(f"  点{idx}: ({x:.2f}, {y:.2f}) mm")
    
    return positions


def collect_training_data(data_source, grid_positions: list, samples_per_point: int) -> tuple:
    """
    各グリッド点でデータを収集
    
    Args:
        data_source: データソース
        grid_positions: グリッド位置のリスト
        samples_per_point: 1点あたりのサンプル数
    
    Returns:
        tuple: (X, y) - 特徴量とラベル
    """
    X_list = []
    y_list = []
    
    logger.info("=" * 60)
    logger.info("データ収集開始")
    logger.info("=" * 60)
    
    for class_id, (x, y) in enumerate(grid_positions):
        logger.info(f"\nクラス {class_id} - 位置: ({x:.2f}, {y:.2f}) mm")
        
        # 正解位置を設定
        data_source.set_ground_truth(x, y)
        
        for sample_idx in range(samples_per_point):
            # インピーダンス測定
            impedance_vector = data_source.measure_impedance_vector()
            
            result = MeasurementResult(
                impedance_vector=impedance_vector,
                ground_truth=(x, y),
                timestamp=datetime.now().timestamp()
            )
            
            # 特徴量を抽出
            features = result.to_feature_vector()
            
            X_list.append(features)
            y_list.append(class_id)
            
            if (sample_idx + 1) % 10 == 0:
                logger.info(f"  進捗: {sample_idx + 1}/{samples_per_point}")
        
        logger.info(f"  完了: {samples_per_point}サンプル収集")
    
    X = np.array(X_list)
    y = np.array(y_list)
    
    logger.info(f"\n合計データ数: {len(X)}")
    logger.info(f"特徴量の形状: {X.shape}")
    logger.info(f"ラベルの形状: {y.shape}")
    
    return X, y


def train_classifier(X, y, test_size: float = 0.2):
    """
    分類モデルを学習
    
    Args:
        X: 特徴量
        y: ラベル
        test_size: テストデータの割合
    
    Returns:
        tuple: (model, scaler, accuracy)
    """
    logger.info("\n" + "=" * 60)
    logger.info("モデル学習開始")
    logger.info("=" * 60)
    
    # 訓練/テスト分割
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=config.RANDOM_STATE, stratify=y
    )
    
    logger.info(f"訓練データ: {len(X_train)}サンプル")
    logger.info(f"テストデータ: {len(X_test)}サンプル")
    
    # 正規化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # モデル学習
    model = MLPClassifier(
        hidden_layer_sizes=config.HIDDEN_LAYER_SIZES,
        max_iter=config.MAX_ITERATIONS,
        random_state=config.RANDOM_STATE,
        verbose=True
    )
    
    logger.info(f"ニューラルネットワーク構造: 入力={X.shape[1]} → {config.HIDDEN_LAYER_SIZES} → 出力=9")
    
    model.fit(X_train_scaled, y_train)
    
    # 精度評価
    train_accuracy = model.score(X_train_scaled, y_train)
    test_accuracy = model.score(X_test_scaled, y_test)
    
    logger.info(f"\n学習完了:")
    logger.info(f"  訓練精度: {train_accuracy * 100:.2f}%")
    logger.info(f"  テスト精度: {test_accuracy * 100:.2f}%")
    logger.info(f"  反復回数: {model.n_iter_}")
    
    return model, scaler, test_accuracy


def save_model(model, scaler, grid_positions, output_dir: str = "models"):
    """
    モデルとスケーラーを保存
    
    Args:
        model: 学習済みモデル
        scaler: スケーラー
        grid_positions: グリッド位置
        output_dir: 出力ディレクトリ
    """
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = os.path.join(output_dir, "classifier_model.pkl")
    scaler_path = os.path.join(output_dir, "classifier_scaler.pkl")
    grid_path = os.path.join(output_dir, "grid_positions.json")
    
    # モデル保存
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    logger.info(f"モデルを保存: {model_path}")
    
    # スケーラー保存
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    logger.info(f"スケーラーを保存: {scaler_path}")
    
    # グリッド位置保存
    with open(grid_path, 'w') as f:
        json.dump(grid_positions, f, indent=2)
    logger.info(f"グリッド位置を保存: {grid_path}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='9点分類モデルの学習')
    parser.add_argument('--samples', type=int, default=30, help='1点あたりのサンプル数')
    parser.add_argument('--grid-size', type=int, default=3, help='グリッドサイズ（デフォルト: 3x3）')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("9点分類モデル学習スクリプト")
    logger.info("=" * 60)
    logger.info(f"モード: {DataSourceFactory.get_mode_name()}")
    logger.info(f"グリッドサイズ: {args.grid_size}x{args.grid_size}")
    logger.info(f"1点あたりのサンプル数: {args.samples}")
    
    # データソース接続
    data_source = DataSourceFactory.create()
    if not data_source.connect():
        logger.error("データソースへの接続に失敗しました")
        return
    
    logger.info(f"接続成功: {data_source.get_device_info()}")
    
    try:
        # 1. グリッド位置を定義
        grid_positions = define_grid_positions(grid_size=args.grid_size)
        
        # 2. データ収集
        X, y = collect_training_data(data_source, grid_positions, args.samples)
        
        # 3. モデル学習
        model, scaler, accuracy = train_classifier(X, y)
        
        # 4. モデル保存
        save_model(model, scaler, grid_positions)
        
        logger.info("\n" + "=" * 60)
        logger.info("学習完了")
        logger.info(f"テスト精度: {accuracy * 100:.2f}%")
        logger.info("=" * 60)
        
    finally:
        data_source.disconnect()


if __name__ == "__main__":
    main()
