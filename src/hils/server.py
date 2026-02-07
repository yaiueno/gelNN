"""
HILSサーバー - WebSocketベースのシミュレータサーバー

複数のクライアント（GUI、アプリ）からの接続を受け付け、
タッチ位置の管理とインピーダンス計算を提供します。
"""

import asyncio
import websockets
import json
import numpy as np
import logging
from datetime import datetime
from typing import Set, Dict, Optional
from src.utils import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HILSServer:
    """
    HILS WebSocketサーバー
    
    タッチ位置の状態管理とインピーダンス計算を行います。
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        初期化
        
        Args:
            host: サーバーのホスト名
            port: サーバーのポート番号
        """
        self.host = host
        self.port = port
        
        # 接続中のクライアント
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # 現在のタッチ位置
        self.touch_x: float = 50.0  # デフォルト中央
        self.touch_y: float = 50.0
        
        # 端子位置
        self.terminal_positions = config.TERMINAL_POSITIONS
        
        logger.info(f"HILSサーバーを初期化: {host}:{port}")
    
    async def start(self):
        """サーバーを起動"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"HILSサーバー起動: ws://{self.host}:{self.port}")
            await asyncio.Future()  # 永続的に実行
    
    async def handle_client(self, websocket):
        """
        クライアント接続のハンドラ
        
        Args:
            websocket: WebSocketコネクション
        """
        # クライアントを登録
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"クライアント接続: {client_addr}")
        
        try:
            # 初期状態を送信
            await self.send_state_update(websocket)
            
            # メッセージループ
            async for message in websocket:
                await self.handle_message(websocket, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"クライアント切断: {client_addr}")
        
        finally:
            # クライアントを削除
            self.clients.remove(websocket)
            logger.info(f"クライアント数: {len(self.clients)}")
    
    async def handle_message(self, websocket, message: str):
        """
        クライアントからのメッセージを処理
        
        Args:
            websocket: 送信元のWebSocket
            message: JSONメッセージ
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "set_touch":
                # タッチ位置を設定
                x = float(data.get("x", 50.0))
                y = float(data.get("y", 50.0))
                await self.set_touch_position(x, y)
            
            elif msg_type == "measure_impedance":
                # インピーダンス測定
                request_id = data.get("request_id", "")
                impedance_vector = self.calculate_impedance(self.touch_x, self.touch_y)
                
                response = {
                    "type": "impedance_response",
                    "request_id": request_id,
                    "impedance_vector": impedance_vector.tolist(),
                    "ground_truth": [self.touch_x, self.touch_y],
                    "timestamp": datetime.now().timestamp()
                }
                
                await websocket.send(json.dumps(response))
            
            elif msg_type == "get_state":
                # 現在の状態を取得
                await self.send_state_update(websocket)
            
            elif msg_type == "connect":
                # 接続確認
                client_id = data.get("client_id", "unknown")
                logger.info(f"クライアント識別: {client_id}")
                
                response = {
                    "type": "connected",
                    "server_info": "HILS Server v1.0",
                    "timestamp": datetime.now().timestamp()
                }
                await websocket.send(json.dumps(response))
            
            else:
                logger.warning(f"不明なメッセージタイプ: {msg_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
    
    async def set_touch_position(self, x: float, y: float):
        """
        タッチ位置を設定し、全クライアントに通知
        
        Args:
            x: X座標 [mm]
            y: Y座標 [mm]
        """
        self.touch_x = x
        self.touch_y = y
        
        logger.debug(f"タッチ位置更新: ({x:.2f}, {y:.2f}) mm")
        
        # 全クライアントに状態を配信
        await self.broadcast_state()
    
    async def send_state_update(self, websocket):
        """
        特定のクライアントに状態を送信
        
        Args:
            websocket: 送信先のWebSocket
        """
        state = {
            "type": "state_update",
            "touch_position": [self.touch_x, self.touch_y],
            "client_count": len(self.clients),
            "timestamp": datetime.now().timestamp()
        }
        
        await websocket.send(json.dumps(state))
    
    async def broadcast_state(self):
        """全クライアントに状態を配信"""
        if not self.clients:
            return
        
        state = {
            "type": "state_update",
            "touch_position": [self.touch_x, self.touch_y],
            "client_count": len(self.clients),
            "timestamp": datetime.now().timestamp()
        }
        
        message = json.dumps(state)
        
        # 全クライアントに送信
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )
    
    def calculate_impedance(self, x: float, y: float) -> np.ndarray:
        """
        インピーダンスを計算
        
        simulator.py のロジックを移植
        
        Args:
            x: タッチX座標 [mm]
            y: タッチY座標 [mm]
        
        Returns:
            np.ndarray: shape=(N_pairs, 2) のインピーダンスベクトル
        """
        touch_pos = np.array([x, y])
        impedances = []
        
        for source_ch, sink_ch in config.MEASUREMENT_PAIRS:
            # 端子名を取得
            source_name = config.TERMINAL_NAMES[source_ch]
            sink_name = config.TERMINAL_NAMES[sink_ch]
            
            # 端子位置
            source_pos = np.array(self.terminal_positions[source_name])
            sink_pos = np.array(self.terminal_positions[sink_name])
            
            # インピーダンス計算
            magnitude = self._calculate_single_impedance(touch_pos, source_pos, sink_pos)
            
            # 位相はランダム
            phase = np.random.uniform(-np.pi/4, np.pi/4)
            
            impedances.append([magnitude, phase])
        
        return np.array(impedances)
    
    def _calculate_single_impedance(self,
                                    touch_pos: np.ndarray,
                                    source_pos: np.ndarray,
                                    sink_pos: np.ndarray) -> float:
        """
        単一ペアのインピーダンスを計算
        
        Args:
            touch_pos: タッチ位置
            source_pos: Source端子位置
            sink_pos: Sink端子位置
        
        Returns:
            float: インピーダンス振幅 [Ω]
        """
        # Source-Sink間の直線経路からの距離
        line_vec = sink_pos - source_pos
        line_length = np.linalg.norm(line_vec)
        
        if line_length < 1e-6:
            distance = np.linalg.norm(touch_pos - source_pos)
        else:
            # 線分への距離
            t = np.dot(touch_pos - source_pos, line_vec) / (line_length ** 2)
            t = np.clip(t, 0, 1)
            closest_point = source_pos + t * line_vec
            distance = np.linalg.norm(touch_pos - closest_point)
        
        # 2つの端子からの直接距離も考慮
        dist_source = np.linalg.norm(touch_pos - source_pos)
        dist_sink = np.linalg.norm(touch_pos - sink_pos)
        min_terminal_dist = min(dist_source, dist_sink)
        
        # ハイブリッド距離
        effective_dist = distance * 0.7 + min_terminal_dist * 0.3
        
        # 指数的変化
        decay_constant = 30.0
        impedance_change = config.DISTANCE_FACTOR * 100.0 * (1.0 - np.exp(-effective_dist / decay_constant))
        impedance = config.BASE_IMPEDANCE + impedance_change
        
        # ノイズ付加
        noise = np.random.normal(0, config.NOISE_LEVEL * impedance)
        impedance += noise
        
        return max(impedance, 100.0)


async def main():
    """メイン関数"""
    # config から設定を読み込む
    host = getattr(config, 'HILS_SERVER_HOST', 'localhost')
    port = getattr(config, 'HILS_SERVER_PORT', 8765)
    
    server = HILSServer(host=host, port=port)
    
    logger.info("=" * 60)
    logger.info("HILS WebSocketサーバー")
    logger.info("=" * 60)
    logger.info(f"アドレス: ws://{host}:{port}")
    logger.info("Ctrl+C で停止")
    logger.info("=" * 60)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("サーバーを停止します")


if __name__ == "__main__":
    asyncio.run(main())
