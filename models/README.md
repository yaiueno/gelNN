# Models Directory

このディレクトリには、学習済みの機械学習モデルが保存されます。

## ファイル

- `model.pkl`: 学習済みMLPRegressorモデル
- `scaler.pkl`: 特徴量正規化用のStandardScaler

## モデル仕様

**入力:**
- 6ペア × 2 (Magnitude, Phase) = 12次元の特徴ベクトル

**出力:**
- 2次元 (X, Y) のタッチ位置 [mm]

**アーキテクチャ:**
- 入力層: 12ノード
- 隠れ層: 64ノード → 32ノード (デフォルト、`config.py`で変更可能)
- 出力層: 2ノード

## モデルのロード

```python
import pickle

# モデルをロード
with open('models/model.pkl', 'rb') as f:
    model = pickle.load(f)

# スケーラーをロード
with open('models/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# 推論
import numpy as np
impedance_vector = np.array([[1000, 0.1], [1200, 0.2], ...])  # 6ペア
X = impedance_vector.flatten().reshape(1, -1)
X_scaled = scaler.transform(X)
prediction = model.predict(X_scaled)[0]
print(f"Estimated position: ({prediction[0]:.1f}, {prediction[1]:.1f}) mm")
```

## 再学習

GUIアプリケーションの "Train Model" ボタンをクリックすると、このディレクトリのモデルが上書きされます。
