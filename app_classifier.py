"""
分類GUI - 9点確率ヒートマップ表示

リアルタイムでインピーダンスを測定し、9点のどこがタッチされているかの
確率をヒートマップで表示します。
"""

import customtkinter as ctk
import numpy as np
import logging
from typing import Optional, Tuple
import colorsys

from factory import DataSourceFactory
from interfaces import IDataSource
from model_classifier import TouchClassifier
import config

# ログ設定
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# customtkinter設定
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GridCell(ctk.CTkFrame):
    """
    グリッドセル - 1つの分類点を表示
    """
    
    def __init__(self, master, class_id: int, position: tuple, callback=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.class_id = class_id
        self.position = position
        self.probability = 0.0
        self.callback = callback
        
        # クリックイベントをバインド
        self.bind("<Button-1>", self._on_click)
        
        # ラベル（クラスID）
        self.id_label = ctk.CTkLabel(
            self,
            text=f"点{class_id}",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.id_label.pack(pady=(10, 5))
        self.id_label.bind("<Button-1>", self._on_click)  # ラベル上でも反応するように
        
        # 位置表示
        self.pos_label = ctk.CTkLabel(
            self,
            text=f"({position[0]:.0f}, {position[1]:.0f})",
            font=ctk.CTkFont(size=10)
        )
        self.pos_label.pack(pady=2)
        self.pos_label.bind("<Button-1>", self._on_click)
        
        # 確率表示
        self.prob_label = ctk.CTkLabel(
            self,
            text="0%",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.prob_label.pack(pady=10)
        self.prob_label.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event):
        """クリック時のハンドラ"""
        if self.callback:
            self.callback(self.class_id)
    
    def update_probability(self, probability: float, is_max: bool = False, is_ground_truth: bool = False):
        """
        確率を更新して色を変更
        
        Args:
            probability: 確率 (0.0-1.0)
            is_max: 最大確率かどうか
            is_ground_truth: 正解位置かどうか（HILS用）
        """
        self.probability = probability
        
        # テキスト更新
        self.prob_label.configure(text=f"{probability * 100:.1f}%")
        
        # 色を計算
        if is_ground_truth and is_max:
            # 正解かつ最大確率 = 正解！（緑）
            bg_color = "#00CC00"
            text_color = "#FFFFFF"
            border_color = "#00FF00"
            border_width = 3
        elif is_ground_truth and not is_max:
            # 正解だが最大確率ではない = 誤判定（赤）
            bg_color = self._probability_to_color(probability)
            text_color = "#FFFFFF" if probability < 0.5 else "#000000"
            border_color = "#FF0000"
            border_width = 3
        elif is_max:
            # 最大確率（正解位置は不明）
            bg_color = "#00AA00"
            text_color = "#FFFFFF"
            border_color = "#00FF00"
            border_width = 2
        else:
            # 通常のヒートマップカラー
            bg_color = self._probability_to_color(probability)
            text_color = "#FFFFFF" if probability < 0.5 else "#000000"
            border_color = None
            border_width = 2
        
        self.configure(fg_color=bg_color, border_width=border_width)
        if border_color:
            self.configure(border_color=border_color)
        self.prob_label.configure(text_color=text_color)
    
    def _probability_to_color(self, prob: float) -> str:
        """
        確率を色に変換（青 → 黄 → 赤）
        
        Args:
            prob: 確率 (0.0-1.0)
        
        Returns:
            str: 16進数カラーコード
        """
        # HSVカラースペースを使用
        # Hue: 240 (青) → 60 (黄) → 0 (赤)
        hue = (1.0 - prob) * 240 / 360  # 0-1の範囲に正規化
        saturation = 0.8
        value = 0.3 + prob * 0.5  # 暗すぎないように調整
        
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


class ClassifierApp(ctk.CTk):
    """
    分類アプリケーション
    
    9点の確率をリアルタイムで表示します。
    """
    
    def __init__(self):
        super().__init__()
        
        # ウィンドウ設定
        self.title("Ion Gel Touch Classifier - 9-Point Probability")
        self.geometry("900x700")
        
        # データソース
        self.data_source: Optional[IDataSource] = None
        
        # 分類器
        self.classifier: Optional[TouchClassifier] = None
        
        # 監視状態
        self.monitoring = False
        self.update_interval = 500  # ms
        
        # 精度メトリクス（HILS用）
        self.total_samples = 0
        self.correct_predictions = 0
        self.error_distances = []  # 誤差距離のリスト [mm]
        
        # UI構築
        self._create_widgets()
        
        # データソース接続
        self._connect_data_source()
        
        # 分類器ロード
        self._load_classifier()
        
        logger.info("分類アプリケーションを起動しました")
    
    def _create_widgets(self):
        """UIウィジェットを作成"""
        
        # グリッドレイアウト設定
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ========================================
        # 左サイドバー
        # ========================================
        
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # タイトル
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="Touch\nClassifier",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # モード表示
        mode_name = DataSourceFactory.get_mode_name()
        self.mode_label = ctk.CTkLabel(
            self.sidebar,
            text=f"Mode: {mode_name}",
            font=ctk.CTkFont(size=12)
        )
        self.mode_label.grid(row=1, column=0, padx=20, pady=10)
        
        # 接続状態
        self.connection_label = ctk.CTkLabel(
            self.sidebar,
            text="Status: Disconnected",
            font=ctk.CTkFont(size=12),
            text_color="red"
        )
        self.connection_label.grid(row=2, column=0, padx=20, pady=10)
        
        # セパレータ
        ctk.CTkLabel(self.sidebar, text="").grid(row=3, column=0, pady=5)
        
        # 監視開始ボタン
        self.start_btn = ctk.CTkButton(
            self.sidebar,
            text="Start Monitoring",
            command=self._start_monitoring,
            fg_color="green"
        )
        self.start_btn.grid(row=4, column=0, padx=20, pady=10)
        
        # 停止ボタン
        self.stop_btn = ctk.CTkButton(
            self.sidebar,
            text="Stop",
            command=self._stop_monitoring,
            fg_color="red",
            state="disabled"
        )
        self.stop_btn.grid(row=5, column=0, padx=20, pady=10)
        
        # 更新間隔設定
        ctk.CTkLabel(
            self.sidebar,
            text="Update Interval (ms)",
            font=ctk.CTkFont(size=12)
        ).grid(row=6, column=0, padx=20, pady=(20, 5))
        
        self.interval_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="500"
        )
        self.interval_entry.insert(0, "500")
        self.interval_entry.grid(row=7, column=0, padx=20, pady=5)
        
        # ========================================
        # メインエリア: 3x3グリッド
        # ========================================
        
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # グリッドを中央に配置
        for i in range(3):
            self.main_frame.grid_rowconfigure(i, weight=1)
            self.main_frame.grid_columnconfigure(i, weight=1)
        
        # グリッドセルを作成
        self.grid_cells = []
        
        # ========================================
        # ステータスバー
        # ========================================
        
        self.status_bar = ctk.CTkFrame(self, height=40)
        self.status_bar.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10)
        
        # ========================================
        # 精度メトリクスパネル（右側）
        # ========================================
        
        self.metrics_panel = ctk.CTkFrame(self, width=250)
        self.metrics_panel.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        
        # タイトル
        ctk.CTkLabel(
            self.metrics_panel,
            text="Accuracy Metrics",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(20, 10))
        
        # メトリクス表示
        self.accuracy_label = ctk.CTkLabel(
            self.metrics_panel,
            text="Accuracy: N/A",
            font=ctk.CTkFont(size=14)
        )
        self.accuracy_label.pack(pady=5)
        
        self.avg_error_label = ctk.CTkLabel(
            self.metrics_panel,
            text="Avg Error: N/A",
            font=ctk.CTkFont(size=14)
        )
        self.avg_error_label.pack(pady=5)
        
        self.max_error_label = ctk.CTkLabel(
            self.metrics_panel,
            text="Max Error: N/A",
            font=ctk.CTkFont(size=14)
        )
        self.max_error_label.pack(pady=5)
        
        self.min_error_label = ctk.CTkLabel(
            self.metrics_panel,
            text="Min Error: N/A",
            font=ctk.CTkFont(size=14)
        )
        self.min_error_label.pack(pady=5)
        
        self.samples_label = ctk.CTkLabel(
            self.metrics_panel,
            text="Samples: 0",
            font=ctk.CTkFont(size=14)
        )
        self.samples_label.pack(pady=5)
        
        # リセットボタン
        ctk.CTkButton(
            self.metrics_panel,
            text="Reset Statistics",
            command=self._reset_metrics,
            fg_color="orange"
        ).pack(pady=20)
    
    def _connect_data_source(self):
        """データソースに接続"""
        try:
            self.data_source = DataSourceFactory.create()
            
            if self.data_source.connect():
                self.connection_label.configure(
                    text="Status: Connected",
                    text_color="green"
                )
                self._update_status(f"Connected to {self.data_source.get_device_info()}")
            else:
                self.connection_label.configure(
                    text="Status: Connection Failed",
                    text_color="red"
                )
                self._update_status("Connection failed")
        
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            self._update_status(f"Error: {e}")
    
    def _load_classifier(self):
        """分類器をロード"""
        try:
            self.classifier = TouchClassifier()
            self._update_status(f"Classifier loaded: {self.classifier.get_model_info()}")
            
            # グリッド位置を取得してセルを作成
            grid_positions = self.classifier.get_grid_positions()
            
            for class_id, position in enumerate(grid_positions):
                row = class_id // 3
                col = class_id % 3
                
                cell = GridCell(
                    self.main_frame,
                    class_id=class_id,
                    position=position,
                    callback=self._on_cell_click,  # コールバックを追加
                    corner_radius=10,
                    border_width=2
                )
                cell.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                
                self.grid_cells.append(cell)
            
            logger.info(f"グリッドセルを作成: {len(self.grid_cells)}個")
            
        except Exception as e:
            logger.error(f"分類器のロードに失敗: {e}")
            self._update_status(f"Classifier load failed: {e}")

    def _on_cell_click(self, class_id: int):
        """
        グリッドセルクリック時の処理
        
        HILSモードの場合のみ、クリックした位置をタッチ位置として設定します。
        """
        if config.USE_REAL_HARDWARE:
            return  # 実機モードでは何もしない
            
        if not self.data_source or not self.data_source.is_connected():
            return

        if not self.classifier:
            return

        try:
            # クリックされたセルの位置を取得
            position = self.classifier.get_grid_position(class_id)
            x, y = position
            
            # HILSに正解位置を設定
            self.data_source.set_ground_truth(x, y)
            
            self._update_status(f"HILS: Touch simulated at Point {class_id} ({x:.0f}, {y:.0f})")
            
            # 視覚的なフィードバック（一時的に枠色を変えるなど）
            # ここでは特になし（次の更新でヒートマップが変わるため）
            
        except Exception as e:
            logger.error(f"HILS操作エラー: {e}")
    
    def _start_monitoring(self):
        """監視を開始"""
        if not self.data_source or not self.data_source.is_connected():
            self._update_status("Error: Not connected to data source")
            return
        
        if not self.classifier or not self.classifier.is_loaded():
            self._update_status("Error: Classifier not loaded")
            return
        
        try:
            self.update_interval = int(self.interval_entry.get())
        except ValueError:
            self._update_status("Error: Invalid interval value")
            return
        
        self.monitoring = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        self._update_status("Monitoring started")
        self._monitoring_loop()
    
    def _stop_monitoring(self):
        """監視を停止"""
        self.monitoring = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        self._update_status("Monitoring stopped")
    
    def _monitoring_loop(self):
        """監視ループ"""
        if not self.monitoring:
            return
        
        try:
            # インピーダンス測定
            impedance_vector = self.data_source.measure_impedance_vector()
            
            # 確率予測
            probabilities = self.classifier.predict_probabilities(impedance_vector)
            
            # 最大確率のクラスを取得
            max_class = int(np.argmax(probabilities))
            
            # HILSモードの場合、正解位置を取得して精度を評価
            ground_truth = None
            ground_truth_class = None
            
            if self.data_source:
                ground_truth = self.data_source.get_ground_truth()
                
                if ground_truth is not None:
                    # 正解位置に最も近いグリッド点を見つける
                    gt_x, gt_y = ground_truth
                    min_dist = float('inf')
                    
                    for class_id, cell in enumerate(self.grid_cells):
                        cell_x, cell_y = cell.position
                        dist = np.sqrt((gt_x - cell_x)**2 + (gt_y - cell_y)**2)
                        if dist < min_dist:
                            min_dist = dist
                            ground_truth_class = class_id
                    
                    # 精度メトリクスを更新
                    self._update_metrics(max_class, ground_truth_class, probabilities[max_class])
            
            # グリッドセルを更新
            for cell in self.grid_cells:
                is_max = (cell.class_id == max_class)
                is_gt = (ground_truth_class is not None and cell.class_id == ground_truth_class)
                cell.update_probability(probabilities[cell.class_id], is_max, is_gt)
            
            # ステータス更新
            max_prob = probabilities[max_class]
            status_msg = f"Predicted: Point {max_class} ({max_prob * 100:.1f}%)"
            if ground_truth_class is not None:
                result = "✓" if max_class == ground_truth_class else "✗"
                status_msg += f" | Ground Truth: Point {ground_truth_class} {result}"
            self._update_status(status_msg)
            
        except Exception as e:
            logger.error(f"監視エラー: {e}")
            self._update_status(f"Error: {e}")
        
        # 次の更新をスケジュール
        self.after(self.update_interval, self._monitoring_loop)
    
    def _update_metrics(self, predicted_class: int, ground_truth_class: int, confidence: float):
        """精度メトリクスを更新"""
        self.total_samples += 1
        
        # 正解/不正解をカウント
        if predicted_class == ground_truth_class:
            self.correct_predictions += 1
        
        # 誤差距離を計算
        pred_pos = self.grid_cells[predicted_class].position
        gt_pos = self.grid_cells[ground_truth_class].position
        error_dist = np.sqrt((pred_pos[0] - gt_pos[0])**2 + (pred_pos[1] - gt_pos[1])**2)
        self.error_distances.append(error_dist)
        
        # 表示を更新
        accuracy = (self.correct_predictions / self.total_samples) * 100
        avg_error = np.mean(self.error_distances)
        max_error = np.max(self.error_distances)
        min_error = np.min(self.error_distances)
        
        self.accuracy_label.configure(text=f"Accuracy: {accuracy:.1f}%")
        self.avg_error_label.configure(text=f"Avg Error: {avg_error:.2f} mm")
        self.max_error_label.configure(text=f"Max Error: {max_error:.2f} mm")
        self.min_error_label.configure(text=f"Min Error: {min_error:.2f} mm")
        self.samples_label.configure(text=f"Samples: {self.total_samples}")
    
    def _reset_metrics(self):
        """精度メトリクスをリセット"""
        self.total_samples = 0
        self.correct_predictions = 0
        self.error_distances = []
        
        self.accuracy_label.configure(text="Accuracy: N/A")
        self.avg_error_label.configure(text="Avg Error: N/A")
        self.max_error_label.configure(text="Max Error: N/A")
        self.min_error_label.configure(text="Min Error: N/A")
        self.samples_label.configure(text="Samples: 0")
        
        self._update_status("Statistics reset")
    
    def _update_status(self, message: str):
        """ステータスバーを更新"""
        self.status_label.configure(text=message)
        logger.info(message)
    
    def on_closing(self):
        """ウィンドウクローズ時の処理"""
        self.monitoring = False
        
        if self.data_source and self.data_source.is_connected():
            self.data_source.disconnect()
        
        self.destroy()


def main():
    """メイン関数"""
    app = ClassifierApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
