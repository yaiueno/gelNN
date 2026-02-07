"""
HILS GUI - イオンゲル可視化・操作ウィンドウ

HILSサーバーに接続し、イオンゲルをクリックしてタッチ位置を送信します。
"""

import asyncio
import websockets
import json
import tkinter as tk
from tkinter import ttk
import threading
import logging
from typing import Optional
import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HILSGUIApp:
    """
    HILS GUI アプリケーション
    
    イオンゲルの可視化とタッチ操作を提供します。
    """
    
    def __init__(self, root):
        """
        初期化
        
        Args:
            root: Tkルートウィンドウ
        """
        self.root = root
        self.root.title("HILS Simulator - Ion Gel Touch")
        self.root.geometry("600x700")
        self.root.configure(bg="#2b2b2b")
        
        # WebSocket接続
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.server_url = config.HILS_SERVER_URL
        
        # タッチ位置
        self.touch_x = 50.0
        self.touch_y = 50.0
        
        # 接続状態
        self.connected = False
        self.client_count = 0
        
        # 非同期イベントループ
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # UI構築
        self._create_widgets()
        
        # サーバー接続を開始
        self._start_connection()
    
    def _create_widgets(self):
        """UIウィジェットを作成"""
        
        # タイトル
        title_label = tk.Label(
            self.root,
            text="HILS Simulator",
            font=("Arial", 20, "bold"),
            bg="#2b2b2b",
            fg="white"
        )
        title_label.pack(pady=10)
        
        # 接続状態表示
        self.status_label = tk.Label(
            self.root,
            text="Status: Disconnected",
            font=("Arial", 12),
            bg="#2b2b2b",
            fg="red"
        )
        self.status_label.pack(pady=5)
        
        # クライアント数表示
        self.client_label = tk.Label(
            self.root,
            text="Clients: 0",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="gray"
        )
        self.client_label.pack(pady=2)
        
        # イオンゲルキャンバス
        canvas_frame = tk.Frame(self.root, bg="#2b2b2b")
        canvas_frame.pack(pady=20)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            width=500,
            height=500,
            bg="#1e1e1e",
            highlightthickness=2,
            highlightbackground="white"
        )
        self.canvas.pack()
        
        # クリックイベント
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # 座標表示
        self.coord_label = tk.Label(
            self.root,
            text=f"Touch: ({self.touch_x:.1f}, {self.touch_y:.1f}) mm",
            font=("Arial", 14),
            bg="#2b2b2b",
            fg="white"
        )
        self.coord_label.pack(pady=10)
        
        # 説明
        info_label = tk.Label(
            self.root,
            text="Click on the ion gel to simulate touch",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="gray"
        )
        info_label.pack(pady=5)
        
        # イオンゲルを描画
        self._draw_gel()
    
    def _draw_gel(self):
        """イオンゲルと端子を描画"""
        # キャンバスをクリア
        self.canvas.delete("all")
        
        # イオンゲル領域
        self.canvas.create_rectangle(
            25, 25, 475, 475,
            fill="#404040",
            outline="white",
            width=2
        )
        
        # グリッド線
        for i in range(1, 10):
            x = 25 + i * 50
            self.canvas.create_line(
                x, 25, x, 475,
                fill="#555555",
                dash=(2, 2)
            )
            
            y = 25 + i * 50
            self.canvas.create_line(
                25, y, 475, y,
                fill="#555555",
                dash=(2, 2)
            )
        
        # 端子を描画
        terminal_pos_canvas = {
            "A": (25, 25),
            "B": (475, 25),
            "C": (475, 475),
            "D": (25, 475)
        }
        
        for name, (cx, cy) in terminal_pos_canvas.items():
            self.canvas.create_oval(
                cx-15, cy-15, cx+15, cy+15,
                fill="#FFD700",
                outline="white",
                width=2
            )
            self.canvas.create_text(
                cx, cy,
                text=name,
                font=("Arial", 12, "bold"),
                fill="black"
            )
        
        # タッチポイントを描画
        self._draw_touch_point()
    
    def _draw_touch_point(self):
        """現在のタッチポイントを描画"""
        # 古いタッチポイントを削除
        self.canvas.delete("touch")
        
        # mm -> canvas座標変換
        canvas_x = 25 + (self.touch_x / config.GEL_WIDTH) * 450
        canvas_y = 25 + (self.touch_y / config.GEL_HEIGHT) * 450
        
        # タッチポイント
        self.canvas.create_oval(
            canvas_x-10, canvas_y-10, canvas_x+10, canvas_y+10,
            fill="#FF0000",
            outline="white",
            width=2,
            tags="touch"
        )
        
        # 十字線
        self.canvas.create_line(
            canvas_x-20, canvas_y, canvas_x+20, canvas_y,
            fill="#FF0000",
            width=2,
            tags="touch"
        )
        self.canvas.create_line(
            canvas_x, canvas_y-20, canvas_x, canvas_y+20,
            fill="#FF0000",
            width=2,
            tags="touch"
        )
    
    def _on_canvas_click(self, event):
        """キャンバスクリック時の処理"""
        # canvas座標 -> mm座標変換
        x_mm = ((event.x - 25) / 450) * config.GEL_WIDTH
        y_mm = ((event.y - 25) / 450) * config.GEL_HEIGHT
        
        # 範囲チェック
        x_mm = max(0, min(config.GEL_WIDTH, x_mm))
        y_mm = max(0, min(config.GEL_HEIGHT, y_mm))
        
        # タッチ位置を設定
        self._set_touch_position(x_mm, y_mm)
    
    def _set_touch_position(self, x: float, y: float):
        """
        タッチ位置を設定してサーバーに送信
        
        Args:
            x: X座標 [mm]
            y: Y座標 [mm]
        """
        self.touch_x = x
        self.touch_y = y
        
        # UI更新
        self.coord_label.config(text=f"Touch: ({x:.1f}, {y:.1f}) mm")
        self._draw_touch_point()
        
        # サーバーに送信（接続中かつループが有効な場合のみ）
        if self.connected and self.websocket and self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._send_touch_to_server(x, y),
                self.loop
            )
    
    async def _send_touch_to_server(self, x: float, y: float):
        """サーバーにタッチ位置を送信"""
        try:
            message = {
                "type": "set_touch",
                "x": x,
                "y": y
            }
            await self.websocket.send(json.dumps(message))
            logger.debug(f"タッチ位置送信: ({x:.2f}, {y:.2f})")
        except Exception as e:
            logger.error(f"送信エラー: {e}")
    
    def _start_connection(self):
        """サーバー接続を開始"""
        # 非同期処理用のスレッドを開始
        thread = threading.Thread(target=self._run_async_loop, daemon=True)
        thread.start()
    
    def _run_async_loop(self):
        """非同期イベントループを実行"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._connect_to_server())
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            self.root.after(0, lambda: self.status_label.config(
                text=f"Status: Error - {str(e)[:30]}",
                fg="red"
            ))
    
    async def _connect_to_server(self):
        """サーバーに接続"""
        try:
            logger.info(f"サーバーに接続中: {self.server_url}")
            
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                self.connected = True
                
                # UI更新
                self.root.after(0, lambda: self.status_label.config(
                    text="Status: Connected",
                    fg="green"
                ))
                
                logger.info("サーバーに接続しました")
                
                # メッセージループ
                async for message in websocket:
                    await self._handle_message(message)
        
        except websockets.exceptions.ConnectionRefused:
            logger.error("サーバーが起動していません")
            self.root.after(0, lambda: self.status_label.config(
                text="Status: Server not running",
                fg="red"
            ))
        except Exception as e:
            logger.error(f"接続失敗: {e}")
            self.root.after(0, lambda: self.status_label.config(
                text=f"Status: Connection Failed",
                fg="red"
            ))
    
    async def _handle_message(self, message: str):
        """サーバーからのメッセージを処理"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "state_update":
                # 状態更新
                touch_pos = data.get("touch_position", [50.0, 50.0])
                client_count = data.get("client_count", 0)
                
                self.client_count = client_count
                
                # UI更新
                self.root.after(0, lambda: self.client_label.config(
                    text=f"Clients: {client_count}"
                ))
            
            elif msg_type == "connected":
                # 接続確認
                server_info = data.get("server_info", "Unknown")
                logger.info(f"サーバー: {server_info}")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")


def main():
    """メイン関数"""
    root = tk.Tk()
    app = HILSGUIApp(root)
    
    logger.info("=" * 60)
    logger.info("HILS GUI起動")
    logger.info(f"サーバー: {config.HILS_SERVER_URL}")
    logger.info("=" * 60)
    
    root.mainloop()


if __name__ == "__main__":
    main()
