# Data Directory

このディレクトリには、データ収集時に取得したインピーダンス測定データが保存されます。

## ファイル形式

- `training_data_YYYYMMDD_HHMMSS.pkl`: Pickle形式の学習データ
  - `MeasurementResult` オブジェクトのリスト
  - 各オブジェクトには以下が含まれます：
    - `impedance_vector`: インピーダンスベクトル (N_pairs × 2)
    - `ground_truth`: 正解位置 (x, y) [mm]
    - `timestamp`: タイムスタンプ

## 使用方法

GUIアプリケーション (`app.py`) でデータ収集を行うと、自動的にこのディレクトリに保存されます。

## データのロード

```python
import pickle

with open('data/training_data_20260207_153000.pkl', 'rb') as f:
    training_data = pickle.load(f)

for result in training_data:
    print(f"Position: {result.ground_truth}")
    print(f"Impedance: {result.impedance_vector}")
```
