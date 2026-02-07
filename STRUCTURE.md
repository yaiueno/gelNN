# プロジェクト構造図

```
gelNN/
│
├── src/                           # ソースコードディレクトリ
│   ├── __init__.py               # パッケージ初期化
│   │
│   ├── core/                     # ✅ コアビジネスロジック
│   │   ├── __init__.py
│   │   ├── interfaces.py         # IDataSource, MeasurementResult
│   │   ├── factory.py            # DataSourceFactory
│   │   └── models/
│   │       ├── __init__.py
│   │       └── classifier.py     # TouchClassifier
│   │
│   ├── hardware/                 # 🔧 ハードウェア層
│   │   ├── __init__.py
│   │   ├── hardware.py           # RealHardwareSource (AD3+Arduino)
│   │   └── dwfconstants.py       # AD3 SDK定数
│   │
│   ├── hils/                     # 🎮 HILSシミュレーション
│   │   ├── __init__.py
│   │   ├── simulator.py          # HILSSimulatorSource（ローカル）
│   │   ├── server.py             # HILSServer（WebSocket）
│   │   ├── client.py             # HILSClientSource
│   │   └── gui.py                # HILS操作GUI
│   │
│   ├── gui/                      # 🖥️ GUIアプリケーション
│   │   ├── __init__.py
│   │   ├── app.py                # データ収集・学習・推論GUI
│   │   └── app_classifier.py     # 9点分類器GUI
│   │
│   └── utils/                    # 🛠️ ユーティリティ
│       ├── __init__.py
│       ├── config.py             # システム設定
│       └── frequency_analyzer.py # 周波数分析ツール
│
├── scripts/                      # 📜 実行スクリプト
│   ├── train.py                  # 学習スクリプト
│   └── test_auto.py              # 自動テストスクリプト
│
├── logs/                         # 📝 ログファイル
│   └── test_log_*.txt
│
├── data/                         # 💾 データファイル
│   └── README.md
│
├── models/                       # 🧠 学習済みモデル
│   ├── grid_positions.json
│   └── README.md
│
├── arduino/                      # 🤖 Arduino用コード
│   └── mux_controller/
│       └── mux_controller.ino
│
├── run_app.py                   # ▶️ アプリ起動
├── run_classifier.py            # ▶️ 分類器起動
├── run_hils_server.py           # ▶️ HILSサーバー起動
├── run_hils_gui.py              # ▶️ HILS GUI起動
│
├── start_full_hils_system.bat   # 🚀 HILSフルシステム起動
├── start_hils_classifier.bat    # 🚀 分類器起動
│
├── requirements.txt              # 📦 依存パッケージ
├── README.md                     # 📖 プロジェクト説明
└── REFACTORING.md               # 📋 リファクタリング報告
```

## 📊 モジュール依存関係

```
┌─────────────────────────────────────────────┐
│              エントリーポイント               │
│  run_app.py, run_classifier.py, etc.        │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────┐              ┌────▼─────┐
│  GUI   │              │ scripts  │
│ モジュール │              │  モジュール  │
└───┬────┘              └────┬─────┘
    │                        │
    └────────┬───────────────┘
             │
        ┌────▼─────┐
        │   core   │ ◄──────┐
        │ モジュール  │         │
        └────┬─────┘         │
             │               │
    ┌────────┴────────┐      │
    │                 │      │
┌───▼────┐      ┌────▼─────┐│
│  HILS  │      │ hardware ││
│モジュール│      │ モジュール  ││
└───┬────┘      └────┬─────┘│
    │                │      │
    └────────┬────────┘      │
             │               │
        ┌────▼─────┐         │
        │  utils   ├─────────┘
        │ モジュール  │
        └──────────┘
```

## 🔑 各モジュールの役割

| モジュール | 責務 | 主要クラス/関数 |
|----------|------|---------------|
| **core** | ビジネスロジック、抽象化 | IDataSource, DataSourceFactory, TouchClassifier |
| **hardware** | 実機制御 | RealHardwareSource |
| **hils** | シミュレーション | HILSSimulatorSource, HILSServer, HILSClientSource |
| **gui** | ユーザーインターフェース | TouchEstimationApp, ClassifierApp |
| **utils** | 共通機能、設定 | config, FrequencyAnalyzer |
| **scripts** | 実行スクリプト | train, test_auto |

## 🎯 設計原則

1. **関心の分離 (Separation of Concerns)**
   - 各モジュールは明確な責務を持つ
   - GUI、ビジネスロジック、ハードウェア制御を分離

2. **依存性の逆転 (Dependency Inversion)**
   - IDataSourceインターフェースによる抽象化
   - 実装（HILS/実機）の切り替えが容易

3. **単一責任の原則 (Single Responsibility)**
   - 各ファイルは1つの目的に集中
   - モジュールごとに独立したテストが可能

4. **開放閉鎖の原則 (Open-Closed)**
   - 新しいデータソースの追加が容易
   - 既存コードを変更せずに拡張可能
