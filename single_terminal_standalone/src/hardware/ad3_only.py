"""
AD3単体ドライバ - Arduinoなし、単一端子ペア測定

Analog Discovery 3のみを使用し、MUX切り替えなしで
1ペア（W1+/1+ → 1-/GND）のインピーダンスを直接測定します。
端子切り替えがないので Arduino は不要です。

2-20kHz 周波数スイープによるリアクタンス(X)ピーク検出にも対応。
"""

import numpy as np
import time
import logging
from typing import Tuple, Optional, List, Dict

from src.core.interfaces import IDataSource
from src.utils import config

# Analog Discovery 3 SDK のインポート
try:
    from ctypes import *
    from src.hardware.dwfconstants import *
    import sys

    if sys.platform.startswith("win"):
        dwf = cdll.dwf
    elif sys.platform.startswith("darwin"):
        dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
    else:
        dwf = cdll.LoadLibrary("libdwf.so")

    AD3_AVAILABLE = True
except Exception as e:
    AD3_AVAILABLE = False
    print(f"Warning: AD3 SDK not available: {e}")

logger = logging.getLogger(__name__)


class AD3OnlySource(IDataSource):
    """
    AD3単体ドライバ（Arduino不要）

    端子切り替えなし。AD3のインピーダンスアナライザで
    固定1ペアを繰り返し測定します。
    measure_impedance_vector() は shape=(1, 2) を返します。

    sweep_impedance() で2-20kHzスイープを行い、
    リアクタンス(X)ピーク周波数を検出できます。
    """

    # スイープデフォルト設定
    SWEEP_START_HZ = 2_000.0
    SWEEP_STOP_HZ = 20_000.0
    SWEEP_NUM_POINTS = 50

    def __init__(self):
        if not AD3_AVAILABLE:
            raise RuntimeError(
                "AD3 SDK が利用できません。WaveForms SDK をインストールしてください。"
            )

        self._connected = False
        self.hdwf = c_int()

        # 最新スイープ結果キャッシュ
        self._last_sweep: Optional[Dict] = None

        logger.info("AD3OnlySource を初期化しました（Arduino不要）")

    # --------------------------------------------------
    # IDataSource 実装
    # --------------------------------------------------

    def connect(self) -> bool:
        try:
            logger.info("Analog Discovery 3 に接続中...")
            dwf.FDwfDeviceOpen(c_int(-1), byref(self.hdwf))

            if self.hdwf.value == 0:
                szerr = create_string_buffer(512)
                dwf.FDwfGetLastErrorMsg(szerr)
                logger.error(f"AD3 が見つかりません: {szerr.value.decode()}")
                return False

            logger.info(f"AD3 に接続しました (Handle: {self.hdwf.value})")
            self._setup_impedance_analyzer()
            self._connected = True
            return True

        except Exception as e:
            logger.error(f"AD3 接続エラー: {e}")
            return False

    def disconnect(self) -> None:
        if self.hdwf.value != 0:
            dwf.FDwfDeviceClose(self.hdwf)
            logger.info("AD3 から切断しました")
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def set_ground_truth(self, x: float, y: float) -> None:
        pass  # 実機では不要

    def get_ground_truth(self) -> Optional[Tuple[float, float]]:
        return None

    def measure_impedance_vector(self) -> np.ndarray:
        """
        1ペア分のインピーダンスを測定

        Returns:
            np.ndarray: shape=(1, 2)  [[Magnitude, Phase]]
        """
        if not self._connected:
            raise RuntimeError("AD3 が接続されていません")

        magnitude, phase = self._measure_single_impedance()
        return np.array([[magnitude, phase]])

    def get_device_info(self) -> str:
        if not self._connected:
            return "AD3 Only (Not Connected)"
        version = create_string_buffer(32)
        dwf.FDwfGetVersion(version)
        return f"AD3 Only (SDK: {version.value.decode()}, No Arduino)"

    # --------------------------------------------------
    # 内部メソッド
    # --------------------------------------------------

    def _setup_impedance_analyzer(self) -> None:
        dwf.FDwfAnalogImpedanceModeSet(self.hdwf, c_int(8))
        dwf.FDwfAnalogImpedanceReferenceSet(self.hdwf, c_double(10000.0))
        dwf.FDwfAnalogImpedanceFrequencySet(
            self.hdwf, c_double(config.MEASUREMENT_FREQUENCY)
        )
        dwf.FDwfAnalogImpedanceAmplitudeSet(
            self.hdwf, c_double(config.MEASUREMENT_AMPLITUDE)
        )
        # インピーダンスアナライザを開始して安定化を待つ
        dwf.FDwfAnalogImpedanceConfigure(self.hdwf, c_int(0))  # 設定適用
        time.sleep(0.5)  # セトリング待ち
        logger.info(
            f"AD3 インピーダンスアナライザ設定完了: "
            f"{config.MEASUREMENT_FREQUENCY}Hz, {config.MEASUREMENT_AMPLITUDE}V"
        )

    def _measure_single_impedance(self) -> Tuple[float, float]:
        dwf.FDwfAnalogImpedanceConfigure(self.hdwf, c_int(1))

        sts = c_byte()
        timeout_count = 0
        while True:
            dwf.FDwfAnalogImpedanceStatus(self.hdwf, byref(sts))
            if sts.value == 2:  # DwfStateDone
                break
            time.sleep(0.01)
            timeout_count += 1
            if timeout_count > 500:
                raise RuntimeError("AD3 インピーダンス測定タイムアウト")

        resistance = c_double()
        reactance = c_double()
        # *** 修正: R と X を個別に取得（API は 3 引数: hdwf, type, &value）***
        dwf.FDwfAnalogImpedanceStatusMeasure(
            self.hdwf, DwfAnalogImpedanceResistance, byref(resistance)
        )
        dwf.FDwfAnalogImpedanceStatusMeasure(
            self.hdwf, DwfAnalogImpedanceReactance, byref(reactance)
        )

        z_real = resistance.value
        z_imag = reactance.value
        magnitude = np.sqrt(z_real ** 2 + z_imag ** 2)
        phase = np.arctan2(z_imag, z_real)

        logger.debug(
            f"測定値: R={z_real:.2f}Ω, X={z_imag:.2f}Ω, "
            f"|Z|={magnitude:.2f}Ω, phase={phase:.4f}rad"
        )

        return magnitude, phase

    # --------------------------------------------------
    # 周波数スイープ & ピーク検出
    # --------------------------------------------------

    def sweep_impedance(
        self,
        start_hz: float = None,
        stop_hz: float = None,
        num_points: int = None,
    ) -> Dict:
        """
        周波数スイープを実行し、各周波数でのインピーダンスを取得

        Args:
            start_hz: 開始周波数 [Hz] (デフォルト 2kHz)
            stop_hz: 終了周波数 [Hz] (デフォルト 20kHz)
            num_points: 測定点数 (デフォルト 50)

        Returns:
            dict: {
                'frequencies':  np.ndarray shape=(N,),
                'magnitude':    np.ndarray shape=(N,),  # |Z| [Ω]
                'phase':        np.ndarray shape=(N,),  # [rad]
                'resistance':   np.ndarray shape=(N,),  # R [Ω]
                'reactance':    np.ndarray shape=(N,),  # X [Ω]
            }
        """
        if not self._connected:
            raise RuntimeError("AD3 が接続されていません")

        start_hz = start_hz or self.SWEEP_START_HZ
        stop_hz = stop_hz or self.SWEEP_STOP_HZ
        num_points = num_points or self.SWEEP_NUM_POINTS

        freqs = np.logspace(np.log10(start_hz), np.log10(stop_hz), num_points)
        magnitudes = np.zeros(num_points)
        phases = np.zeros(num_points)
        resistances = np.zeros(num_points)
        reactances = np.zeros(num_points)

        for i, freq in enumerate(freqs):
            # 周波数を変更して測定
            dwf.FDwfAnalogImpedanceFrequencySet(self.hdwf, c_double(freq))
            time.sleep(0.002)  # セトリング

            dwf.FDwfAnalogImpedanceConfigure(self.hdwf, c_int(1))

            sts = c_byte()
            timeout_count = 0
            while True:
                dwf.FDwfAnalogImpedanceStatus(self.hdwf, byref(sts))
                if sts.value == 2:
                    break
                time.sleep(0.005)
                timeout_count += 1
                if timeout_count > 200:
                    logger.warning(f"スイープ {freq:.0f}Hz でタイムアウト")
                    break

            r = c_double()
            x = c_double()
            # *** 修正: R と X を個別に取得（API は 3 引数）***
            dwf.FDwfAnalogImpedanceStatusMeasure(
                self.hdwf, DwfAnalogImpedanceResistance, byref(r)
            )
            dwf.FDwfAnalogImpedanceStatusMeasure(
                self.hdwf, DwfAnalogImpedanceReactance, byref(x)
            )

            resistances[i] = r.value
            reactances[i] = x.value
            magnitudes[i] = np.sqrt(r.value ** 2 + x.value ** 2)
            phases[i] = np.arctan2(x.value, r.value)

        # 元の周波数に戻す
        dwf.FDwfAnalogImpedanceFrequencySet(
            self.hdwf, c_double(config.MEASUREMENT_FREQUENCY)
        )

        result = {
            'frequencies': freqs,
            'magnitude': magnitudes,
            'phase': phases,
            'resistance': resistances,
            'reactance': reactances,
        }
        self._last_sweep = result

        logger.debug(
            f"スイープ完了: {start_hz:.0f}-{stop_hz:.0f}Hz, {num_points}点"
        )
        return result

    def find_x_peak(self, sweep_data: Dict = None) -> Dict:
        """
        リアクタンス(X)のピークを検出

        Args:
            sweep_data: sweep_impedance() の戻り値。None なら最新キャッシュを使用

        Returns:
            dict: {
                'peak_freq':       float,  # ピーク周波数 [Hz]
                'peak_reactance':  float,  # ピーク時の X [Ω]
                'peak_magnitude':  float,  # ピーク時の |Z| [Ω]
                'peak_phase':      float,  # ピーク時の phase [rad]
                'peak_index':      int,    # ピークのインデックス
            }
        """
        if sweep_data is None:
            sweep_data = self._last_sweep
        if sweep_data is None:
            raise RuntimeError("スイープデータがありません。先に sweep_impedance() を実行してください。")

        freqs = sweep_data['frequencies']
        reactance = sweep_data['reactance']
        magnitude = sweep_data['magnitude']
        phase = sweep_data['phase']

        # |X| が最大となる点をピークとする
        abs_x = np.abs(reactance)
        peak_idx = int(np.argmax(abs_x))

        result = {
            'peak_freq': float(freqs[peak_idx]),
            'peak_reactance': float(reactance[peak_idx]),
            'peak_magnitude': float(magnitude[peak_idx]),
            'peak_phase': float(phase[peak_idx]),
            'peak_index': peak_idx,
        }

        logger.debug(
            f"Xピーク検出: {result['peak_freq']:.0f}Hz, "
            f"X={result['peak_reactance']:.1f}Ω, |Z|={result['peak_magnitude']:.1f}Ω"
        )
        return result

    def extract_sweep_features(self, sweep_data: Dict = None) -> Dict:
        """
        スイープデータからスペクトル特徴量を抽出 (分類用)

        スペクトルを低域/中域/高域の3バンドに分割し、
        各帯域の |Z| 平均・X 平均、およびXの傾きを含む
        10次元特徴量セットを返します。高域の差異も捉えられます。

        Returns:
            dict: peak_freq, peak_magnitude, peak_phase, peak_reactance,
                  z_mean_low, z_mean_mid, z_mean_high,
                  x_mean_low, x_mean_mid, x_mean_high,
                  x_slope
        """
        if sweep_data is None:
            sweep_data = self._last_sweep
        if sweep_data is None:
            raise RuntimeError(
                "スイープデータがありません。先に sweep_impedance() を実行してください。"
            )

        peak = self.find_x_peak(sweep_data)

        freqs = sweep_data['frequencies']
        mag = sweep_data['magnitude']
        reactance = sweep_data['reactance']
        n = len(freqs)

        # 3バンドに分割 (低域 / 中域 / 高域)
        n3 = n // 3
        low = slice(0, n3)
        mid = slice(n3, 2 * n3)
        high = slice(2 * n3, n)

        # X の傾き (対数周波数空間での線形回帰)
        log_freqs = np.log10(freqs)
        x_slope = float(np.polyfit(log_freqs, reactance, 1)[0])

        result = {
            'peak_freq': peak['peak_freq'],
            'peak_magnitude': peak['peak_magnitude'],
            'peak_phase': peak['peak_phase'],
            'peak_reactance': peak['peak_reactance'],
            'z_mean_low': float(np.mean(mag[low])),
            'z_mean_mid': float(np.mean(mag[mid])),
            'z_mean_high': float(np.mean(mag[high])),
            'x_mean_low': float(np.mean(reactance[low])),
            'x_mean_mid': float(np.mean(reactance[mid])),
            'x_mean_high': float(np.mean(reactance[high])),
            'x_slope': x_slope,
        }

        logger.debug(
            f"スペクトル特徴量: peak={result['peak_freq']:.0f}Hz, "
            f"x_high={result['x_mean_high']:.1f}Ω, slope={x_slope:.2f}"
        )
        return result

    def measure_sweep_features(self) -> Dict:
        """
        スイープ → スペクトル特徴量抽出 ワンショットAPI

        Returns:
            dict: extract_sweep_features() と同じ形式
        """
        sweep = self.sweep_impedance()
        return self.extract_sweep_features(sweep)

    @property
    def last_sweep(self) -> Optional[Dict]:
        """最新のスイープ結果"""
        return self._last_sweep
