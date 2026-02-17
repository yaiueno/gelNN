"""
エントリポイント - 単一端子押圧検出アプリ（学習 & 判定）

AD3 単体（Arduino不要）で 1ペアのインピーダンスを測定し、
NNモデルで押圧の有無をリアルタイム判定します。

Usage:
    python run.py
"""

from src.gui.app_single_terminal import main

if __name__ == "__main__":
    main()
