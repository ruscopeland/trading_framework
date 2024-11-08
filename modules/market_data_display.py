import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from core.base_module import ModuleBase
from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager

class MarketDataDisplay(ModuleBase):
    def __init__(self, module_id: str):
        super().__init__(module_id)
        self.module_name = "Market Data Display"
        self.module_description = "Displays real-time market data and order book"
        
        # Cache for market data
        self._price_cache: Dict[str, float] = {}
        self._volume_cache: Dict[str, float] = {}
        self._orderbook_cache: Dict[str, Dict] = {}
        
        # Display settings
        self._orderbook_depth = 10
        self._selected_pair = ""
        self._price_precision = 2
        self._size_precision = 6

    def initialize(self) -> bool:
        """Initialize the module"""
        try:
            # Register event handlers
            event_system.subscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
            event_system.subscribe(EventTypes.ORDER_BOOK_UPDATE, self._handle_orderbook_update)
            event_system.subscribe(EventTypes.TRADE_UPDATE, self._handle_trade_update)
            
            # Create main window
            self.create_window()
            
            return True
        except Exception as e:
            self.logger.error(f"Error initializing MarketDataDisplay: {str(e)}")
            return False

    def _setup_window_contents(self):
        """Setup the module's window contents"""
        # Pair selector
        dpg.add_combo(
            label="Trading Pair",
            items=[],  # Will be populated from config
            callback=self._on_pair_selected,
            tag=f"{self.module_id}_pair_selector"
        )
        
        dpg.add_separator()
        
        # Price and volume display
        with dpg.group(horizontal=True):
            dpg.add_text("Price: ")
            dpg.add_text("0.00", tag=f"{self.module_id}_price")
            dpg.add_text("  Volume: ")
            dpg.add_text("0.00", tag=f"{self.module_id}_volume")
        
        dpg.add_separator()
        
        # Order book display
        with dpg.group(horizontal=True):
            # Bids
            with dpg.child_window(width=200, height=300):
                dpg.add_text("Bids")
                dpg.add_separator()
                dpg.add_table(
                    tag=f"{self.module_id}_bids_table",
                    header_row=True
                )
                with dpg.table_row():
                    dpg.add_table_column(label="Price")
                    dpg.add_table_column(label="Size")
                    dpg.add_table_column(label="Total")
            
            # Asks
            with dpg.child_window(width=200, height=300):
                dpg.add_text("Asks")
                dpg.add_separator()
                dpg.add_table(
                    tag=f"{self.module_id}_asks_table",
                    header_row=True
                )
                with dpg.table_row():
                    dpg.add_table_column(label="Price")
                    dpg.add_table_column(label="Size")
                    dpg.add_table_column(label="Total")
        
        dpg.add_separator()
        
        # Recent trades
        with dpg.child_window(height=150):
            dpg.add_text("Recent Trades")
            dpg.add_separator()
            dpg.add_table(
                tag=f"{self.module_id}_trades_table",
                header_row=True
            )
            with dpg.table_row():
                dpg.add_table_column(label="Time")
                dpg.add_table_column(label="Price")
                dpg.add_table_column(label="Size")
                dpg.add_table_column(label="Side")

    def _handle_price_update(self, event: Event):
        """Handle price updates"""
        data = event.data
        pair = data["pair"]
        
        if pair != self._selected_pair:
            return
            
        price = data["ticker"]["price"]
        volume = data["ticker"]["volume"]
        
        self._price_cache[pair] = price
        self._volume_cache[pair] = volume
        
        # Update display
        dpg.set_value(f"{self.module_id}_price", f"{price:.{self._price_precision}f}")
        dpg.set_value(f"{self.module_id}_volume", f"{volume:.{self._size_precision}f}")

    def _handle_orderbook_update(self, event: Event):
        """Handle order book updates"""
        data = event.data
        pair = data["pair"]
        
        if pair != self._selected_pair:
            return
            
        book = data["book"]
        self._orderbook_cache[pair] = book
        
        # Update bids
        bids = sorted(book["bids"].items(), key=lambda x: float(x[0]), reverse=True)[:self._orderbook_depth]
        total = 0
        dpg.delete_item(f"{self.module_id}_bids_table", children_only=True, slot=1)
        
        for price, size in bids:
            total += size
            with dpg.table_row(parent=f"{self.module_id}_bids_table"):
                dpg.add_text(f"{float(price):.{self._price_precision}f}")
                dpg.add_text(f"{size:.{self._size_precision}f}")
                dpg.add_text(f"{total:.{self._size_precision}f}")
        
        # Update asks
        asks = sorted(book["asks"].items(), key=lambda x: float(x[0]))[:self._orderbook_depth]
        total = 0
        dpg.delete_item(f"{self.module_id}_asks_table", children_only=True, slot=1)
        
        for price, size in asks:
            total += size
            with dpg.table_row(parent=f"{self.module_id}_asks_table"):
                dpg.add_text(f"{float(price):.{self._price_precision}f}")
                dpg.add_text(f"{size:.{self._size_precision}f}")
                dpg.add_text(f"{total:.{self._size_precision}f}")

    def _handle_trade_update(self, event: Event):
        """Handle trade updates"""
        data = event.data
        pair = data["pair"]
        
        if pair != self._selected_pair:
            return
            
        trades = data["trades"]
        
        # Update trades table
        dpg.delete_item(f"{self.module_id}_trades_table", children_only=True, slot=1)
        
        for trade in trades[:10]:  # Show last 10 trades
            with dpg.table_row(parent=f"{self.module_id}_trades_table"):
                trade_time = datetime.fromtimestamp(trade["time"]).strftime("%H:%M:%S")
                dpg.add_text(trade_time)
                dpg.add_text(f"{trade['price']:.{self._price_precision}f}")
                dpg.add_text(f"{trade['volume']:.{self._size_precision}f}")
                dpg.add_text(trade["side"])

    def _on_pair_selected(self, sender, value):
        """Handle pair selection"""
        self._selected_pair = value
        
        # Clear displays
        dpg.set_value(f"{self.module_id}_price", "0.00")
        dpg.set_value(f"{self.module_id}_volume", "0.00")
        dpg.delete_item(f"{self.module_id}_bids_table", children_only=True, slot=1)
        dpg.delete_item(f"{self.module_id}_asks_table", children_only=True, slot=1)
        dpg.delete_item(f"{self.module_id}_trades_table", children_only=True, slot=1)

    def update(self) -> None:
        """Update the module"""
        pass  # Updates are handled by event callbacks

    def cleanup(self) -> None:
        """Cleanup module resources"""
        event_system.unsubscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
        event_system.unsubscribe(EventTypes.ORDER_BOOK_UPDATE, self._handle_orderbook_update)
        event_system.unsubscribe(EventTypes.TRADE_UPDATE, self._handle_trade_update)

    def get_data(self) -> Dict[str, Any]:
        """Get module data"""
        return {
            "price_cache": self._price_cache,
            "volume_cache": self._volume_cache,
            "orderbook_cache": self._orderbook_cache,
            "selected_pair": self._selected_pair
        } 