"""
HILSクライアント - WebSocket経由でサーバーに接続

サーバーモードのHILSシミュレータと通信します。
"""

import asyncio
import websockets
import json
import numpy as np
import logging
import threading
import uuid
from typing import Optional
from queue import Queue

from interfaces import IDataSource
import config

logger = logging.getLogger(__name__)


class HILSClientSource(IDataSource):
    """
    HILSクライアント - WebSocket経由でサーバーに接続
    
    既存のIDataSourceインターフェースを実装し、
    サーバーベースのHILSシミュレータとして動作します。
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """
        初期化
        
        Args:
            server_url: サーバーURL（デフォルトはconfig から読み込み）
        """
        self.server_url = server_url or config.HILS_SERVER_URL
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        
        # 非同期処理用
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        
        # レスポンス待ち用のキュー
        self.response_queue = Queue()
        
        # キャッシュ用
        self._latest_touch_x = 50.0
        self._latest_touch_y = 50.0
        
        logger.info(f"HILSクライアントを初期化: {self.server_url}")
    
    def connect(self) -> bool:
        """
        サーバーに接続
        
        Returns:
            bool: 接続成功時True
        """
        try:
            # 非同期処理用のスレッドを開始
            self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self.thread.start()
            
            # 接続完了を待機（タイムアウト5秒）
            import time
            timeout = 5.0
            start_time = time.time()
            
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self._connected:
                logger.info("HILSサーバーに接続しました")
                return True
            else:
                logger.error("HILSサーバーへの接続がタイムアウトしました")
                return False
        
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            return False
    
    def disconnect(self) -> None:
        """サーバーから切断"""
        self._connected = False
        
        if self.websocket:
            # WebSocketを閉じる（非同期）
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.close(),
                    self.loop
                )
        
        logger.info("HILSサーバーから切断しました")
    
    def is_connected(self) -> bool:
        """
        接続状態を確認
        
        Returns:
            bool: 接続中の場合True
        """
        return self._connected
    
    def set_ground_truth(self, x: float, y: float) -> None:
        """
        正解位置を設定（サーバーに送信）
        
        Args:
            x: X座標 [mm]
            y: Y座標 [mm]
        """
        if not self._connected or not self.loop:
            logger.warning("サーバーに未接続です")
            return
        
        # 非同期でサーバーに送信
        asyncio.run_coroutine_threadsafe(
            self._send_set_touch(x, y),
            self.loop
        )
        
        logger.debug(f"正解位置を設定: ({x:.2f}, {y:.2f}) mm")
    
    def get_ground_truth(self) -> Optional[tuple[float, float]]:
        """
        現在の正解位置を取得（サーバーから取得）
        
        Returns:
            Optional[tuple[float, float]]: (x, y) [mm]
        """
        if not self._connected or not self.loop:
            return None
        
        # リクエストIDを生成
        request_id = str(uuid.uuid4())
        
        # 非同期でサーバーに状態リクエスト
        asyncio.run_coroutine_threadsafe(
            self._send_get_state_request(request_id),
            self.loop
        )
        
        # レスポンスを待機（タイムアウト1秒）
        try:
            # 専用のキューを用意するか、既存のキューを共有するか検討が必要だが、
            # 簡易的に既存キューを使用し、タイプで判断する
            # ただし、measure_impedanceと競合する可能性があるため、
            # ここではシンプルに最新のキャッシュされた値を返す実装を検討すべきだが
            # IDataSourceの仕様上、能動的に取得する
            
            # 注意: ここではレスポンス待ちの実装が複雑になるため、
            # 内部変数にキャッシュされた最新のタッチ位置を返すようにする
            # _handle_messageでstate_updateを受け取って更新する
            return (self._latest_touch_x, self._latest_touch_y)
            
        except Exception as e:
            logger.error(f"正解位置取得エラー: {e}")
            return None

    def measure_impedance_vector(self) -> np.ndarray:
        """
        インピーダンスを測定（サーバーから取得）
        
        Returns:
            np.ndarray: shape=(N_pairs, 2) のインピーダンスベクトル
        
        Raises:
            RuntimeError: 未接続時または測定失敗時
        """
        if not self._connected or not self.loop:
            raise RuntimeError("サーバーに未接続です")
        
        # リクエストIDを生成
        request_id = str(uuid.uuid4())
        
        # 非同期でサーバーにリクエスト
        future = asyncio.run_coroutine_threadsafe(
            self._send_measure_request(request_id),
            self.loop
        )
        
        # レスポンスを待機（タイムアウト3秒）
        try:
            result = self.response_queue.get(timeout=3.0)
            
            if result.get("request_id") == request_id:
                impedance_list = result.get("impedance_vector", [])
                
                # 正解位置も更新しておく
                if "ground_truth" in result:
                    gt = result["ground_truth"]
                    self._latest_touch_x = gt[0]
                    self._latest_touch_y = gt[1]
                
                return np.array(impedance_list)
            else:
                # 異なるIDのレスポンスが来た場合（古いのが残っていたなど）
                # もう一度待ってみる（簡易的なリトライ）
                try:
                    result = self.response_queue.get(timeout=1.0)
                    if result.get("request_id") == request_id:
                        impedance_list = result.get("impedance_vector", [])
                        return np.array(impedance_list)
                except:
                    pass
                
                raise RuntimeError("レスポンスのリクエストIDが一致しません")
        
        except Exception as e:
            raise RuntimeError(f"インピーダンス測定失敗: {e}")
    
    def get_device_info(self) -> str:
        """
        デバイス情報を取得
        
        Returns:
            str: デバイス情報の文字列
        """
        return f"HILS Client (Server: {self.server_url})"
    
    def _run_event_loop(self):
        """非同期イベントループを実行"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._connect_to_server())
        except Exception as e:
            logger.error(f"イベントループエラー: {e}")
        finally:
            self.loop.close()
    
    async def _connect_to_server(self):
        """サーバーに接続してメッセージループを開始"""
        try:
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                self._connected = True
                
                logger.info(f"サーバーに接続: {self.server_url}")
                
                # 接続メッセージを送信
                await self._send_connect_message()
                
                # メッセージ受信ループ
                async for message in websocket:
                    await self._handle_message(message)
        
        except Exception as e:
            logger.error(f"サーバー接続エラー: {e}")
            self._connected = False
    
    async def _send_connect_message(self):
        """接続メッセージを送信"""
        message = {
            "type": "connect",
            "client_id": f"client_{uuid.uuid4().hex[:8]}"
        }
        await self.websocket.send(json.dumps(message))
    
    async def _send_set_touch(self, x: float, y: float):
        """タッチ位置設定メッセージを送信"""
        message = {
            "type": "set_touch",
            "x": x,
            "y": y
        }
        await self.websocket.send(json.dumps(message))
    
    async def _send_measure_request(self, request_id: str):
        """インピーダンス測定リクエストを送信"""
        message = {
            "type": "measure_impedance",
            "request_id": request_id
        }
        await self.websocket.send(json.dumps(message))
    
    async def _send_get_state_request(self, request_id: str):
        """状態取得リクエストを送信"""
        message = {
            "type": "get_state",
            "request_id": request_id
        }
        await self.websocket.send(json.dumps(message))
    
    async def _handle_message(self, message: str):
        """サーバーからのメッセージを処理"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "impedance_response":
                # インピーダンスレスポンスをキューに追加
                self.response_queue.put(data)
            
            elif msg_type == "state_update":
                # 状態更新
                touch_pos = data.get("touch_position")
                if touch_pos:
                    self._latest_touch_x = touch_pos[0]
                    self._latest_touch_y = touch_pos[1]
            
            elif msg_type == "connected":
                # 接続確認
                server_info = data.get("server_info", "Unknown")
                logger.info(f"サーバー情報: {server_info}")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
