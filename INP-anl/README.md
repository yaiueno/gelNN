# ゲルインピーダンス測定・分析ツール

Analog Discovery 3 のインピーダンスアナライザーを用いてゲルを測定し、  
**リリース（非加圧）** と **プレス（加圧）** の差分を可視化します。

## ディレクトリ構成

```
INP-anl/
├── config.py          # 共通設定（周波数範囲・保存先など）
├── measure.py         # 測定スクリプト（AD3 接続 → スイープ → CSV 保存）
├── analyze.py         # 分析スクリプト（統計量算出）
├── plot.py            # グラフ描画（リリース/プレス比較 Bode プロット）
├── diag_ad3.py        # AD3 接続診断スクリプト
├── requirements.txt
├── data/
│   ├── measurement/   # 測定用データ（フル + 測定分割）
│   └── analysis/      # 分析用データ + 統計結果
└── graphs/            # 生成グラフ (PNG)
```

## セットアップ

### 前提条件
- **Digilent WaveForms** がインストール済み（dwf ライブラリを含む）
- Analog Discovery 3 が USB 接続されていること

### Python 依存パッケージ

```bash
pip install -r requirements.txt
```

## 使い方

### 1. 測定

6 回連続測定（1–3 回: リリース、4–6 回: プレス）がデフォルトです。

```bash
# デフォルト設定で 6 回測定
python measure.py

# サンプル名を指定
python measure.py --name pva_gel_5pct

# リリース 3 回、プレス 3 回（デフォルト）
python measure.py --name pva_gel --release 3 --press 3

# リリース 5 回、プレス 5 回に変更
python measure.py --name pva_gel --release 5 --press 5
```

4 回目の測定開始前に「ゲルを押してください」と通知が表示されます。

**測定パラメータ** (config.py で変更可能):

| パラメータ | デフォルト値 |
|-----------|------------|
| 周波数範囲 | 1 kHz – 1 MHz |
| ステップ数 | 100 点 (対数スケール) |
| 基準抵抗 | 1 kΩ |
| 励振振幅 | 1 V |

**CSV ファイル命名規則:**
```
{サンプル名}_{release|press}_r{回番号}_{タイムスタンプ}_full.csv
{サンプル名}_{release|press}_r{回番号}_{タイムスタンプ}_meas.csv
{サンプル名}_{release|press}_r{回番号}_{タイムスタンプ}_anl.csv
```

### 2. 分析

```bash
python analyze.py
python analyze.py --file data/measurement/sample_gel_release_r1_20260217_full.csv
```

### 3. グラフ生成

```bash
# サンプル名を指定してリリース/プレス比較グラフを生成
python plot.py --name sample_gel

# ウィンドウ表示も行う
python plot.py --name sample_gel --show
```

## グラフ化手法

`plot.py` では 4 種類のグラフを自動生成します。

### グラフ 1: リリース全回 Bode プロット
- リリース（非加圧）の各回データを **重ね描き**
- 上段: |Z| vs 周波数（対数-対数スケール）
- 下段: θ vs 周波数（対数-リニアスケール）
- 各回を異なるマーカー＋青系の色で区別

### グラフ 2: プレス全回 Bode プロット
- プレス（加圧）の各回データを **重ね描き**
- 赤系の色パレットで各回を区別
- 加圧時の測定再現性を目視確認

### グラフ 3: リリース vs プレス 比較 Bode プロット
- **平均線**: リリース群・プレス群それぞれの平均を太線で描画
- **標準偏差帯**: `fill_between` で ±1σ の範囲を半透明の帯として表示
- **個別ライン**: 各回の生データを薄い線で背景に描画
- 青系 = リリース、赤系 = プレス

この手法により、加圧による |Z| や θ の変化量と、測定ばらつきの範囲を
一目で比較できます。

### グラフ 4: 差分プロット (Δ)
- **Δ|Z|** = プレス平均 − リリース平均 [Ω]
- **Δθ**  = プレス平均 − リリース平均 [deg]
- ゼロラインを基準線として描画
- 右軸に **変化率 [%]** を併記（Δ|Z| / |Z|_release × 100）
- 周波数ごとの加圧応答の大きさと方向を直接読み取れる

### 描画ライブラリ
- **matplotlib** を使用
- 日本語表示: `MS Gothic` フォント（Windows）
- 対数スケール: `ax.loglog()` / `ax.semilogx()`
- 統計帯: `ax.fill_between()` で ±1σ を可視化
- 出力形式: PNG (150 dpi)

## データ形式 (CSV)

| カラム | 単位 | 説明 |
|--------|------|------|
| `frequency_Hz` | Hz | 測定周波数 |
| `impedance_ohm` | Ω | インピーダンスの絶対値 \|Z\| |
| `phase_deg` | deg | 位相角 θ |
| `resistance_ohm` | Ω | 直列等価抵抗 Rs |
| `reactance_ohm` | Ω | 直列等価リアクタンス Xs |
