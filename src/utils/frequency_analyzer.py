"""
周波数分析ツール - Frequency Analyzer

イオンゲルのインピーダンス特性の周波数依存性を分析し、
タッチ位置判別に最適な測定周波数を特定します。

Usage:
    python frequency_analyzer.py --mode hils    # HILSモード
    python frequency_analyzer.py --mode real    # 実機モード
"""

import argparse
import numpy as np
import json
import logging
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from src.utils import config
from src.core.factory import DataSourceFactory
from src.core.models.classifier import TouchClassifier

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FrequencyAnalyzer:
    """
    周波数分析ツール
    
    様々な周波数でインピーダンスを測定し、クラス分離性能を評価します。
    """
    
    def __init__(self, data_source, classifier: TouchClassifier = None):
        """
        初期化
        
        Args:
            data_source: IDataSource インターフェースを実装したデータソース
            classifier: TouchClassifier インスタンス（グリッド位置取得用）
        """
        self.data_source = data_source
        self.classifier = classifier
        self.results = {}
        
    def generate_frequency_list(self, 
                                min_freq: float = 100.0,
                                max_freq: float = 100000.0,
                                num_points: int = 20) -> List[float]:
        """
        対数スケールで周波数リストを生成
        
        Args:
            min_freq: 最小周波数 [Hz]
            max_freq: 最大周波数 [Hz]
            num_points: サンプル点数
            
        Returns:
            周波数のリスト
        """
        return np.logspace(np.log10(min_freq), np.log10(max_freq), num_points).tolist()
    
    def collect_data_at_frequency(self,
                                  frequency: float,
                                  grid_positions: List[Tuple[float, float]],
                                  samples_per_position: int = 10) -> Dict:
        """
        指定周波数でデータを収集
        
        Args:
            frequency: 測定周波数 [Hz]
            grid_positions: グリッド位置のリスト [(x, y), ...]
            samples_per_position: 1位置あたりのサンプル数
            
        Returns:
            収集データの辞書 {
                'frequency': float,
                'data': List[np.ndarray],  # 各位置でのインピーダンスベクトル
                'labels': List[int]        # 位置のラベル
            }
        """
        logger.info(f"Collecting data at {frequency:.1f} Hz...")
        
        # TODO: 実機モードの場合、ここでAD3の周波数設定を変更する必要がある
        # 現状はconfig.MEASUREMENT_FREQUENCYが使用される
        
        all_data = []
        all_labels = []
        
        for pos_idx, (x, y) in enumerate(grid_positions):
            logger.info(f"  Position {pos_idx}: ({x:.1f}, {y:.1f})")
            
            # 正解位置を設定（HILSモードの場合）
            if hasattr(self.data_source, 'set_ground_truth'):
                self.data_source.set_ground_truth(x, y)
            
            # 複数回測定
            for sample in range(samples_per_position):
                impedance_vector = self.data_source.measure_impedance_vector()
                all_data.append(impedance_vector)
                all_labels.append(pos_idx)
        
        return {
            'frequency': frequency,
            'data': all_data,
            'labels': all_labels
        }
    
    def evaluate_separability(self, data: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """
        クラス分離性能を評価
        
        Args:
            data: データ行列 (n_samples, n_features)
            labels: ラベル配列 (n_samples,)
            
        Returns:
            評価メトリクスの辞書
        """
        n_classes = len(np.unique(labels))
        
        # データを平坦化（複素数の場合は実部と虚部を分離）
        if data.dtype == complex:
            data_real = np.column_stack([data.real, data.imag])
        else:
            # 既に (n_samples, n_pairs, 2) の形式の場合
            if len(data.shape) == 3:
                data_real = data.reshape(data.shape[0], -1)
            else:
                data_real = data
        
        metrics = {}
        
        # 1. Fisher's discriminant ratio (simplified)
        # クラス間分散 / クラス内分散
        try:
            within_class_var = 0
            between_class_var = 0
            
            overall_mean = np.mean(data_real, axis=0)
            
            for class_id in np.unique(labels):
                class_data = data_real[labels == class_id]
                class_mean = np.mean(class_data, axis=0)
                n_samples = len(class_data)
                
                # クラス内分散
                within_class_var += np.sum(np.var(class_data, axis=0))
                
                # クラス間分散
                between_class_var += n_samples * np.sum((class_mean - overall_mean) ** 2)
            
            fisher_ratio = between_class_var / (within_class_var + 1e-10)
            metrics['fisher_ratio'] = float(fisher_ratio)
        except Exception as e:
            logger.warning(f"Fisher ratio calculation failed: {e}")
            metrics['fisher_ratio'] = 0.0
        
        # 2. Silhouette Score (クラスタリング品質)
        try:
            if len(np.unique(labels)) > 1:
                silhouette = silhouette_score(data_real, labels)
                metrics['silhouette_score'] = float(silhouette)
            else:
                metrics['silhouette_score'] = 0.0
        except Exception as e:
            logger.warning(f"Silhouette score calculation failed: {e}")
            metrics['silhouette_score'] = 0.0
        
        # 3. PCAでの分離度（第1主成分での分散）
        try:
            if data_real.shape[1] >= 2:
                pca = PCA(n_components=min(2, data_real.shape[1]))
                pca_data = pca.fit_transform(data_real)
                
                # 第1主成分での分離度
                pc1_separation = np.var(pca_data[:, 0])
                metrics['pca_separation'] = float(pc1_separation)
                metrics['pca_variance_ratio'] = float(pca.explained_variance_ratio_[0])
            else:
                metrics['pca_separation'] = 0.0
                metrics['pca_variance_ratio'] = 0.0
        except Exception as e:
            logger.warning(f"PCA analysis failed: {e}")
            metrics['pca_separation'] = 0.0
            metrics['pca_variance_ratio'] = 0.0
        
        return metrics
    
    def run_frequency_sweep(self,
                           frequencies: List[float] = None,
                           grid_size: Tuple[int, int] = (3, 3),
                           samples_per_position: int = 5) -> Dict:
        """
        周波数スイープを実行
        
        Args:
            frequencies: 測定する周波数のリスト（Noneの場合は自動生成）
            grid_size: グリッドサイズ (rows, cols)
            samples_per_position: 1位置あたりのサンプル数
            
        Returns:
            分析結果の辞書
        """
        if frequencies is None:
            frequencies = self.generate_frequency_list()
        
        # グリッド位置を生成
        if self.classifier:
            grid_positions = [self.classifier.get_grid_position(i) 
                            for i in range(grid_size[0] * grid_size[1])]
        else:
            # デフォルトの3x3グリッド
            grid_positions = []
            for row in range(grid_size[0]):
                for col in range(grid_size[1]):
                    x = col * 50.0
                    y = row * 50.0
                    grid_positions.append((x, y))
        
        all_results = {
            'frequencies': [],
            'metrics': [],
            'optimal_frequency': None,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        for freq in frequencies:
            # データ収集
            data_dict = self.collect_data_at_frequency(
                freq, grid_positions, samples_per_position
            )
            
            # numpy配列に変換
            data_array = np.array(data_dict['data'])
            labels_array = np.array(data_dict['labels'])
            
            # 分離性能を評価
            metrics = self.evaluate_separability(data_array, labels_array)
            
            all_results['frequencies'].append(freq)
            all_results['metrics'].append(metrics)
            
            logger.info(f"  Fisher ratio: {metrics.get('fisher_ratio', 0):.3f}, "
                       f"Silhouette: {metrics.get('silhouette_score', 0):.3f}")
        
        # 最適周波数を選択（Fisher ratioが最大）
        fisher_ratios = [m.get('fisher_ratio', 0) for m in all_results['metrics']]
        best_idx = np.argmax(fisher_ratios)
        all_results['optimal_frequency'] = frequencies[best_idx]
        
        logger.info(f"\nOptimal frequency: {all_results['optimal_frequency']:.1f} Hz")
        
        self.results = all_results
        return all_results
    
    def save_results(self, filename: str = "frequency_config.json"):
        """
        分析結果を設定ファイルとして保存
        
        Args:
            filename: 保存ファイル名
        """
        if not self.results:
            logger.warning("No results to save")
            return
        
        # 推奨周波数リスト（上位3つ）
        fisher_ratios = [m.get('fisher_ratio', 0) for m in self.results['metrics']]
        top_indices = np.argsort(fisher_ratios)[-3:][::-1]
        recommended_freqs = [self.results['frequencies'][i] for i in top_indices]
        
        config_data = {
            "optimal_frequency": self.results['optimal_frequency'],
            "frequency_range": [
                min(self.results['frequencies']),
                max(self.results['frequencies'])
            ],
            "analysis_results": {
                "frequencies_tested": self.results['frequencies'],
                "fisher_ratios": [m.get('fisher_ratio', 0) for m in self.results['metrics']],
                "silhouette_scores": [m.get('silhouette_score', 0) for m in self.results['metrics']],
                "recommended_frequencies": recommended_freqs
            },
            "measurement_params": {
                "amplitude": config.MEASUREMENT_AMPLITUDE,
                "samples_per_position": 5
            },
            "last_updated": self.results['analysis_timestamp']
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
    
    def plot_results(self):
        """
        分析結果をプロット
        """
        if not self.results:
            logger.warning("No results to plot")
            return
        
        frequencies = self.results['frequencies']
        fisher_ratios = [m.get('fisher_ratio', 0) for m in self.results['metrics']]
        silhouette_scores = [m.get('silhouette_score', 0) for m in self.results['metrics']]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Fisher ratio
        ax1.semilogx(frequencies, fisher_ratios, 'bo-', linewidth=2, markersize=8)
        ax1.axvline(self.results['optimal_frequency'], color='r', linestyle='--', 
                   label=f"Optimal: {self.results['optimal_frequency']:.1f} Hz")
        ax1.set_xlabel('Frequency [Hz]')
        ax1.set_ylabel('Fisher Ratio')
        ax1.set_title('Class Separability vs Frequency')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Silhouette score
        ax2.semilogx(frequencies, silhouette_scores, 'go-', linewidth=2, markersize=8)
        ax2.axvline(self.results['optimal_frequency'], color='r', linestyle='--',
                   label=f"Optimal: {self.results['optimal_frequency']:.1f} Hz")
        ax2.set_xlabel('Frequency [Hz]')
        ax2.set_ylabel('Silhouette Score')
        ax2.set_title('Clustering Quality vs Frequency')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig('frequency_analysis_results.png', dpi=150, bbox_inches='tight')
        logger.info("Plot saved to frequency_analysis_results.png")
        plt.show()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Frequency Analysis Tool')
    parser.add_argument('--mode', type=str, choices=['hils', 'real'], default='hils',
                       help='Data source mode (hils or real)')
    parser.add_argument('--min-freq', type=float, default=100.0,
                       help='Minimum frequency [Hz]')
    parser.add_argument('--max-freq', type=float, default=100000.0,
                       help='Maximum frequency [Hz]')
    parser.add_argument('--num-points', type=int, default=15,
                       help='Number of frequency points')
    parser.add_argument('--samples', type=int, default=5,
                       help='Samples per position')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Frequency Analysis Tool")
    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info(f"Frequency range: {args.min_freq:.1f} - {args.max_freq:.1f} Hz")
    logger.info(f"Number of points: {args.num_points}")
    logger.info("=" * 60)
    
    # データソースを作成
    use_real = (args.mode == 'real')
    data_source = DataSourceFactory.create_data_source(use_real_hardware=use_real)
    
    if not data_source.connect():
        logger.error("Failed to connect to data source")
        return 1
    
    # 分類器をロード（グリッド位置取得用）
    try:
        classifier = TouchClassifier()
        classifier.load_model()
    except:
        logger.warning("Could not load classifier, using default grid")
        classifier = None
    
    # 周波数分析を実行
    analyzer = FrequencyAnalyzer(data_source, classifier)
    
    frequencies = analyzer.generate_frequency_list(
        args.min_freq, args.max_freq, args.num_points
    )
    
    results = analyzer.run_frequency_sweep(
        frequencies=frequencies,
        samples_per_position=args.samples
    )
    
    # 結果を保存
    analyzer.save_results()
    
    # プロット表示
    analyzer.plot_results()
    
    # クリーンアップ
    data_source.disconnect()
    
    logger.info("Analysis complete!")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
