# Ion Gel Touch Position Estimation System

イオンゲルのタッチ位置をインピーダンス測定から推定するシステムです。HILS（Hardware-In-the-Loop Simulation）と実機を設定変更で切り替え可能です。

## 🚀 クイックスタート

### HILSモード（シミュレータ）で試す

```cmd
# 全システムを一括起動
01_start_hils_full_system.bat
```

これだけで、以下の3つのウィンドウが立ち上がります：
1. **HILS Server** - バックエンドサーバー
2. **HILS Controller** - タッチ位置操作GUI
3. **Classifier App** - 判定結果表示GUI

---

## 📦 バッチファイル一覧

すべての機能は、わかりやすいバッチファイルから起動できます：

| バッチファイル | 用途 | 所要時間 | 対象モード |
|---------------|------|---------|-----------|
| **01_start_hils_full_system.bat** | HILSフルシステム起動 | - | HILS |
| **02_data_collection_and_training.bat** | データ収集・学習・推論 | 10～30分 | HILS/実機 |
| **03_frequency_analysis_hils.bat** | 周波数分析（HILS） | 5～10分 | HILS |
| **04_frequency_analysis_real.bat** | 周波数分析（実機） | 10～30分 | 実機 |
| **05_train_classifier_model.bat** | モデル学習（バッチ） | 5～15分 | HILS/実機 |
| **06_run_automated_test.bat** | 自動テスト | 5～10分 | HILS/実機 |
| **07_classifier_app_only.bat** | 分類器単独起動 | - | HILS |

📘 **詳細な使い方**: [USAGE_GUIDE.md](USAGE_GUIDE.md) を参照してください。

---

## ✨ 特徴

- **デュアルMUX構成**: CD4051 x2 で任意の端子ペアを選択可能
- **HILS/実機切り替え**: 設定ファイル1行でシームレスに切り替え
- **サーバー・クライアント分離**: WebSocketによる分散アーキテクチャ
- **Strategyパターン**: 抽象インターフェースで実装を分離
- **モダンGUI**: customtkinter による直感的な操作
- **機械学習**: MLPRegressorと分類器で位置推定
- **周波数最適化**: 自動周波数分析ツール搭載
- **リアルタイム検証**: 確率ヒートマップとメトリクス表示

---

## 🏗️ システム構成

### 実機モード

```
┌─────────────┐
│   PC        │
│  (Python)   │
└──────┬──────┘
       │ USB
       ├────────────┐
       │            │
┌──────▼──────┐ ┌──▼─────────┐
│  Arduino    │ │    AD3     │
│    Uno      │ │ (Impedance)│
└──────┬──────┘ └──┬─────┬───┘
       │           │     │
    GPIO(6本)   W1+1+  1-+GND
       │           │     │
    ┌──▼───────────▼─────▼──┐
    │  CD4051 x2 (Dual MUX) │
    └──────────┬─────────────┘
               │
        ┌──────▼──────┐
        │  Ion Gel    │
        │ (A, B, C, D)│
        └─────────────┘
```

### HILSモード

```
HILS GUI Controller → WebSocket → HILS Server ← WebSocket ← Classifier App
    (タッチ操作)                  (シミュレーション)              (結果表示)
```

---

## 📁 プロジェクト構造

```
gelNN/
├── 01_start_hils_full_system.bat       # HILSフルシステム起動
├── 02_data_collection_and_training.bat # データ収集・学習
├── 03_frequency_analysis_hils.bat      # 周波数分析（HILS）
├── 04_frequency_analysis_real.bat      # 周波数分析（実機）
├── 05_train_classifier_model.bat       # モデル学習（バッチ）
├── 06_run_automated_test.bat           # 自動テスト
├── 07_classifier_app_only.bat          # 分類器単独起動
│
├── run_app.py                          # アプリ起動エントリーポイント
├── run_classifier.py                   # 分類器起動エントリーポイント
├── run_hils_server.py                  # HILSサーバー起動
├── run_hils_gui.py                     # HILS GUI起動
│
├── src/                                # ソースコードディレクトリ
│   ├── core/                           # コアロジック
│   │   ├── interfaces.py               # IDataSource, MeasurementResult
│   │   ├── factory.py                  # DataSourceFactory
│   │   └── models/
│   │       └── classifier.py           # TouchClassifier
│   ├── hardware/                       # ハードウェア層
│   │   ├── hardware.py                 # RealHardwareSource
│   │   └── dwfconstants.py             # AD3定数
│   ├── hils/                           # HILSシステム
│   │   ├── simulator.py                # HILSSimulatorSource
│   │   ├── server.py                   # HILSServer (WebSocket)
│   │   ├── client.py                   # HILSClientSource
│   │   └── gui.py                      # HILS操作GUI
│   ├── gui/                            # GUIアプリケーション
│   │   ├── app.py                      # データ収集・学習・推論GUI
│   │   └── app_classifier.py           # 分類器GUI
│   └── utils/                          # ユーティリティ
│       ├── config.py                   # 設定ファイル
│       └── frequency_analyzer.py       # 周波数分析ツール
│
├── scripts/                            # 実行スクリプト
│   ├── train.py                        # 学習スクリプト
│   └── test_auto.py                    # 自動テストスクリプト
│
├── arduino/                            # Arduino用コード
│   └── mux_controller/
│       └── mux_controller.ino
│
├── data/                               # データファイル
├── models/                             # 学習済みモデル
├── logs/                               # ログファイル
│
├── USAGE_GUIDE.md                      # 使い方ガイド（詳細）
├── STRUCTURE.md                        # アーキテクチャ詳細
└── README.md                           # このファイル
```

---

## 🔧 セットアップ

### 前提条件

- Python 3.8以上
- pip

### インストール手順

1. **リポジトリをクローン**

```bash
git clone <repository-url>
cd gelNN
```

2. **依存パッケージをインストール**

```bash
pip install -r requirements.txt
```

必要なパッケージ：
- `customtkinter` - モダンGUI
- `numpy` - 数値計算
- `scikit-learn` - 機械学習
- `pyserial` - Arduino通信
- `websockets` - WebSocket通信（HILS用）

3. **実機使用の場合のみ: AD3 SDKをインストール**

[Digilent WaveForms](https://digilent.com/shop/software/digilent-waveforms/) をダウンロード・インストール

4. **実機使用の場合のみ: Arduinoプログラムを書き込み**

Arduino IDEで `arduino/mux_controller/mux_controller.ino` を開き、Arduino Unoに書き込み

5. **設定ファイルを編集**

`src\utils\config.py` を開き、使用モードを選択：

```python
# HILSモード（シミュレータ）
USE_REAL_HARDWARE = False
USE_HILS_SERVER = True

# 実機モード
USE_REAL_HARDWARE = True
ARDUINO_PORT = "COM3"  # 環境に応じて変更
```

---

## 📖 使い方

### 推奨ワークフロー

#### 初めて使う場合（HILSモード）

1. **システム動作確認**（5分）
   ```cmd
   01_start_hils_full_system.bat
   ```
   - HILS Controllerでクリック
   - Classifier Appで結果確認

2. **データ収集・学習**（15分）
   ```cmd
   02_data_collection_and_training.bat
   ```
   - 複数位置でデータ収集
   - モデル学習
   - 推論テスト

3. **性能評価**（10分）
   ```cmd
   06_run_automated_test.bat
   ```
   - 自動テストで精度確認

#### 実機で使う場合

1. **設定変更**
   `src\utils\config.py`:
   ```python
   USE_REAL_HARDWARE = True
   ```

2. **周波数分析**（30分）
   ```cmd
   04_frequency_analysis_real.bat
   ```

3. **データ収集・学習**（30分）
   ```cmd
   02_data_collection_and_training.bat
   ```

### 各機能の詳細

すべての機能は番号付きバッチファイルから起動できます。

📘 **詳細な使い方**: [USAGE_GUIDE.md](USAGE_GUIDE.md) を参照してください。

各バッチファイルの説明：
- **01**: HILSフルシステム起動（サーバー+GUI+分類器）
- **02**: データ収集・学習・推論GUI
- **03**: 周波数分析（HILS）
- **04**: 周波数分析（実機）
- **05**: モデル学習（バッチ処理）
- **06**: 自動テスト
- **07**: 分類器単独起動

---

## 🐛 トラブルシューティング

### よくある問題

**バッチファイルが起動しない**
```bash
pip install -r requirements.txt
python --version  # Python 3.8以上を確認
```

**HILS Serverに接続できない**
- ポート8765が使用中でないか確認
- `src\utils\config.py` の設定確認
- ファイアウォール設定確認

**実機が認識されない**
- AD3とArduinoの接続を確認
- デバイスマネージャーでCOMポート確認
- `src\utils\config.py` の `ARDUINO_PORT` を修正

**推論精度が低い**
- データ量を増やす（100サンプル以上）
- 周波数分析で最適周波数を決定
- グリッド全体に均等にデータを配置

📘 **詳細なトラブルシューティング**: [USAGE_GUIDE.md](USAGE_GUIDE.md#トラブルシューティング) を参照

---

## 📚 詳細ドキュメント

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - 各バッチファイルの詳細な使い方
- **[STRUCTURE.md](STRUCTURE.md)** - システムアーキテクチャと設計
- **[REFACTORING.md](REFACTORING.md)** - リファクタリング履歴

---

## 🎯 今後の拡張

- [ ] より高度な機械学習モデル（CNN、RNN）
- [ ] リアルタイム軌跡追跡
- [ ] マルチタッチ対応
- [ ] Webベースインターフェース

---

## 📄 ライセンス

MIT License

## 👥 作成者

Ion Gel Touch Estimation Project Team

---

**最終更新**: 2026年2月8日
