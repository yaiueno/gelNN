"""
HILS GUIコントローラーのエントリーポイント
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.hils.gui import HILSGUIApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = HILSGUIApp(root)
    root.mainloop()
