"""
DWF Constants - Analog Discovery SDK 定数定義

このファイルはDigilent WaveForms SDKの定数を定義します。
AD3（Analog Discovery 3）のインピーダンス測定に必要な定数が含まれています。
"""

from ctypes import c_int

# ========================================
# デバイス状態
# ========================================

DwfStateReady = c_int(0)
DwfStateConfig = c_int(1)
DwfStatePrefill = c_int(2)
DwfStateArmed = c_int(3)
DwfStateWait = c_int(4)
DwfStateTriggered = c_int(5)
DwfStateRunning = c_int(6)
DwfStateDone = c_int(2)  # 測定完了

# ========================================
# トリガーソース
# ========================================

trigsrcNone = c_int(0)
trigsrcPC = c_int(1)
trigsrcDetectorAnalogIn = c_int(2)
trigsrcDetectorDigitalIn = c_int(3)
trigsrcAnalogIn = c_int(4)
trigsrcDigitalIn = c_int(5)
trigsrcDigitalOut = c_int(6)
trigsrcAnalogOut1 = c_int(7)
trigsrcAnalogOut2 = c_int(8)
trigsrcAnalogOut3 = c_int(9)
trigsrcAnalogOut4 = c_int(10)
trigsrcExternal1 = c_int(11)
trigsrcExternal2 = c_int(12)
trigsrcExternal3 = c_int(13)
trigsrcExternal4 = c_int(14)

# ========================================
# アナログ入力フィルタ
# ========================================

filterDecimate = c_int(0)
filterAverage = c_int(1)
filterMinMax = c_int(2)

# ========================================
# アナログ出力ノード
# ========================================

AnalogOutNodeCarrier = c_int(0)
AnalogOutNodeFM = c_int(1)
AnalogOutNodeAM = c_int(2)

# ========================================
# アナログ出力関数
# ========================================

funcDC = c_int(0)
funcSine = c_int(1)
funcSquare = c_int(2)
funcTriangle = c_int(3)
funcRampUp = c_int(4)
funcRampDown = c_int(5)
funcNoise = c_int(6)
funcPulse = c_int(7)
funcTrapezium = c_int(8)
funcSinePower = c_int(9)
funcCustom = c_int(30)
funcPlay = c_int(31)

# ========================================
# アナログインピーダンスモード
# ========================================

DwfAnalogImpedanceImpedance = c_int(0)
DwfAnalogImpedanceImpedancePhase = c_int(1)
DwfAnalogImpedanceResistance = c_int(2)
DwfAnalogImpedanceReactance = c_int(3)
DwfAnalogImpedanceAdmittance = c_int(4)
DwfAnalogImpedanceAdmittancePhase = c_int(5)
DwfAnalogImpedanceConductance = c_int(6)
DwfAnalogImpedanceSusceptance = c_int(7)
DwfAnalogImpedanceSeriesCapacitance = c_int(8)
DwfAnalogImpedanceParallelCapacitance = c_int(9)
DwfAnalogImpedanceSeriesInductance = c_int(10)
DwfAnalogImpedanceParallelInductance = c_int(11)
DwfAnalogImpedanceDissipation = c_int(12)
DwfAnalogImpedanceQuality = c_int(13)

# ========================================
# インピーダンス測定パラメータ
# ========================================

DwfAnalogImpedanceMeasureImpedance = c_int(1)
DwfAnalogImpedanceMeasureImpedancePhase = c_int(2)
DwfAnalogImpedanceMeasureResistance = c_int(3)
DwfAnalogImpedanceMeasureReactance = c_int(4)
DwfAnalogImpedanceMeasureAdmittance = c_int(5)
DwfAnalogImpedanceMeasureAdmittancePhase = c_int(6)
DwfAnalogImpedanceMeasureConductance = c_int(7)
DwfAnalogImpedanceMeasureSusceptance = c_int(8)
DwfAnalogImpedanceMeasureSeriesCapacitance = c_int(9)
DwfAnalogImpedanceMeasureParallelCapacitance = c_int(10)
DwfAnalogImpedanceMeasureSeriesInductance = c_int(11)
DwfAnalogImpedanceMeasureParallelInductance = c_int(12)
DwfAnalogImpedanceMeasureDissipation = c_int(13)
DwfAnalogImpedanceMeasureQuality = c_int(14)

# ========================================
# エラーコード
# ========================================

dwfercNoErc = c_int(0)
dwfercUnknownError = c_int(1)
dwfercApiLockTimeout = c_int(2)
dwfercAlreadyOpened = c_int(3)
dwfercNotSupported = c_int(4)
dwfercInvalidParameter0 = c_int(16)
dwfercInvalidParameter1 = c_int(17)
dwfercInvalidParameter2 = c_int(18)
dwfercInvalidParameter3 = c_int(19)

# ========================================
# デバイスパラメータ
# ========================================

DwfDeviceParameterUsbPower = c_int(1)
DwfDeviceParameterLedBrightness = c_int(2)
DwfDeviceParameterOnClose = c_int(3)
DwfDeviceParameterAudioOut = c_int(4)
DwfDeviceParameterUsbLimit = c_int(5)

# ========================================
# アナログIO
# ========================================

DwfAnalogIOEnable = c_int(1)
DwfAnalogIOVoltage = c_int(2)
DwfAnalogIOCurrent = c_int(3)
DwfAnalogIOPower = c_int(4)
DwfAnalogIOTemperature = c_int(5)

# ========================================
# デジタルIO
# ========================================

DwfDigitalInClockSourceInternal = c_int(0)
DwfDigitalInClockSourceExternal = c_int(1)

DwfDigitalInSampleModeSimple = c_int(0)
DwfDigitalInSampleModeNoise = c_int(1)

DwfDigitalOutOutputPushPull = c_int(0)
DwfDigitalOutOutputOpenDrain = c_int(1)
DwfDigitalOutOutputOpenSource = c_int(2)
DwfDigitalOutOutputThreeState = c_int(3)

DwfDigitalOutTypePulse = c_int(0)
DwfDigitalOutTypeCustom = c_int(1)
DwfDigitalOutTypeRandom = c_int(2)

DwfDigitalOutIdleInit = c_int(0)
DwfDigitalOutIdleLow = c_int(1)
DfDigitalOutIdleHigh = c_int(2)
DwfDigitalOutIdleZet = c_int(3)

# ========================================
# アナログ入力カップリング
# ========================================

DwfAnalogCouplingDC = c_int(0)
DwfAnalogCouplingAC = c_int(1)

# ========================================
# 取得モード
# ========================================

acqmodeSingle = c_int(0)
acqmodeScanShift = c_int(1)
acqmodeScanScreen = c_int(2)
acqmodeRecord = c_int(3)
acqmodeOvers = c_int(4)
acqmodeSingle1 = c_int(5)

# ========================================
# ウィンドウ関数
# ========================================

DwfWindowRectangular = c_int(0)
DwfWindowTriangular = c_int(1)
DwfWindowHamming = c_int(2)
DwfWindowHann = c_int(3)
DwfWindowCosine = c_int(4)
DwfWindowBlackmanHarris = c_int(5)
DwfWindowFlatTop = c_int(6)
DwfWindowKaiser = c_int(7)
