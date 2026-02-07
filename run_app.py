"""
データ収集・学習・推論GUIアプリケーションのエントリーポイント
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.gui.app import TouchEstimationApp

if __name__ == "__main__":
    app = TouchEstimationApp()
    app.mainloop()
