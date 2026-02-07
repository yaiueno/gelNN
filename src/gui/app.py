"""
GUIアプリケーション - データ収集・学習・推論

customtkinterを使用した、モダンなGUIアプリケーションです。
- データ収集: グリッド上の位置をクリックしてインピーダンスデータを収集
- 学習: MLPRegressorで位置推定モデルを学習
- 推論: リアルタイムでタッチ位置を推定
"""

import customtkinter as ctk
import numpy as np
import pickle
import os
import json
from datetime import datetime
from typing import Optional, List, Tuple
import logging

from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from src.core.factory import DataSourceFactory
from src.core.interfaces import IDataSource, MeasurementResult
from src.utils import config

# ログ設定
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# customtkinter設定
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TouchEstimationApp(ctk.CTk):
    """
    タッチ位置推定アプリケーション
    
    データ収集、学習、推論の3つのモードを持ちます。
    """
    
    def __init__(self):
        super().__init__()
        
        # ウィンドウ設定
        self.title("Ion Gel Touch Position Estimation")
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        
        # データソース
        self.data_source: Optional[IDataSource] = None
        
        # 学習データ
        self.training_data: List[MeasurementResult] = []
        
        # 学習済みモデル
        self.model: Optional[MLPRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        
        # 実機モード判定
        self.use_real_hardware = config.USE_REAL_HARDWARE
        
        # グリッドボタン（実機モード用）
        self.grid_buttons: List[ctk.CTkButton] = []
        
        # UI構築
        self._create_widgets()
        
        # データソース接続
        self._connect_data_source()
        
        logger.info("アプリケーションを起動しました")
    
    def _create_widgets(self):
        """UIウィジェットを作成"""
        
        # グリッドレイアウト設定
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ========================================
        # 左サイドバー
        # ========================================
        
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # タイトル
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="Ion Gel Touch\nEstimation", 
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
        
        # データ収集セクション
        ctk.CTkLabel(
            self.sidebar, 
            text="Data Collection", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=4, column=0, padx=20, pady=(10, 5))
        
        self.samples_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Samples per position"
        )
        self.samples_entry.insert(0, str(config.DEFAULT_SAMPLES_PER_POSITION))
        self.samples_entry.grid(row=5, column=0, padx=20, pady=5)
        
        # 実機モード: 3x3グリッドボタン
        if self.use_real_hardware:
            # グリッドフレーム
            self.grid_frame = ctk.CTkFrame(self.sidebar)
            self.grid_frame.grid(row=6, column=0, padx=20, pady=10)
            
            # 3x3グリッドボタン作成
            for row in range(3):
                for col in range(3):
                    grid_id = row * 3 + col
                    btn = ctk.CTkButton(
                        self.grid_frame,
                        text=f"P{grid_id}",
                        width=60,
                        height=40,
                        command=lambda gid=grid_id, r=row, c=col: self._collect_at_grid(gid, r, c)
                    )
                    btn.grid(row=row, column=col, padx=3, pady=3)
                    self.grid_buttons.append(btn)
            
            # リセットボタン
            self.reset_btn = ctk.CTkButton(
                self.sidebar,
                text="Reset Collection",
                command=self._reset_grid_collection,
                fg_color="gray",
                hover_color="darkgray"
            )
            self.reset_btn.grid(row=7, column=0, padx=20, pady=5)
            
            current_row = 8
        else:
            # HILSモード: フリーハンド収集ボタン
            self.collect_btn = ctk.CTkButton(
                self.sidebar,
                text="Start Collection",
                command=self._start_collection_mode
            )
            self.collect_btn.grid(row=6, column=0, padx=20, pady=5)
            
            current_row = 7
        
        # 学習セクション
        ctk.CTkLabel(
            self.sidebar, 
            text="Training", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=current_row, column=0, padx=20, pady=(20, 5))
        
        self.train_btn = ctk.CTkButton(
            self.sidebar,
            text="Train Model",
            command=self._train_model
        )
        self.train_btn.grid(row=current_row+1, column=0, padx=20, pady=5)
        
        # 推論セクション（HILSモードのみ）
        if not self.use_real_hardware:
            ctk.CTkLabel(
                self.sidebar, 
                text="Inference", 
                font=ctk.CTkFont(size=14, weight="bold")
            ).grid(row=current_row+2, column=0, padx=20, pady=(20, 5))
            
            self.inference_btn = ctk.CTkButton(
                self.sidebar,
                text="Start Inference",
                command=self._start_inference_mode
            )
            self.inference_btn.grid(row=current_row+3, column=0, padx=20, pady=5)
            
            current_row += 4
        else:
            current_row += 2
        
        # データ数表示
        self.data_count_label = ctk.CTkLabel(
            self.sidebar,
            text="Training Data: 0",
            font=ctk.CTkFont(size=12)
        )
        self.data_count_label.grid(row=current_row, column=0, padx=20, pady=(20, 10))
        
        # 周波数情報セクション
        ctk.CTkLabel(
            self.sidebar, 
            text="Frequency Info", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=current_row+1, column=0, padx=20, pady=(20, 5))
        
        self.frequency_label = ctk.CTkLabel(
            self.sidebar,
            text=self._get_frequency_info_text(),
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        self.frequency_label.grid(row=current_row+2, column=0, padx=20, pady=5)
        
        self.analyze_freq_btn = ctk.CTkButton(
            self.sidebar,
            text="Analyze Frequencies",
            command=self._launch_frequency_analyzer,
            fg_color="orange",
            hover_color="darkorange"
        )
        self.analyze_freq_btn.grid(row=current_row+3, column=0, padx=20, pady=5)
        
        # ========================================
        # メインエリア
        # ========================================
        
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # キャンバス（タッチ位置表示用）
        self.canvas = ctk.CTkCanvas(
            self.main_frame,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        
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
    
    def _start_collection_mode(self):
        """データ収集モードを開始"""
        self._update_status("Click on canvas to collect data at that position")
        self.canvas.configure(cursor="crosshair")
    
    def _start_inference_mode(self):
        """推論モードを開始"""
        if self.model is None:
            self._update_status("Error: No trained model. Train a model first.")
            return
        
        self._update_status("Inference mode: Click to estimate touch position")
        self.canvas.configure(cursor="hand2")
    
    def _on_canvas_click(self, event):
        """キャンバスクリック時の処理"""
        # キャンバス座標を実座標に変換
        x_mm, y_mm = self._canvas_to_real_coords(event.x, event.y)
        
        # データ収集モード
        if self.canvas.cget("cursor") == "crosshair":
            self._collect_data_at_position(x_mm, y_mm)
        
        # 推論モード
        elif self.canvas.cget("cursor") == "hand2":
            self._infer_position()
    
    def _collect_data_at_position(self, x: float, y: float):
        """指定位置でデータを収集"""
        try:
            samples = int(self.samples_entry.get())
        except ValueError:
            self._update_status("Error: Invalid sample count")
            return
        
        self._update_status(f"Collecting {samples} samples at ({x:.1f}, {y:.1f})...")
        
        # 正解位置を設定
        self.data_source.set_ground_truth(x, y)
        
        # サンプル収集
        for i in range(samples):
            impedance_vector = self.data_source.measure_impedance_vector()
            
            result = MeasurementResult(
                impedance_vector=impedance_vector,
                ground_truth=(x, y),
                timestamp=datetime.now().timestamp()
            )
            
            self.training_data.append(result)
            
            self._update_status(f"Collected {i+1}/{samples} samples at ({x:.1f}, {y:.1f})")
        
        # データ数更新
        self.data_count_label.configure(text=f"Training Data: {len(self.training_data)}")
        
        # キャンバスに点を描画
        canvas_x, canvas_y = self._real_to_canvas_coords(x, y)
        self.canvas.create_oval(
            canvas_x-3, canvas_y-3, canvas_x+3, canvas_y+3,
            fill="green", outline="white"
        )
        
        self._update_status(f"Completed: {samples} samples at ({x:.1f}, {y:.1f})")
        
        # データ保存
        self._save_training_data()
    
    def _grid_to_position(self, row: int, col: int) -> Tuple[float, float]:
        """
        グリッド座標を実座標に変換
        
        Args:
            row: 行 (0-2)
            col: 列 (0-2)
            
        Returns:
            (x, y): ミリメートル座標
        """
        # ゲルサイズ内に均等配置 (0%, 50%, 100%)
        x = (col / 2.0) * config.GEL_WIDTH
        y = (row / 2.0) * config.GEL_HEIGHT
        
        return x, y
    
    def _collect_at_grid(self, grid_id: int, row: int, col: int):
        """
        グリッド位置でデータを収集
        
        Args:
            grid_id: グリッドID (0-8)
            row: 行 (0-2)
            col: 列 (0-2)
        """
        if not self.data_source or not self.data_source.is_connected():
            self._update_status("Error: Not connected to hardware")
            return
        
        x, y = self._grid_to_position(row, col)
        
        # ユーザーに指示
        self._update_status(f">>> Press Punchhole P{grid_id} at position ({x:.0f}, {y:.0f}) mm <<<")
        
        # ボタンの色を変更（測定準備中）
        btn = self.grid_buttons[grid_id]
        btn.configure(fg_color="orange", text=f"P{grid_id}\nReady...")
        
        # 1秒待機（ユーザーが準備する時間）
        self.after(1000, lambda: self._start_grid_measurement(grid_id, x, y, btn))
    
    def _start_grid_measurement(self, grid_id: int, x: float, y: float, btn: ctk.CTkButton):
        """
        実際の測定を開始
        
        Args:
            grid_id: グリッドID
            x: X座標 [mm]
            y: Y座標 [mm]
            btn: ボタンウィジェット
        """
        try:
            samples = int(self.samples_entry.get())
        except ValueError:
            samples = config.DEFAULT_SAMPLES_PER_POSITION
        
        # 正解位置を設定
        self.data_source.set_ground_truth(x, y)
        
        # 測定中表示
        btn.configure(text=f"P{grid_id}\nMeasuring...")
        
        # 測定実行
        for i in range(samples):
            try:
                impedance_vector = self.data_source.measure_impedance_vector()
                
                result = MeasurementResult(
                    impedance_vector=impedance_vector,
                    ground_truth=(x, y),
                    timestamp=datetime.now().timestamp()
                )
                
                self.training_data.append(result)
                
                # プログレス表示
                btn.configure(text=f"P{grid_id}\n{i+1}/{samples}")
                self._update_status(f"P{grid_id}: Collected {i+1}/{samples} samples")
                
                # UIを更新（応答性を保つ）
                self.update()
                
            except Exception as e:
                logger.error(f"測定エラー: {e}")
                btn.configure(fg_color="red", text=f"P{grid_id}\nError")
                self._update_status(f"Error at P{grid_id}: {e}")
                return
        
        # 完了 - ボタンを緑に
        btn.configure(fg_color="green", text=f"P{grid_id}\n✓")
        self.data_count_label.configure(text=f"Training Data: {len(self.training_data)}")
        
        # キャンバスに点を描画
        canvas_x, canvas_y = self._real_to_canvas_coords(x, y)
        self.canvas.create_oval(
            canvas_x-5, canvas_y-5, canvas_x+5, canvas_y+5,
            fill="green", outline="white", width=2
        )
        self.canvas.create_text(
            canvas_x, canvas_y-15,
            text=f"P{grid_id}", fill="white",
            font=("Arial", 10, "bold")
        )
        
        self._update_status(f"✓ P{grid_id} completed: {samples} samples at ({x:.0f}, {y:.0f}) mm")
        
        # データ保存
        self._save_training_data()
    
    def _reset_grid_collection(self):
        """
        グリッド収集状態をリセット
        """
        # ボタンをデフォルト色にリセット
        for i, btn in enumerate(self.grid_buttons):
            btn.configure(
                fg_color=["#3B8ED0", "#1F6AA5"],  # デフォルト色
                text=f"P{i}"
            )
        
        # データクリア
        self.training_data.clear()
        self.data_count_label.configure(text="Training Data: 0")
        
        # キャンバスクリア
        self.canvas.delete("all")
        self._on_canvas_resize(None)  # 端子を再描画
        
        self._update_status("Grid collection reset")
    
    def _train_model(self):
        """モデルを学習"""
        if len(self.training_data) < 10:
            self._update_status("Error: Need at least 10 samples to train")
            return
        
        self._update_status("Training model...")
        
        # 特徴量とラベルを抽出
        X = np.array([result.to_feature_vector() for result in self.training_data])
        y = np.array([result.ground_truth for result in self.training_data])
        
        # 正規化
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # モデル学習
        self.model = MLPRegressor(
            hidden_layer_sizes=config.HIDDEN_LAYER_SIZES,
            max_iter=config.MAX_ITERATIONS,
            random_state=config.RANDOM_STATE,
            verbose=False
        )
        
        self.model.fit(X_scaled, y)
        
        # モデル保存
        self._save_model()
        
        self._update_status(f"Training completed: {len(self.training_data)} samples")
    
    def _infer_position(self):
        """位置を推論"""
        if self.model is None:
            self._update_status("Error: No trained model")
            return
        
        self._update_status("Measuring...")
        
        # インピーダンス測定
        impedance_vector = self.data_source.measure_impedance_vector()
        
        result = MeasurementResult(impedance_vector=impedance_vector)
        
        # 特徴量抽出と正規化
        X = result.to_feature_vector().reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # 推論
        prediction = self.model.predict(X_scaled)[0]
        pred_x, pred_y = prediction
        
        # キャンバスに描画
        self.canvas.delete("inference")
        canvas_x, canvas_y = self._real_to_canvas_coords(pred_x, pred_y)
        self.canvas.create_oval(
            canvas_x-5, canvas_y-5, canvas_x+5, canvas_y+5,
            fill="red", outline="white", width=2, tags="inference"
        )
        
        self._update_status(f"Estimated position: ({pred_x:.1f}, {pred_y:.1f}) mm")
    
    def _canvas_to_real_coords(self, canvas_x: float, canvas_y: float) -> Tuple[float, float]:
        """キャンバス座標を実座標に変換"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        x_mm = (canvas_x / width) * config.GEL_WIDTH
        y_mm = (canvas_y / height) * config.GEL_HEIGHT
        
        return x_mm, y_mm
    
    def _real_to_canvas_coords(self, x_mm: float, y_mm: float) -> Tuple[float, float]:
        """実座標をキャンバス座標に変換"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        canvas_x = (x_mm / config.GEL_WIDTH) * width
        canvas_y = (y_mm / config.GEL_HEIGHT) * height
        
        return canvas_x, canvas_y
    
    def _on_canvas_resize(self, event):
        """キャンバスリサイズ時の処理"""
        # 端子位置を描画
        self.canvas.delete("terminal")
        
        for name, (x, y) in config.TERMINAL_POSITIONS.items():
            canvas_x, canvas_y = self._real_to_canvas_coords(x, y)
            self.canvas.create_oval(
                canvas_x-8, canvas_y-8, canvas_x+8, canvas_y+8,
                fill="blue", outline="white", width=2, tags="terminal"
            )
            self.canvas.create_text(
                canvas_x, canvas_y-15,
                text=name, fill="white", font=("Arial", 12, "bold"),
                tags="terminal"
            )
    
    def _update_status(self, message: str):
        """ステータスバーを更新"""
        self.status_label.configure(text=message)
        logger.info(message)
    
    def _save_training_data(self):
        """学習データを保存"""
        os.makedirs(config.DATA_DIR, exist_ok=True)
        
        filename = os.path.join(
            config.DATA_DIR,
            f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )
        
        with open(filename, 'wb') as f:
            pickle.dump(self.training_data, f)
        
        logger.info(f"学習データを保存: {filename}")
    
    def _save_model(self):
        """モデルを保存"""
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        
        model_file = os.path.join(config.MODEL_DIR, "model.pkl")
        scaler_file = os.path.join(config.MODEL_DIR, "scaler.pkl")
        
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        logger.info(f"モデルを保存: {model_file}")
    
    def _get_frequency_info_text(self) -> str:
        """周波数情報テキストを取得"""
        freq_info = config.get_frequency_analysis_info()
        
        if freq_info is None:
            return "Current: {:.0f} Hz\n(No analysis data)".format(config.MEASUREMENT_FREQUENCY)
        
        optimal_freq = freq_info.get('optimal_frequency', config.MEASUREMENT_FREQUENCY)
        last_updated = freq_info.get('last_updated', 'Unknown')
        
        # 日時を簡潔に表示
        if last_updated != 'Unknown':
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_updated)
                last_updated = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        recommended = freq_info.get('analysis_results', {}).get('recommended_frequencies', [])
        
        info_text = f"Optimal: {optimal_freq:.0f} Hz\n"
        if recommended and len(recommended) > 1:
            info_text += f"Also good: {recommended[1]:.0f} Hz\n"
        info_text += f"Updated: {last_updated}"
        
        return info_text
    
    def _launch_frequency_analyzer(self):
        """周波数分析ツールを起動"""
        import subprocess
        import sys
        
        self._update_status("Launching frequency analyzer...")
        
        # HILSモードか実機モードかを判定
        mode = "hils" if not config.USE_REAL_HARDWARE else "real"
        
        try:
            # 別プロセスで周波数分析ツールを起動
            subprocess.Popen([sys.executable, "frequency_analyzer.py", "--mode", mode])
            self._update_status(f"Frequency analyzer launched in {mode.upper()} mode")
        except Exception as e:
            self._update_status(f"Error launching analyzer: {e}")
            logger.error(f"周波数分析ツール起動エラー: {e}")
    
    def on_closing(self):
        """ウィンドウクローズ時の処理"""
        if self.data_source and self.data_source.is_connected():
            self.data_source.disconnect()
        
        self.destroy()


def main():
    """メイン関数"""
    app = TouchEstimationApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
