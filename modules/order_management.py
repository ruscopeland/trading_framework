import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from decimal import Decimal

from core.base_module import ModuleBase
from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager

class OrderManagement(ModuleBase):
    def __init__(self, module_id: str):
        super().__init__(module_id)
        self.module_name = "Order Management"
        self.module_description = "Manages order entry and active orders"
        
        # Order tracking
        self._open_orders: Dict[str, Dict] = {}
        self._order_history: List[Dict] = []
        
        # Trading settings
        self._trading_pairs: List[str] = []
        self._selected_pair = ""
        self._price_precision = 2
        self._size_precision = 6
        
        # Risk management
        self._max_position_size: Dict[str, float] = {}
        self._max_order_size: Dict[str, float] = {}
        self._price_deviation_limit = 0.05  # 5% default

    def initialize(self) -> bool:
        """Initialize the module"""
        try:
            # Register event handlers
            event_system.subscribe(EventTypes.ORDER_UPDATE, self._handle_order_update)
            event_system.subscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
            event_system.subscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
            
            # Create main window
            self.create_window()
            
            # Load trading pairs from config
            self._load_trading_pairs()
            
            # Load risk settings
            self._load_risk_settings()
            
            return True
        except Exception as e:
            self.logger.error(f"Error initializing OrderManagement: {str(e)}")
            return False

    def _setup_window_contents(self):
        """Setup the module's window contents"""
        with dpg.tab_bar():
            # Order Entry Tab
            with dpg.tab(label="Order Entry"):
                self._setup_order_entry()
            
            # Open Orders Tab
            with dpg.tab(label="Open Orders"):
                self._setup_open_orders()
            
            # Order History Tab
            with dpg.tab(label="Order History"):
                self._setup_order_history()
            
            # Settings Tab
            with dpg.tab(label="Settings"):
                self._setup_settings()

    def _setup_order_entry(self):
        """Setup order entry interface"""
        # Trading pair selector
        dpg.add_combo(
            label="Trading Pair",
            items=self._trading_pairs,
            callback=self._on_pair_selected,
            tag=f"{self.module_id}_pair_selector"
        )
        
        dpg.add_separator()
        
        # Market Data Display
        with dpg.group(horizontal=True):
            dpg.add_text("Best Bid: ")
            dpg.add_text("0.00", tag=f"{self.module_id}_best_bid")
            dpg.add_text("  Best Ask: ")
            dpg.add_text("0.00", tag=f"{self.module_id}_best_ask")
        
        dpg.add_separator()
        
        # Order Type Selection
        dpg.add_radio_button(
            label="Order Type",
            items=["Market", "Limit", "Stop-Limit"],
            callback=self._on_order_type_changed,
            horizontal=True,
            tag=f"{self.module_id}_order_type"
        )
        
        # Order Parameters
        with dpg.group():
            # Size input
            dpg.add_input_float(
                label="Size",
                callback=self._validate_order_size,
                tag=f"{self.module_id}_order_size"
            )
            
            # Price inputs (for limit orders)
            dpg.add_input_float(
                label="Limit Price",
                show=False,
                callback=self._validate_price,
                tag=f"{self.module_id}_limit_price"
            )
            
            # Stop price input (for stop-limit orders)
            dpg.add_input_float(
                label="Stop Price",
                show=False,
                callback=self._validate_price,
                tag=f"{self.module_id}_stop_price"
            )
        
        dpg.add_separator()
        
        # Order Buttons
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Buy",
                callback=self._place_buy_order,
                tag=f"{self.module_id}_buy_button"
            )
            dpg.add_button(
                label="Sell",
                callback=self._place_sell_order,
                tag=f"{self.module_id}_sell_button"
            )
        
        # Order Preview
        dpg.add_separator()
        dpg.add_text("Order Preview", tag=f"{self.module_id}_preview_label")
        with dpg.group(tag=f"{self.module_id}_preview_group"):
            dpg.add_text("Type: ", tag=f"{self.module_id}_preview_type")
            dpg.add_text("Size: ", tag=f"{self.module_id}_preview_size")
            dpg.add_text("Price: ", tag=f"{self.module_id}_preview_price")
            dpg.add_text("Total: ", tag=f"{self.module_id}_preview_total")

    def _setup_open_orders(self):
        """Setup open orders display"""
        dpg.add_table(
            tag=f"{self.module_id}_open_orders_table",
            header_row=True
        )
        with dpg.table_row():
            dpg.add_table_column(label="Time")
            dpg.add_table_column(label="Pair")
            dpg.add_table_column(label="Type")
            dpg.add_table_column(label="Side")
            dpg.add_table_column(label="Price")
            dpg.add_table_column(label="Size")
            dpg.add_table_column(label="Filled")
            dpg.add_table_column(label="Status")
            dpg.add_table_column(label="Actions")

    def _setup_order_history(self):
        """Setup order history display"""
        dpg.add_table(
            tag=f"{self.module_id}_order_history_table",
            header_row=True
        )
        with dpg.table_row():
            dpg.add_table_column(label="Time")
            dpg.add_table_column(label="Pair")
            dpg.add_table_column(label="Type")
            dpg.add_table_column(label="Side")
            dpg.add_table_column(label="Price")
            dpg.add_table_column(label="Size")
            dpg.add_table_column(label="Status")
            dpg.add_table_column(label="Details")

    def _setup_settings(self):
        """Setup trading settings"""
        dpg.add_text("Risk Management")
        dpg.add_separator()
        
        # Position size limits
        dpg.add_input_float(
            label="Max Position Size (%)",
            default_value=100.0,
            callback=self._update_risk_settings,
            tag=f"{self.module_id}_max_position_pct"
        )
        
        # Order size limits
        dpg.add_input_float(
            label="Max Order Size (%)",
            default_value=50.0,
            callback=self._update_risk_settings,
            tag=f"{self.module_id}_max_order_pct"
        )
        
        # Price deviation limit
        dpg.add_input_float(
            label="Max Price Deviation (%)",
            default_value=5.0,
            callback=self._update_risk_settings,
            tag=f"{self.module_id}_price_deviation"
        )

    def _validate_order_size(self, sender, value):
        """Validate order size input"""
        try:
            if not self._selected_pair:
                return
            
            # Check against max order size
            max_size = self._max_order_size.get(self._selected_pair, float('inf'))
            if value > max_size:
                dpg.set_value(sender, max_size)
                self._show_warning(f"Maximum order size is {max_size}")
            
            self._update_preview()
            
        except Exception as e:
            self.logger.error(f"Error validating order size: {str(e)}")

    def _validate_price(self, sender, value):
        """Validate price input"""
        try:
            if not self._selected_pair:
                return
            
            current_price = float(dpg.get_value(f"{self.module_id}_best_ask"))
            deviation = abs(value - current_price) / current_price
            
            if deviation > self._price_deviation_limit:
                dpg.set_value(sender, current_price)
                self._show_warning(f"Price deviation exceeds {self._price_deviation_limit*100}%")
            
            self._update_preview()
            
        except Exception as e:
            self.logger.error(f"Error validating price: {str(e)}")

    def _update_preview(self):
        """Update order preview"""
        try:
            order_type = dpg.get_value(f"{self.module_id}_order_type")
            size = dpg.get_value(f"{self.module_id}_order_size")
            
            if order_type == "Market":
                price = float(dpg.get_value(f"{self.module_id}_best_ask"))
            else:
                price = dpg.get_value(f"{self.module_id}_limit_price")
            
            total = size * price
            
            dpg.set_value(f"{self.module_id}_preview_type", f"Type: {order_type}")
            dpg.set_value(f"{self.module_id}_preview_size", f"Size: {size:.{self._size_precision}f}")
            dpg.set_value(f"{self.module_id}_preview_price", f"Price: {price:.{self._price_precision}f}")
            dpg.set_value(f"{self.module_id}_preview_total", f"Total: {total:.{self._price_precision}f}")
            
        except Exception as e:
            self.logger.error(f"Error updating preview: {str(e)}")

    def _place_order(self, side: str):
        """Place an order"""
        try:
            if not self._selected_pair:
                self._show_warning("Please select a trading pair")
                return
            
            order_type = dpg.get_value(f"{self.module_id}_order_type")
            size = dpg.get_value(f"{self.module_id}_order_size")
            
            if size <= 0:
                self._show_warning("Invalid order size")
                return
            
            order = {
                "pair": self._selected_pair,
                "type": order_type.lower(),
                "side": side,
                "size": size
            }
            
            if order_type != "Market":
                price = dpg.get_value(f"{self.module_id}_limit_price")
                if price <= 0:
                    self._show_warning("Invalid price")
                    return
                order["price"] = price
            
            if order_type == "Stop-Limit":
                stop_price = dpg.get_value(f"{self.module_id}_stop_price")
                if stop_price <= 0:
                    self._show_warning("Invalid stop price")
                    return
                order["stop_price"] = stop_price
            
            # Publish order request
            event_system.publish(Event(
                type=EventTypes.ORDER_REQUEST,
                data=order,
                source=self.module_id
            ))
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            self._show_error("Order Error", str(e))

    def _place_buy_order(self):
        """Place buy order"""
        self._place_order("buy")

    def _place_sell_order(self):
        """Place sell order"""
        self._place_order("sell")

    def _handle_order_update(self, event: Event):
        """Handle order updates"""
        try:
            order = event.data
            order_id = order["order_id"]
            
            if order["status"] == "open":
                self._open_orders[order_id] = order
                self._update_open_orders_table()
            elif order["status"] in ["filled", "cancelled", "expired"]:
                if order_id in self._open_orders:
                    del self._open_orders[order_id]
                self._order_history.append(order)
                self._update_open_orders_table()
                self._update_order_history_table()
                
        except Exception as e:
            self.logger.error(f"Error handling order update: {str(e)}")

    def update(self) -> None:
        """Update the module"""
        pass  # Updates are handled by event callbacks

    def cleanup(self) -> None:
        """Cleanup module resources"""
        event_system.unsubscribe(EventTypes.ORDER_UPDATE, self._handle_order_update)
        event_system.unsubscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
        event_system.unsubscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)

    def get_data(self) -> Dict[str, Any]:
        """Get module data"""
        return {
            "open_orders": self._open_orders,
            "order_history": self._order_history,
            "selected_pair": self._selected_pair,
            "risk_settings": {
                "max_position_size": self._max_position_size,
                "max_order_size": self._max_order_size,
                "price_deviation_limit": self._price_deviation_limit
            }
        } 