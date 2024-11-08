# utils/websocket_client.py

import websockets
import json
import logging
import asyncio
import hmac
import base64
import hashlib
import time
import urllib.parse
from typing import Dict, List, Optional, Callable
from config.config import KRAKEN_API_KEY, KRAKEN_API_SECRET

class KrakenWebsocketClient:
    """
    Kraken WebSocket API v2 client
    Handles WebSocket connection and message routing
    """
    def __init__(self):
        self.logger = logging.getLogger("KrakenWebSocket")
        self.ws = None
        self.running = False
        
        # Callback handlers
        self.on_order_book: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        self.on_ticker: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # WebSocket URLs
        self.ws_public_url = "wss://ws.kraken.com/v2"
        self.ws_private_url = "wss://ws-auth.kraken.com/v2"

        # Private WebSocket connection
        self.ws_private = None
        self.running_private = False
        
        # Additional callback handlers for private data
        self.on_own_trades: Optional[Callable] = None
        self.on_open_orders: Optional[Callable] = None
        self.on_balances: Optional[Callable] = None

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Generate authentication headers for private WebSocket
        Returns:
            Dict with authentication headers
        """
        try:
            nonce = str(int(time.time() * 1000))
            token = base64.b64decode(KRAKEN_API_SECRET)
            
            # Create signature
            signature_message = f"v2/private/subscribe{nonce}"
            signature = hmac.new(
                token,
                signature_message.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            return {
                "API-Key": KRAKEN_API_KEY,
                "API-Sign": signature_b64,
                "API-Nonce": nonce
            }
        except Exception as e:
            self.logger.error(f"Error generating auth headers: {str(e)}")
            raise

    async def connect(self):
        """Connect to Kraken WebSocket"""
        try:
            self.ws = await websockets.connect(self.ws_public_url)
            self.running = True
            asyncio.create_task(self._message_handler())
            self.logger.info("Connected to Kraken WebSocket")
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {str(e)}")
            if self.on_error:
                self.on_error(str(e))
            raise

    async def connect_private(self):
        """Connect to private WebSocket endpoint"""
        try:
            headers = self._get_auth_headers()
            self.ws_private = await websockets.connect(
                self.ws_private_url,
                extra_headers=headers
            )
            self.running_private = True
            asyncio.create_task(self._private_message_handler())
            self.logger.info("Connected to Kraken private WebSocket")
        except Exception as e:
            self.logger.error(f"Private WebSocket connection error: {str(e)}")
            if self.on_error:
                self.on_error(str(e))
            raise

    async def disconnect(self):
        """Disconnect from both public and private WebSockets"""
        self.running = False
        self.running_private = False
        
        if self.ws:
            await self.ws.close()
            self.ws = None
            
        if self.ws_private:
            await self.ws_private.close()
            self.ws_private = None

    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        while self.running and self.ws:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                if "event" in data:
                    await self._handle_event(data)
                else:
                    await self._handle_data(data)
                    
            except websockets.exceptions.ConnectionClosed:
                self.logger.error("WebSocket connection closed")
                break
            except Exception as e:
                self.logger.error(f"Error handling message: {str(e)}")
                if self.on_error:
                    self.on_error(str(e))

    async def _handle_event(self, event: Dict):
        """Handle WebSocket events"""
        if event["event"] == "error":
            self.logger.error(f"WebSocket error event: {event}")
            if self.on_error:
                self.on_error(event["msg"])

    async def _handle_data(self, data: List):
        """Handle WebSocket data messages"""
        try:
            channel = data[1]
            pair = data[2]
            payload = data[3]

            if channel == "book":
                if self.on_order_book:
                    self.on_order_book(pair, payload)
            elif channel == "trade":
                if self.on_trade:
                    self.on_trade(pair, payload)
            elif channel == "ticker":
                if self.on_ticker:
                    self.on_ticker(pair, payload)
                    
        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}")
            if self.on_error:
                self.on_error(str(e))

    async def _private_message_handler(self):
        """Handle incoming private WebSocket messages"""
        while self.running_private and self.ws_private:
            try:
                message = await self.ws_private.recv()
                data = json.loads(message)
                
                if "event" in data:
                    await self._handle_private_event(data)
                else:
                    await self._handle_private_data(data)
                    
            except websockets.exceptions.ConnectionClosed:
                self.logger.error("Private WebSocket connection closed")
                break
            except Exception as e:
                self.logger.error(f"Error handling private message: {str(e)}")
                if self.on_error:
                    self.on_error(str(e))

    async def _handle_private_event(self, event: Dict):
        """Handle private WebSocket events"""
        if event["event"] == "error":
            self.logger.error(f"Private WebSocket error event: {event}")
            if self.on_error:
                self.on_error(event["msg"])
        elif event["event"] == "subscribed":
            self.logger.info(f"Successfully subscribed to private channel: {event}")

    async def _handle_private_data(self, data: List):
        """Handle private WebSocket data messages"""
        try:
            channel = data[1]
            payload = data[2]

            if channel == "owns":
                if self.on_own_trades:
                    self.on_own_trades(payload)
            elif channel == "openOrders":
                if self.on_open_orders:
                    self.on_open_orders(payload)
            elif channel == "balances":
                if self.on_balances:
                    self.on_balances(payload)
                    
        except Exception as e:
            self.logger.error(f"Error processing private data: {str(e)}")
            if self.on_error:
                self.on_error(str(e))

    async def subscribe_public(self, pair: str, channels: List[str]):
        """
        Subscribe to public channels
        Args:
            pair: Trading pair
            channels: List of channels to subscribe to
        """
        message = {
            "event": "subscribe",
            "pair": [pair],
            "subscription": {
                "name": channels
            }
        }
        
        await self.ws.send(json.dumps(message))

    async def subscribe_private(self, channels: List[str]):
        """
        Subscribe to private channels
        Args:
            channels: List of channels to subscribe to
            Available channels:
            - "owns"        (Own Trades)
            - "openOrders" (Open Orders)
            - "balances"   (Account Balance)
        """
        if not self.ws_private:
            await self.connect_private()

        try:
            message = {
                "event": "subscribe",
                "subscription": {
                    "name": channels,
                    "token": KRAKEN_API_KEY
                }
            }
            
            await self.ws_private.send(json.dumps(message))
            self.logger.info(f"Subscribed to private channels: {channels}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to private channels: {str(e)}")
            if self.on_error:
                self.on_error(str(e))
