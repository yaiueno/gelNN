"""
分類アプリケーションのエントリーポイント
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.gui.app_classifier import ClassifierApp

if __name__ == "__main__":
    app = ClassifierApp()
    app.mainloop()
