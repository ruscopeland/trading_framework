# core/data_manager.py
from typing import Dict, List, Any, Optional, Set, Callable
import asyncio
import logging
from datetime import datetime
import json
from decimal import Decimal
import threading

from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager
from utils.websocket_client import KrakenWebsocketClient

class DataManager:
    """
    Manages market data and WebSocket connections
    Handles data distribution and caching
    """
    def __init__(self):
        self.logger = logging.getLogger("DataManager")
        self._ws_client: Optional[KrakenWebsocketClient] = None
        self._running = False
        self._lock = threading.RLock()
        
        # Data caches
        self._order_books: Dict[str, Dict] = {}
        self._latest_trades: Dict[str, List] = {}
        self._ticker_data: Dict[str, Dict] = {}
        
        # Subscription management
        self._subscribed_pairs: Set[str] = set()
        self._subscription_callbacks: Dict[str, Set[Callable]] = {}
        
        # Initialize state
        self._initialize_state()

    def _initialize_state(self):
        """Initialize state entries"""
        state_manager.set_state(
            "data_manager_status",
            "initialized",
            "DataManager",
            persistent=False
        )

    async def start(self, pairs: List[str]):
        """
        Start the data manager
        Args:
            pairs: List of trading pairs to subscribe to
        """
        if self._running:
            return

        self._running = True
        self._ws_client = KrakenWebsocketClient()
        
        # Register WebSocket callbacks
        self._ws_client.on_order_book = self._handle_order_book
        self._ws_client.on_trade = self._handle_trade
        self._ws_client.on_ticker = self._handle_ticker
        self._ws_client.on_error = self._handle_error
        
        try:
            await self._ws_client.connect()
            state_manager.set_state(
                "data_manager_status",
                "connected",
                "DataManager",
                persistent=False
            )
            
            # Subscribe to pairs
            for pair in pairs:
                await self._subscribe_pair(pair)
                
        except Exception as e:
            self.logger.error(f"Error starting data manager: {str(e)}")
            state_manager.set_state(
                "data_manager_status",
                f"error: {str(e)}",
                "DataManager",
                persistent=False
            )

    async def stop(self):
        """Stop the data manager"""
        if not self._running:
            return

        self._running = False
        if self._ws_client:
            await self._ws_client.disconnect()
            self._ws_client = None
            
        state_manager.set_state(
            "data_manager_status",
            "stopped",
            "DataManager",
            persistent=False
        )

    async def _subscribe_pair(self, pair: str):
        """
        Subscribe to a trading pair
        Args:
            pair: Trading pair to subscribe to
        """
        if pair in self._subscribed_pairs:
            return

        try:
            await self._ws_client.subscribe_public(pair, [
                "book",
                "trade",
                "ticker"
            ])
            self._subscribed_pairs.add(pair)
            
            # Initialize caches
            self._order_books[pair] = {"bids": {}, "asks": {}}
            self._latest_trades[pair] = []
            self._ticker_data[pair] = {}
            
        except Exception as e:
            self.logger.error(f"Error subscribing to {pair}: {str(e)}")

    def _handle_order_book(self, pair: str, data: Dict):
        """Handle order book updates"""
        with self._lock:
            # Update order book cache
            book = self._order_books[pair]
            for side in ["bids", "asks"]:
                if side in data:
                    for price, volume, _ in data[side]:
                        if float(volume) == 0:
                            book[side].pop(price, None)
                        else:
                            book[side][price] = float(volume)

            # Publish event
            event_system.publish(Event(
                type=EventTypes.ORDER_BOOK_UPDATE,
                data={
                    "pair": pair,
                    "book": book,
                    "timestamp": datetime.utcnow()
                },
                source="DataManager"
            ))

    def _handle_trade(self, pair: str, data: List):
        """Handle trade updates"""
        with self._lock:
            # Update trade cache
            trades = [
                {
                    "price": float(trade[0]),
                    "volume": float(trade[1]),
                    "time": float(trade[2]),
                    "side": trade[3],
                    "type": trade[4]
                }
                for trade in data
            ]
            
            self._latest_trades[pair].extend(trades)
            self._latest_trades[pair] = self._latest_trades[pair][-1000:]  # Keep last 1000 trades

            # Publish event
            event_system.publish(Event(
                type=EventTypes.TRADE_UPDATE,
                data={
                    "pair": pair,
                    "trades": trades,
                    "timestamp": datetime.utcnow()
                },
                source="DataManager"
            ))

    def _handle_ticker(self, pair: str, data: Dict):
        """Handle ticker updates"""
        with self._lock:
            # Update ticker cache
            self._ticker_data[pair] = {
                "price": float(data["c"][0]),
                "volume": float(data["v"][1]),
                "vwap": float(data["p"][1]),
                "trades": int(data["t"][1]),
                "low": float(data["l"][1]),
                "high": float(data["h"][1]),
                "open": float(data["o"][1])
            }

            # Publish event
            event_system.publish(Event(
                type=EventTypes.PRICE_UPDATE,
                data={
                    "pair": pair,
                    "ticker": self._ticker_data[pair],
                    "timestamp": datetime.utcnow()
                },
                source="DataManager"
            ))

    def _handle_error(self, error: str):
        """Handle WebSocket errors"""
        self.logger.error(f"WebSocket error: {error}")
        event_system.publish(Event(
            type=EventTypes.MODULE_ERROR,
            data={
                "module": "DataManager",
                "error": error,
                "timestamp": datetime.utcnow()
            },
            source="DataManager"
        ))

    def get_order_book(self, pair: str) -> Optional[Dict]:
        """Get current order book for a pair"""
        with self._lock:
            return self._order_books.get(pair)

    def get_latest_trades(self, pair: str, limit: int = 100) -> List[Dict]:
        """Get latest trades for a pair"""
        with self._lock:
            trades = self._latest_trades.get(pair, [])
            return trades[-limit:]

    def get_ticker(self, pair: str) -> Optional[Dict]:
        """Get current ticker data for a pair"""
        with self._lock:
            return self._ticker_data.get(pair)

    def get_status(self) -> Dict[str, Any]:
        """Get data manager status"""
        return {
            "running": self._running,
            "subscribed_pairs": list(self._subscribed_pairs),
            "connection_status": "connected" if self._ws_client else "disconnected",
            "cache_sizes": {
                "order_books": len(self._order_books),
                "trades": sum(len(trades) for trades in self._latest_trades.values()),
                "tickers": len(self._ticker_data)
            }
        }

    async def start_private(self):
        """Start private data subscriptions"""
        try:
            await self._ws_client.connect_private()
            
            # Register private callbacks
            self._ws_client.on_own_trades = self._handle_own_trades
            self._ws_client.on_open_orders = self._handle_open_orders
            self._ws_client.on_balances = self._handle_balances
            
            # Subscribe to private channels
            await self._ws_client.subscribe_private([
                "owns",
                "openOrders",
                "balances"
            ])
            
        except Exception as e:
            self.logger.error(f"Error starting private data: {str(e)}")
            state_manager.set_state(
                "private_data_status",
                f"error: {str(e)}",
                "DataManager",
                persistent=False
            )

    def _handle_own_trades(self, data: Dict):
        """Handle own trades updates"""
        event_system.publish(Event(
            type=EventTypes.OWN_TRADES_UPDATE,
            data={
                "trades": data,
                "timestamp": datetime.utcnow()
            },
            source="DataManager"
        ))

    def _handle_open_orders(self, data: Dict):
        """Handle open orders updates"""
        event_system.publish(Event(
            type=EventTypes.OPEN_ORDERS_UPDATE,
            data={
                "orders": data,
                "timestamp": datetime.utcnow()
            },
            source="DataManager"
        ))

    def _handle_balances(self, data: Dict):
        """Handle balance updates"""
        event_system.publish(Event(
            type=EventTypes.BALANCE_UPDATE,
            data={
                "balances": data,
                "timestamp": datetime.utcnow()
            },
            source="DataManager"
        ))

# Global data manager instance
data_manager = DataManager()