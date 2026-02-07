"""
実機ハードウェアドライバ - AD3 + Arduino制御

Analog Discovery 3のインピーダンス測定機能と、
Arduinoによるマルチプレクサ制御を統合したドライバです。
"""

import numpy as np
import serial
import time
import logging
from typing import Tuple, Optional

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


class RealHardwareSource(IDataSource):
    """
    実機ハードウェアドライバ
    
    Analog Discovery 3でインピーダンスを測定し、
    Arduinoで2つのマルチプレクサを独立制御します。
    """
    
    def __init__(self):
        """初期化"""
        if not AD3_AVAILABLE:
            raise RuntimeError("AD3 SDK が利用できません。WaveForms SDKをインストールしてください。")
        
        self._connected = False
        self.hdwf = c_int()  # AD3デバイスハンドル
        self.arduino = None  # Arduinoシリアル接続
        
        logger.info("実機ハードウェアドライバを初期化しました")
    
    def connect(self) -> bool:
        """
        AD3とArduinoに接続
        
        Returns:
            bool: 接続成功時True、失敗時False
        """
        try:
            # Arduino接続
            logger.info(f"Arduinoに接続中: {config.ARDUINO_PORT}")
            self.arduino = serial.Serial(
                port=config.ARDUINO_PORT,
                baudrate=config.ARDUINO_BAUDRATE,
                timeout=1.0
            )
            time.sleep(2.0)  # Arduinoのリセット待ち
            logger.info("Arduinoに接続しました")
            
            # AD3接続
            logger.info("Analog Discovery 3に接続中...")
            
            # デバイスを開く
            dwf.FDwfDeviceOpen(c_int(-1), byref(self.hdwf))
            
            if self.hdwf.value == 0:
                logger.error("AD3デバイスが見つかりません")
                self.arduino.close()
                return False
            
            logger.info(f"AD3に接続しました (Handle: {self.hdwf.value})")
            
            # インピーダンスアナライザの初期化
            self._setup_impedance_analyzer()
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            if self.arduino and self.arduino.is_open:
                self.arduino.close()
            return False
    
    def disconnect(self) -> None:
        """AD3とArduinoから切断"""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            logger.info("Arduinoから切断しました")
        
        if self.hdwf.value != 0:
            dwf.FDwfDeviceClose(self.hdwf)
            logger.info("AD3から切断しました")
        
        self._connected = False
    
    def is_connected(self) -> bool:
        """
        接続状態を確認
        
        Returns:
            bool: 接続中の場合True
        """
        return self._connected
    
    def set_ground_truth(self, x: float, y: float) -> None:
        """
        正解位置を設定（実機では無視）
        
        実機では測定のみを行うため、このメソッドは何もしません。
        
        Args:
            x: X座標 [mm] (無視)
            y: Y座標 [mm] (無視)
        """
        # 実機では何もしない
        pass
    
    def get_ground_truth(self) -> Optional[Tuple[float, float]]:
        """
        現在の正解位置を取得（実機では常にNone）
        
        実機では正解位置が不明なため、常にNoneを返します。
        
        Returns:
            None: 実機では正解位置が不明
        """
        return None
    
    def measure_impedance_vector(self) -> np.ndarray:
        """
        全ペアのインピーダンスを測定
        
        Returns:
            np.ndarray: shape=(N_pairs, 2) の配列
                        各行は [Magnitude[Ω], Phase[rad]]
        
        Raises:
            RuntimeError: 測定失敗時
        """
        if not self._connected:
            raise RuntimeError("デバイスが接続されていません")
        
        impedances = []
        
        for pair_id, (source_ch, sink_ch) in enumerate(config.MEASUREMENT_PAIRS):
            # Arduinoにペア選択コマンドを送信
            self._select_pair(source_ch, sink_ch)
            
            # 安定化待ち
            time.sleep(0.05)
            
            # インピーダンス測定
            magnitude, phase = self._measure_single_impedance()
            
            impedances.append([magnitude, phase])
            
            logger.debug(f"Pair {pair_id} ({source_ch}→{sink_ch}): {magnitude:.2f}Ω, {phase:.4f}rad")
        
        impedance_vector = np.array(impedances)
        
        logger.info(f"インピーダンス測定完了: {len(impedances)} pairs")
        
        return impedance_vector
    
    def _select_pair(self, source_ch: int, sink_ch: int) -> None:
        """
        Arduinoにペア選択コマンドを送信
        
        Args:
            source_ch: Source側チャンネル (0-3)
            sink_ch: Sink側チャンネル (0-3)
        """
        # コマンドフォーマット: "S<source_ch>K<sink_ch>\n"
        # 例: "S0K1\n" = Source Ch0, Sink Ch1
        command = f"S{source_ch}K{sink_ch}\n"
        self.arduino.write(command.encode())
        
        # 応答待ち（オプション）
        response = self.arduino.readline().decode().strip()
        logger.debug(f"Arduino応答: {response}")
    
    def _setup_impedance_analyzer(self) -> None:
        """
        AD3のインピーダンスアナライザを設定
        """
        # インピーダンス測定モードを有効化
        dwf.FDwfAnalogImpedanceModeSet(self.hdwf, c_int(8))  # mode 8 = impedance
        
        # リファレンス抵抗を設定（10kΩ）
        dwf.FDwfAnalogImpedanceReferenceSet(self.hdwf, c_double(10000.0))
        
        # 測定周波数を設定
        dwf.FDwfAnalogImpedanceFrequencySet(self.hdwf, c_double(config.MEASUREMENT_FREQUENCY))
        
        # 振幅を設定
        dwf.FDwfAnalogImpedanceAmplitudeSet(self.hdwf, c_double(config.MEASUREMENT_AMPLITUDE))
        
        logger.info(f"インピーダンスアナライザ設定完了: {config.MEASUREMENT_FREQUENCY}Hz, {config.MEASUREMENT_AMPLITUDE}V")
    
    def _measure_single_impedance(self) -> Tuple[float, float]:
        """
        単一ペアのインピーダンスを測定
        
        Returns:
            Tuple[float, float]: (Magnitude[Ω], Phase[rad])
        """
        # 測定開始
        dwf.FDwfAnalogImpedanceConfigure(self.hdwf, c_int(1))
        
        # 測定完了待ち
        sts = c_byte()
        while True:
            dwf.FDwfAnalogImpedanceStatus(self.hdwf, byref(sts))
            if sts.value == 2:  # DwfStateDone
                break
            time.sleep(0.01)
        
        # 結果取得
        resistance = c_double()
        reactance = c_double()
        dwf.FDwfAnalogImpedanceStatusMeasure(self.hdwf, c_int(1), byref(resistance), byref(reactance))
        
        # 複素インピーダンスから振幅と位相を計算
        z_real = resistance.value
        z_imag = reactance.value
        
        magnitude = np.sqrt(z_real**2 + z_imag**2)
        phase = np.arctan2(z_imag, z_real)
        
        return magnitude, phase
    
    def get_device_info(self) -> str:
        """
        デバイス情報を取得
        
        Returns:
            str: デバイス情報の文字列
        """
        if not self._connected:
            return "Real Hardware (Not Connected)"
        
        # AD3のバージョン情報を取得
        version = create_string_buffer(32)
        dwf.FDwfGetVersion(version)
        
        return f"Real Hardware (AD3 SDK: {version.value.decode()}, Arduino: {config.ARDUINO_PORT})"
