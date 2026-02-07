"""
HILSサーバーのエントリーポイント
"""

import sys
import os
import asyncio

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.hils.server import HILSServer

if __name__ == "__main__":
    server = HILSServer()
    asyncio.run(server.start())
