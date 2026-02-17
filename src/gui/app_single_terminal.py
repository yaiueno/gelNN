"""  
単一端子押圧検出 GUI - 学習モード & 判定モード + スペクトラム

customtkinter + matplotlib で以下のモードを提供:
  [学習モード] 押す/離す状態でデータ収集 → NNモデル学習
  [判定モード] 学習済みNNでリアルタイム押圧判定
  [スペクトラム] 2-20kHz周波数スイープ結果・ Xピーク追跡

AD3単体（Arduino不要）でも、HILS でも動作します。
"""

import customtkinter as ctk
import numpy as np
import logging
import time
from typing import Optional

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.core.interfaces import IDataSource
from src.core.models.press_classifier import PressClassifierModel
from src.utils import config

# ログ設定
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 定数
COLLECT_SAMPLES = 30          # 1回の収集で取るサンプル数
DEFAULT_UPDATE_MS = 200
GRAPH_WIDTH = 6
GRAPH_HEIGHT = 2.8

# スイープデフォルト
SWEEP_START_HZ = 2_000.0
SWEEP_STOP_HZ = 20_000.0
SWEEP_NUM_POINTS = 50


# =========================================================
# データソース生成ヘルパ
# =========================================================

def _create_data_source() -> IDataSource:
    """
    config に応じてデータソースを生成。
    USE_REAL_HARDWARE=True の場合は AD3OnlySource（Arduino不要）を使う。
    """
    if config.USE_REAL_HARDWARE:
        from src.hardware.ad3_only import AD3OnlySource
        logger.info("AD3 単体モードで起動します（Arduino不要）")
        return AD3OnlySource()
    else:
        # HILS モード
        if getattr(config, "USE_HILS_SERVER", False):
            from src.hils.client import HILSClientSource
            logger.info("HILS クライアントモードで起動します")
            return HILSClientSource()
        else:
            from src.hils.simulator import HILSSimulatorSource
            logger.info("HILS ローカルシミュレータで起動します")
            return HILSSimulatorSource()


def _get_mode_name() -> str:
    if config.USE_REAL_HARDWARE:
        return "AD3 Only (Real)"
    elif getattr(config, "USE_HILS_SERVER", False):
        return "HILS Client"
    else:
        return "HILS Simulator"


# =========================================================
# メインアプリ
# =========================================================

class SingleTerminalApp(ctk.CTk):
    """
    単一端子押圧検出アプリ (学習+判定)
    """

    def __init__(self):
        super().__init__()

        self.title("Single Terminal Press Detector")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # 内部状態
        self.data_source: Optional[IDataSource] = None
        self.classifier = PressClassifierModel()
        self.monitoring = False
        self._collecting = False
        self._collect_remaining = 0
        self._collect_label = 0
        self._update_interval = DEFAULT_UPDATE_MS

        # スイープモードフラグ
        self._sweep_mode = False   # True: Xピーク周波数を特徴量に使う

        # スペクトラム用
        self._last_sweep_data = None
        self._peak_freq_history: list = []
        self._peak_time_history: list = []

        # 波形履歴 (判定モード用)
        self._mag_history: list = []
        self._time_history: list = []
        self._press_history: list = []
        self._start_time = time.time()
        self._HISTORY_MAX = 200

        # UI構築
        self._create_widgets()

        # 接続
        self._connect_data_source()

        # 既存モデルロード試行
        if self.classifier.load():
            self._update_model_info()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        logger.info("SingleTerminalApp 起動")

    # =======================================================
    # 接続
    # =======================================================

    def _connect_data_source(self):
        try:
            self.data_source = _create_data_source()
            ok = self.data_source.connect()
            if ok:
                self._set_status("Connected", "#00ff00")
            else:
                self._set_status("Connection Failed", "red")
        except Exception as e:
            self._set_status(f"Error: {e}", "red")
            logger.exception("接続失敗")

    # =======================================================
    # 測定ヘルパ
    # =======================================================

    def _measure_once(self):
        """1回測定 → (sweep_features_or_None, magnitude, phase)"""
        if self.data_source is None:
            raise RuntimeError("データソース未接続")

        if self._sweep_mode and hasattr(self.data_source, 'sweep_impedance'):
            sweep = self.data_source.sweep_impedance()
            self._last_sweep_data = sweep
            sf = self.data_source.extract_sweep_features(sweep)
            return sf, sf['peak_magnitude'], sf['peak_phase']
        else:
            vec = self.data_source.measure_impedance_vector()
            return None, float(vec[0, 0]), float(vec[0, 1])

    # =======================================================
    # UI 構築
    # =======================================================

    def _create_widgets(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 左サイドバー (共通) ---
        self._create_sidebar()

        # --- 右メインエリア: TabView ---
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self._create_train_tab()
        self._create_detect_tab()
        self._create_spectrum_tab()

    # ----- サイドバー -----

    def _create_sidebar(self):
        sb = ctk.CTkFrame(self, width=240, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_rowconfigure(20, weight=1)
        self._sb = sb
        row = 0

        ctk.CTkLabel(sb, text="Single Terminal\nPress Detector",
                      font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=row, column=0, padx=18, pady=(18, 4)); row += 1

        ctk.CTkLabel(sb, text=f"Mode: {_get_mode_name()}",
                      font=ctk.CTkFont(size=11),
        ).grid(row=row, column=0, padx=18, pady=4); row += 1

        self.status_label = ctk.CTkLabel(sb, text="Status: ---",
                                          font=ctk.CTkFont(size=11), text_color="gray")
        self.status_label.grid(row=row, column=0, padx=18, pady=4); row += 1

        # モデル情報
        ctk.CTkLabel(sb, text="Model", font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=row, column=0, padx=18, pady=(14, 2)); row += 1

        self.model_info_label = ctk.CTkLabel(sb, text="Not trained",
                                              font=ctk.CTkFont(size=10), text_color="orange",
                                              wraplength=200, justify="left")
        self.model_info_label.grid(row=row, column=0, padx=18, pady=2); row += 1

        # 更新間隔
        ctk.CTkLabel(sb, text="Update Interval (ms)",
                      font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=row, column=0, padx=18, pady=(14, 2)); row += 1

        self.interval_entry = ctk.CTkEntry(sb, width=200, placeholder_text="200")
        self.interval_entry.insert(0, str(DEFAULT_UPDATE_MS))
        self.interval_entry.grid(row=row, column=0, padx=18, pady=4); row += 1

        # スイープモード切替
        ctk.CTkLabel(sb, text="Sweep Mode",
                      font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=row, column=0, padx=18, pady=(14, 2)); row += 1

        self.sweep_var = ctk.BooleanVar(value=False)
        self.sweep_switch = ctk.CTkSwitch(
            sb, text="Xピーク追跡 (2-20kHz)",
            variable=self.sweep_var,
            font=ctk.CTkFont(size=11),
            command=self._on_sweep_toggle,
        )
        self.sweep_switch.grid(row=row, column=0, padx=18, pady=4); row += 1

        self.sweep_info_label = ctk.CTkLabel(sb, text="OFF: 固定周波数",
                                              font=ctk.CTkFont(size=10), text_color="gray",
                                              wraplength=200, justify="left")
        self.sweep_info_label.grid(row=row, column=0, padx=18, pady=2); row += 1

    # ----- 学習モードタブ -----

    def _create_train_tab(self):
        tab = self.tabview.add("学習モード")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        # 説明
        ctk.CTkLabel(tab,
            text="押していない状態 と 押した状態 のデータを収集し、NNで学習します。",
            font=ctk.CTkFont(size=12), wraplength=600, justify="left",
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # ---- 収集コントロール ----
        ctrl = ctk.CTkFrame(tab)
        ctrl.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(ctrl, text=f"Samples per click: {COLLECT_SAMPLES}",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

        self.btn_collect_released = ctk.CTkButton(
            ctrl, text="Collect RELEASED (離す)", width=200,
            fg_color="#336633", hover_color="#448844",
            command=lambda: self._start_collect(label=0),
        )
        self.btn_collect_released.pack(side="left", padx=8, pady=8)

        self.btn_collect_pressed = ctk.CTkButton(
            ctrl, text="Collect PRESSED (押す)", width=200,
            fg_color="#663333", hover_color="#884444",
            command=lambda: self._start_collect(label=1),
        )
        self.btn_collect_pressed.pack(side="left", padx=8, pady=8)

        self.collect_progress = ctk.CTkProgressBar(ctrl, width=120)
        self.collect_progress.set(0)
        self.collect_progress.pack(side="left", padx=8)

        # ---- サンプル数 & 学習 ----
        train_ctrl = ctk.CTkFrame(tab)
        train_ctrl.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.sample_count_label = ctk.CTkLabel(
            train_ctrl, text="Released: 0    Pressed: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.sample_count_label.pack(side="left", padx=10)

        self.btn_clear = ctk.CTkButton(
            train_ctrl, text="Clear Data", width=120,
            fg_color="gray", hover_color="#666666",
            command=self._clear_data,
        )
        self.btn_clear.pack(side="left", padx=8, pady=8)

        self.btn_train = ctk.CTkButton(
            train_ctrl, text="Train Model", width=160,
            fg_color="#cc8800", hover_color="#aa7700",
            command=self._train_model,
        )
        self.btn_train.pack(side="left", padx=8, pady=8)

        self.train_result_label = ctk.CTkLabel(
            train_ctrl, text="", font=ctk.CTkFont(size=11),
        )
        self.train_result_label.pack(side="left", padx=10)

        # ---- 学習データ散布図 ----
        self.train_graph_frame = ctk.CTkFrame(tab)
        self.train_graph_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nsew")

        self.fig_train = Figure(figsize=(GRAPH_WIDTH, GRAPH_HEIGHT), dpi=100)
        self.fig_train.patch.set_facecolor("#2b2b2b")
        self.ax_train = self.fig_train.add_subplot(111)
        self._style_ax(self.ax_train, "Training Data")
        self.fig_train.tight_layout(pad=2)
        self.canvas_train = FigureCanvasTkAgg(self.fig_train, master=self.train_graph_frame)
        self.canvas_train.get_tk_widget().pack(fill="both", expand=True)

    # ----- 判定モードタブ -----

    def _create_detect_tab(self):
        tab = self.tabview.add("判定モード")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # ---- 上: インジケーター ----
        ind = ctk.CTkFrame(tab, height=170)
        ind.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ind.grid_columnconfigure(0, weight=1)
        ind.grid_columnconfigure(1, weight=1)
        ind.grid_columnconfigure(2, weight=1)
        ind.grid_columnconfigure(3, weight=0)

        self.press_label = ctk.CTkLabel(ind, text="---",
            font=ctk.CTkFont(size=56, weight="bold"), text_color="gray")
        self.press_label.grid(row=0, column=0, padx=18, pady=12, sticky="w")

        # 数値
        f1 = ctk.CTkFrame(ind, fg_color="transparent")
        f1.grid(row=0, column=1, padx=12, pady=12)
        ctk.CTkLabel(f1, text="Impedance", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.det_mag_label = ctk.CTkLabel(f1, text="--- Ohm",
            font=ctk.CTkFont(size=24, weight="bold"))
        self.det_mag_label.pack(anchor="w")
        ctk.CTkLabel(f1, text="Phase", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(6, 0))
        self.det_phase_label = ctk.CTkLabel(f1, text="--- rad", font=ctk.CTkFont(size=14))
        self.det_phase_label.pack(anchor="w")

        f2 = ctk.CTkFrame(ind, fg_color="transparent")
        f2.grid(row=0, column=2, padx=12, pady=12)
        ctk.CTkLabel(f2, text="Confidence", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.det_conf_label = ctk.CTkLabel(f2, text="--- %",
            font=ctk.CTkFont(size=24, weight="bold"))
        self.det_conf_label.pack(anchor="w")

        # Start / Stop
        btn_frame = ctk.CTkFrame(ind, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=12, pady=12)
        self.btn_start = ctk.CTkButton(btn_frame, text="Start", width=100,
            fg_color="green", hover_color="#009900", command=self._start_monitoring)
        self.btn_start.pack(pady=4)
        self.btn_stop = ctk.CTkButton(btn_frame, text="Stop", width=100,
            fg_color="red", hover_color="#990000", command=self._stop_monitoring, state="disabled")
        self.btn_stop.pack(pady=4)

        # ---- 下: リアルタイムグラフ ----
        self.det_graph_frame = ctk.CTkFrame(tab)
        self.det_graph_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self.fig_det = Figure(figsize=(GRAPH_WIDTH, GRAPH_HEIGHT), dpi=100)
        self.fig_det.patch.set_facecolor("#2b2b2b")
        self.ax_det = self.fig_det.add_subplot(111)
        self._style_ax(self.ax_det, "Impedance Magnitude (Real-time)")
        self.line_det, = self.ax_det.plot([], [], color="#00aaff", linewidth=1.5)
        self.fig_det.tight_layout(pad=2)
        self.canvas_det = FigureCanvasTkAgg(self.fig_det, master=self.det_graph_frame)
        self.canvas_det.get_tk_widget().pack(fill="both", expand=True)

    # ---- グラフスタイル ----
    @staticmethod
    def _style_ax(ax, title: str):
        ax.set_facecolor("#1e1e1e")
        ax.set_title(title, color="white", fontsize=11)
        ax.tick_params(colors="white", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#555555")

    # ----- スペクトラムタブ -----

    def _create_spectrum_tab(self):
        tab = self.tabview.add("スペクトラム")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # コントロール
        ctrl = ctk.CTkFrame(tab)
        ctrl.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        self.btn_single_sweep = ctk.CTkButton(
            ctrl, text="Single Sweep", width=140,
            fg_color="#336699", hover_color="#4477aa",
            command=self._run_single_sweep,
        )
        self.btn_single_sweep.pack(side="left", padx=8, pady=8)

        self.btn_continuous_sweep = ctk.CTkButton(
            ctrl, text="Continuous", width=120,
            fg_color="#339966", hover_color="#44aa77",
            command=self._toggle_continuous_sweep,
        )
        self.btn_continuous_sweep.pack(side="left", padx=8, pady=8)
        self._continuous_sweep = False

        self.sweep_status_label = ctk.CTkLabel(
            ctrl, text="", font=ctk.CTkFont(size=11))
        self.sweep_status_label.pack(side="left", padx=10)

        # Xピーク情報
        info = ctk.CTkFrame(tab)
        info.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(info, text="X Peak Freq:",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=10)
        self.peak_freq_label = ctk.CTkLabel(
            info, text="--- Hz",
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#ffaa00")
        self.peak_freq_label.pack(side="left", padx=10)

        ctk.CTkLabel(info, text="X(peak):",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=10)
        self.peak_x_label = ctk.CTkLabel(
            info, text="--- Ω",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#00aaff")
        self.peak_x_label.pack(side="left", padx=5)

        ctk.CTkLabel(info, text="|Z|(peak):",
                      font=ctk.CTkFont(size=11)).pack(side="left", padx=10)
        self.peak_z_label = ctk.CTkLabel(
            info, text="--- Ω",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#aaaaaa")
        self.peak_z_label.pack(side="left", padx=5)

        # スペクトラムグラフ (上: |Z| & R, 下: X)
        self.spectrum_graph_frame = ctk.CTkFrame(tab)
        self.spectrum_graph_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="nsew")

        self.fig_spec = Figure(figsize=(GRAPH_WIDTH, GRAPH_HEIGHT * 1.6), dpi=100)
        self.fig_spec.patch.set_facecolor("#2b2b2b")
        self.ax_spec_z = self.fig_spec.add_subplot(211)
        self.ax_spec_x = self.fig_spec.add_subplot(212)
        self._style_ax(self.ax_spec_z, "|Z| & R  vs  Frequency")
        self._style_ax(self.ax_spec_x, "Reactance (X)  vs  Frequency")
        self.fig_spec.tight_layout(pad=2)
        self.canvas_spec = FigureCanvasTkAgg(self.fig_spec, master=self.spectrum_graph_frame)
        self.canvas_spec.get_tk_widget().pack(fill="both", expand=True)

    # =======================================================
    # 共通
    # =======================================================

    def _set_status(self, text: str, color: str = "white"):
        self.status_label.configure(text=f"Status: {text}", text_color=color)

    def _on_sweep_toggle(self):
        """スイープモード切替"""
        self._sweep_mode = self.sweep_var.get()
        if self._sweep_mode:
            self.sweep_info_label.configure(
                text="ON: Xピーク周波数 + mag + phase (3D)",
                text_color="#ffaa00")
            self.classifier.use_sweep = True
        else:
            self.sweep_info_label.configure(
                text="OFF: 固定周波数 mag + phase (2D)",
                text_color="gray")
            self.classifier.use_sweep = False

        # データが溜まっていたらクリア警告
        if self.classifier.total_samples > 0:
            self._set_status("Mode changed - consider clearing data", "orange")
        logger.info(f"スイープモード: {self._sweep_mode}")

    def _update_model_info(self):
        if self.classifier.is_ready():
            self.model_info_label.configure(
                text=self.classifier.get_info(), text_color="#00ff00")
        else:
            self.model_info_label.configure(text="Not trained", text_color="orange")

    def _update_sample_count(self):
        n0, n1 = self.classifier.get_sample_counts()
        self.sample_count_label.configure(text=f"Released: {n0}    Pressed: {n1}")

    # =======================================================
    # 学習モード: データ収集
    # =======================================================

    def _start_collect(self, label: int):
        if self.data_source is None or not self.data_source.is_connected():
            self._set_status("Not connected", "red")
            return
        self._collecting = True
        self._collect_remaining = COLLECT_SAMPLES
        self._collect_label = label
        self.collect_progress.set(0)
        self.btn_collect_released.configure(state="disabled")
        self.btn_collect_pressed.configure(state="disabled")
        lbl = "PRESSED" if label == 1 else "RELEASED"
        self._set_status(f"Collecting {lbl}...", "yellow")
        self._collect_step()

    def _collect_step(self):
        if not self._collecting or self._collect_remaining <= 0:
            self._finish_collect()
            return
        try:
            sweep_features, mag, phase = self._measure_once()
            self.classifier.add_sample(mag, phase, self._collect_label,
                                       sweep_features=sweep_features)
            done = COLLECT_SAMPLES - self._collect_remaining + 1
            self.collect_progress.set(done / COLLECT_SAMPLES)
            self._collect_remaining -= 1
            self.after(30, self._collect_step)
        except Exception as e:
            logger.error(f"収集エラー: {e}")
            self._set_status(f"Error: {e}", "red")
            self._finish_collect()

    def _finish_collect(self):
        self._collecting = False
        self.btn_collect_released.configure(state="normal")
        self.btn_collect_pressed.configure(state="normal")
        self._update_sample_count()
        self._update_train_scatter()
        self._set_status("Collection done", "#00ff00")

    def _clear_data(self):
        self.classifier.clear_samples()
        self._update_sample_count()
        self._update_train_scatter()
        self.train_result_label.configure(text="")

    # =======================================================
    # 学習モード: 散布図
    # =======================================================

    def _update_train_scatter(self):
        ax = self.ax_train
        ax.clear()
        self._style_ax(ax, "Training Data")

        if self.classifier.total_samples == 0:
            self.canvas_train.draw_idle()
            return

        X = np.array(self.classifier._X_buf)
        y = np.array(self.classifier._y_buf)

        mask0 = y == 0
        mask1 = y == 1

        if self.classifier.use_sweep and X.shape[1] == 10:
            # 10D: X軸=log10(peak_freq), Y軸=x_mean_high
            xidx, yidx = 0, 8
            xlabel = "log10(peak_freq)"
            ylabel = "x_mean_high [Ω]"
        else:
            xidx, yidx = 0, 1
            xlabel = "log10(mag+1)"
            ylabel = "phase [rad]"

        if mask0.any():
            ax.scatter(X[mask0, xidx], X[mask0, yidx],
                       c="#33ff33", s=20, alpha=0.7, label="Released")
        if mask1.any():
            ax.scatter(X[mask1, xidx], X[mask1, yidx],
                       c="#ff3333", s=20, alpha=0.7, label="Pressed")

        ax.set_xlabel(xlabel, color="white", fontsize=9)
        ax.set_ylabel(ylabel, color="white", fontsize=9)
        ax.legend(fontsize=8, facecolor="#333333", edgecolor="#555555", labelcolor="white")
        self.canvas_train.draw_idle()

    # =======================================================
    # 学習モード: 学習実行
    # =======================================================

    def _train_model(self):
        n0, n1 = self.classifier.get_sample_counts()
        if n0 < 2 or n1 < 2:
            self.train_result_label.configure(
                text="Both classes need at least 2 samples", text_color="red")
            return

        try:
            result = self.classifier.train()
            self.classifier.save()
            self.train_result_label.configure(
                text=f"Train: {result['train_acc']:.1%}  Test: {result['test_acc']:.1%}  "
                     f"(n={result['n_train']}+{result['n_test']})",
                text_color="#00ff00",
            )
            self._update_model_info()
            self._draw_decision_boundary()
        except Exception as e:
            logger.error(f"学習エラー: {e}")
            self.train_result_label.configure(text=f"Error: {e}", text_color="red")

    def _draw_decision_boundary(self):
        """学習データ散布図に決定境界を重ねて描画 (2D特徴量のみ)"""
        if not self.classifier.is_ready():
            return
        if self.classifier.scaler is None or self.classifier.model is None:
            return
        # 3D 特徴量 (sweep mode) では 2D 境界を描画できないのでスキップ
        if getattr(self.classifier, 'use_sweep', False):
            return

        ax = self.ax_train
        X = np.array(self.classifier._X_buf)
        y = np.array(self.classifier._y_buf)
        if len(X) < 2 or X.shape[1] != 2:
            return

        # メッシュグリッド
        x_min, x_max = X[:, 0].min() - 0.2, X[:, 0].max() + 0.2
        y_min, y_max = X[:, 1].min() - 0.2, X[:, 1].max() + 0.2
        xx, yy = np.meshgrid(
            np.linspace(x_min, x_max, 100),
            np.linspace(y_min, y_max, 100),
        )
        grid = np.c_[xx.ravel(), yy.ravel()]
        grid_scaled = self.classifier.scaler.transform(grid)
        proba = self.classifier.model.predict_proba(grid_scaled)
        press_idx = list(self.classifier.model.classes_).index(1)
        Z = proba[:, press_idx].reshape(xx.shape)

        ax.contourf(xx, yy, Z, levels=20, cmap="RdYlGn_r", alpha=0.3)
        ax.contour(xx, yy, Z, levels=[0.5], colors=["#ffcc00"], linewidths=2)

        self.canvas_train.draw_idle()

    # =======================================================
    # 判定モード
    # =======================================================

    def _start_monitoring(self):
        if not self.classifier.is_ready():
            self._set_status("Train model first!", "orange")
            return
        if self.data_source is None or not self.data_source.is_connected():
            self._set_status("Not connected", "red")
            return

        try:
            self._update_interval = int(self.interval_entry.get())
        except ValueError:
            self._update_interval = DEFAULT_UPDATE_MS

        self.monitoring = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._mag_history.clear()
        self._time_history.clear()
        self._press_history.clear()
        self._peak_freq_history.clear()
        self._peak_time_history.clear()
        self._start_time = time.time()
        self._set_status("Monitoring", "#00ff00")
        self._monitor_loop()

    def _stop_monitoring(self):
        self.monitoring = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self._set_status("Stopped", "gray")

    def _monitor_loop(self):
        if not self.monitoring:
            return
        try:
            sweep_features, mag, phase = self._measure_once()
            label, confidence = self.classifier.predict(
                mag, phase, sweep_features=sweep_features)
            is_pressed = label == 1

            # 履歴
            t = time.time() - self._start_time
            self._mag_history.append(mag)
            self._time_history.append(t)
            self._press_history.append(is_pressed)
            peak_freq = sweep_features['peak_freq'] if sweep_features else None
            if peak_freq is not None:
                self._peak_freq_history.append(peak_freq)
                self._peak_time_history.append(t)
                if len(self._peak_freq_history) > self._HISTORY_MAX:
                    self._peak_freq_history = self._peak_freq_history[-self._HISTORY_MAX:]
                    self._peak_time_history = self._peak_time_history[-self._HISTORY_MAX:]
            if len(self._mag_history) > self._HISTORY_MAX:
                self._mag_history = self._mag_history[-self._HISTORY_MAX:]
                self._time_history = self._time_history[-self._HISTORY_MAX:]
                self._press_history = self._press_history[-self._HISTORY_MAX:]

            # UI更新
            self._update_detect_ui(is_pressed, mag, phase, confidence, peak_freq)
            self._update_detect_graph()

            # スイープモード時はスペクトラムも更新
            if self._sweep_mode and self._last_sweep_data is not None:
                self._update_spectrum_graph(self._last_sweep_data)
        except Exception as e:
            logger.error(f"判定エラー: {e}")
            self._set_status(f"Error: {e}", "red")

        if self.monitoring:
            self.after(self._update_interval, self._monitor_loop)

    def _update_detect_ui(self, pressed: bool, mag: float, phase: float, conf: float,
                           peak_freq: Optional[float] = None):
        if pressed:
            self.press_label.configure(text="PRESSED", text_color="#ff3333")
        else:
            self.press_label.configure(text="RELEASED", text_color="#33ff33")

        self.det_mag_label.configure(text=f"{mag:.1f} Ohm")
        self.det_phase_label.configure(text=f"{phase:.4f} rad")
        self.det_conf_label.configure(
            text=f"{conf * 100:.1f} %",
            text_color="#ff5555" if pressed else "#55ff55",
        )

        # スペクトラムタブのピーク情報も同期
        if peak_freq is not None:
            self.peak_freq_label.configure(text=f"{peak_freq:.0f} Hz")

    def _update_detect_graph(self):
        if len(self._time_history) < 2:
            return
        times = self._time_history
        mags = self._mag_history

        self.line_det.set_data(times, mags)
        t0, t1 = times[0], times[-1]
        self.ax_det.set_xlim(t0, max(t1, t0 + 1))
        arr = np.array(mags)
        self.ax_det.set_ylim(arr.min() * 0.95, arr.max() * 1.05)
        self.ax_det.set_xlabel("Time [s]", color="white", fontsize=9)
        self.ax_det.set_ylabel("Magnitude [Ohm]", color="white", fontsize=9)
        self.canvas_det.draw_idle()

    # =======================================================
    # スペクトラム
    # =======================================================

    def _run_single_sweep(self):
        """1回スイープして表示"""
        if self.data_source is None or not self.data_source.is_connected():
            self._set_status("Not connected", "red")
            return
        if not hasattr(self.data_source, 'sweep_impedance'):
            self._set_status("Sweep not supported (HILS?)", "orange")
            return

        try:
            self.sweep_status_label.configure(text="Sweeping...", text_color="yellow")
            self.update_idletasks()

            sweep = self.data_source.sweep_impedance()
            peak = self.data_source.find_x_peak(sweep)
            self._last_sweep_data = sweep

            self._update_spectrum_graph(sweep, peak)
            self.sweep_status_label.configure(
                text=f"Done  |  Peak: {peak['peak_freq']:.0f} Hz",
                text_color="#00ff00")
        except Exception as e:
            logger.error(f"スイープエラー: {e}")
            self.sweep_status_label.configure(text=f"Error: {e}", text_color="red")

    def _toggle_continuous_sweep(self):
        """連続スイープのON/OFF"""
        if self._continuous_sweep:
            self._continuous_sweep = False
            self.btn_continuous_sweep.configure(text="Continuous", fg_color="#339966")
        else:
            if self.data_source is None or not self.data_source.is_connected():
                self._set_status("Not connected", "red")
                return
            if not hasattr(self.data_source, 'sweep_impedance'):
                self._set_status("Sweep not supported", "orange")
                return
            self._continuous_sweep = True
            self.btn_continuous_sweep.configure(text="Stop", fg_color="#cc3333")
            self._continuous_sweep_loop()

    def _continuous_sweep_loop(self):
        if not self._continuous_sweep:
            return
        try:
            sweep = self.data_source.sweep_impedance()
            peak = self.data_source.find_x_peak(sweep)
            self._last_sweep_data = sweep
            self._update_spectrum_graph(sweep, peak)

            self.sweep_status_label.configure(
                text=f"Peak: {peak['peak_freq']:.0f} Hz  |  "
                     f"|Z|={peak['peak_magnitude']:.0f}Ω  "
                     f"X={peak['peak_reactance']:.0f}Ω",
                text_color="#00ff00")
        except Exception as e:
            logger.error(f"連続スイープエラー: {e}")

        if self._continuous_sweep:
            self.after(300, self._continuous_sweep_loop)

    def _update_spectrum_graph(self, sweep: dict, peak: dict = None):
        """スペクトラムグラフを更新"""
        freqs = sweep['frequencies']
        mag = sweep['magnitude']
        res = sweep['resistance']
        rea = sweep['reactance']

        if peak is None and hasattr(self.data_source, 'find_x_peak'):
            peak = self.data_source.find_x_peak(sweep)

        # 上段: |Z| と R
        ax1 = self.ax_spec_z
        ax1.clear()
        self._style_ax(ax1, "|Z| & R  vs  Frequency")
        ax1.semilogx(freqs, mag, color="#00aaff", linewidth=1.5, label="|Z|")
        ax1.semilogx(freqs, res, color="#88ff88", linewidth=1.0, alpha=0.7, label="R")
        if peak:
            ax1.axvline(peak['peak_freq'], color="#ffaa00", linestyle="--", alpha=0.8,
                        label=f"Xpeak={peak['peak_freq']:.0f}Hz")
        ax1.set_xlabel("Frequency [Hz]", color="white", fontsize=9)
        ax1.set_ylabel("Impedance [Ω]", color="white", fontsize=9)
        ax1.legend(fontsize=7, facecolor="#333333", edgecolor="#555555", labelcolor="white")

        # 下段: X (リアクタンス)
        ax2 = self.ax_spec_x
        ax2.clear()
        self._style_ax(ax2, "Reactance (X)  vs  Frequency")
        ax2.semilogx(freqs, rea, color="#ff6666", linewidth=1.5, label="X")
        ax2.axhline(0, color="#555555", linewidth=0.5)
        if peak:
            ax2.plot(peak['peak_freq'], peak['peak_reactance'],
                     'o', color="#ffaa00", markersize=10, zorder=5,
                     label=f"Peak X={peak['peak_reactance']:.0f}Ω")
            ax2.axvline(peak['peak_freq'], color="#ffaa00", linestyle="--", alpha=0.5)
        ax2.set_xlabel("Frequency [Hz]", color="white", fontsize=9)
        ax2.set_ylabel("Reactance [Ω]", color="white", fontsize=9)
        ax2.legend(fontsize=7, facecolor="#333333", edgecolor="#555555", labelcolor="white")

        self.fig_spec.tight_layout(pad=2)
        self.canvas_spec.draw_idle()

        # ピーク数値ラベル更新
        if peak:
            self.peak_freq_label.configure(text=f"{peak['peak_freq']:.0f} Hz")
            self.peak_x_label.configure(text=f"{peak['peak_reactance']:.1f} Ω")
            self.peak_z_label.configure(text=f"{peak['peak_magnitude']:.1f} Ω")

    # =======================================================
    # 終了
    # =======================================================

    def _on_close(self):
        self.monitoring = False
        self._collecting = False
        self._continuous_sweep = False
        if self.data_source:
            try:
                self.data_source.disconnect()
            except Exception:
                pass
        self.destroy()


def main():
    app = SingleTerminalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
