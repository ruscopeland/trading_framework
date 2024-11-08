# gui/main_window.py
import dearpygui.dearpygui as dpg
import asyncio
import threading
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import psutil
import os
from pathlib import Path
import json
import time

from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager
from core.data_manager import data_manager
from gui.theme import setup_theme
from modules.market_data_display import MarketDataDisplay
from modules.order_management import OrderManagement
from modules.position_monitor import PositionMonitor
from modules.account_balance import AccountBalance
from modules.strategies.moving_average_cross import MovingAverageCross

class MainWindow:
    def __init__(self):
        self.logger = logging.getLogger("MainWindow")
        self._modules: Dict[str, Any] = {}
        self._active_windows: set = set()
        
        # Window settings
        self.WINDOW_WIDTH = 1600
        self.WINDOW_HEIGHT = 900
        self.MIN_WIDTH = 1200
        self.MIN_HEIGHT = 700

        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "gui_config.json"
        
        # Track orders and positions
        self._open_orders: Dict[str, Any] = {}
        self._positions: Dict[str, Any] = {}
        
        # System monitoring
        self._last_system_update = 0
        self._system_update_interval = 1.0  # seconds

    def setup(self):
        """Initialize Dear PyGui and setup main window"""
        dpg.create_context()
        dpg.create_viewport(
            title="Crypto Trading Framework",
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            min_width=self.MIN_WIDTH,
            min_height=self.MIN_HEIGHT
        )
        
        # Setup theme
        setup_theme()
        
        # Create main window
        with dpg.window(
            label="Main Window",
            tag="main_window",
            no_close=True,
            no_collapse=True,
            no_move=True
        ):
            self._setup_menu_bar()
            self._setup_main_layout()
            
        # Setup handlers
        self._setup_event_handlers()
        
        # Setup viewport
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def _setup_menu_bar(self):
        """Setup main menu bar"""
        with dpg.menu_bar(tag="main_menu_bar"):
            with dpg.menu(label="File"):
                dpg.add_menu_item(
                    label="Save Configuration",
                    callback=self._save_config
                )
                dpg.add_menu_item(
                    label="Load Configuration",
                    callback=self._load_config
                )
                dpg.add_separator()
                dpg.add_menu_item(
                    label="Exit",
                    callback=self._exit_application
                )

            with dpg.menu(label="View"):
                dpg.add_menu_item(
                    label="System Monitor",
                    callback=lambda: self.toggle_window("system_monitor")
                )
                dpg.add_menu_item(
                    label="Error Log",
                    callback=lambda: self.toggle_window("error_log")
                )

            with dpg.menu(label="Modules"):
                self.modules_menu = dpg.add_menu(label="Active Modules")
                dpg.add_separator()
                dpg.add_menu_item(
                    label="Load Module",
                    callback=self._load_module_dialog
                )

    def _setup_main_layout(self):
        """Setup main window layout"""
        with dpg.group(horizontal=True):
            # Left sidebar - Module List and System Status
            with dpg.child_window(
                width=250,
                tag="left_sidebar"
            ):
                dpg.add_text("Active Modules")
                dpg.add_separator()
                dpg.add_child_window(
                    tag="module_list",
                    height=300
                )
                
                dpg.add_separator()
                dpg.add_text("System Status")
                dpg.add_separator()
                with dpg.child_window(
                    tag="system_status",
                    height=200
                ):
                    dpg.add_text("Connection: ", tag="connection_status")
                    dpg.add_text("Active Pairs: ", tag="active_pairs")
                    dpg.add_text("Memory Usage: ", tag="memory_usage")
                    dpg.add_text("CPU Usage: ", tag="cpu_usage")

            # Main content area
            with dpg.child_window(
                tag="main_content",
                border=False
            ):
                # Tabs for different views
                with dpg.tab_bar(tag="main_tabs"):
                    with dpg.tab(label="Market Overview"):
                        self._setup_market_overview()
                    
                    with dpg.tab(label="Trading"):
                        self._setup_trading_view()
                    
                    with dpg.tab(label="Analysis"):
                        self._setup_analysis_view()

    def _setup_market_overview(self):
        """Setup market overview tab"""
        with dpg.group(horizontal=True):
            # Price overview
            with dpg.child_window(
                width=300,
                height=400,
                tag="price_overview"
            ):
                dpg.add_text("Price Overview")
                dpg.add_separator()

            # Charts
            with dpg.child_window(
                tag="chart_area"
            ):
                dpg.add_text("Price Charts")
                dpg.add_separator()

    def _setup_trading_view(self):
        """Setup trading tab"""
        with dpg.group(horizontal=True):
            # Order entry
            with dpg.child_window(
                width=300,
                tag="order_entry"
            ):
                dpg.add_text("Order Entry")
                dpg.add_separator()
                
                dpg.add_combo(
                    label="Trading Pair",
                    tag="trading_pair_selector"
                )
                
                dpg.add_radio_button(
                    label="Order Type",
                    items=["Market", "Limit"],
                    tag="order_type"
                )
                
                dpg.add_input_float(
                    label="Amount",
                    tag="order_amount"
                )
                
                dpg.add_input_float(
                    label="Price",
                    tag="order_price",
                    show=False
                )
                
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Buy",
                        callback=self._place_buy_order,
                        width=100
                    )
                    dpg.add_button(
                        label="Sell",
                        callback=self._place_sell_order,
                        width=100
                    )

            # Active orders and positions
            with dpg.child_window(
                tag="orders_positions"
            ):
                with dpg.tab_bar():
                    with dpg.tab(label="Open Orders"):
                        dpg.add_text("Open Orders")
                        dpg.add_separator()
                        dpg.add_child_window(
                            tag="open_orders_list",
                            height=200
                        )
                    
                    with dpg.tab(label="Positions"):
                        dpg.add_text("Current Positions")
                        dpg.add_separator()
                        dpg.add_child_window(
                            tag="positions_list",
                            height=200
                        )

    def _setup_analysis_view(self):
        """Setup analysis tab"""
        with dpg.group(horizontal=True):
            # Indicator settings
            with dpg.child_window(
                width=300,
                tag="indicator_settings"
            ):
                dpg.add_text("Indicators")
                dpg.add_separator()

            # Analysis results
            with dpg.child_window(
                tag="analysis_results"
            ):
                dpg.add_text("Analysis Results")
                dpg.add_separator()

    def _setup_event_handlers(self):
        """Setup event handlers"""
        event_system.subscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
        event_system.subscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
        event_system.subscribe(EventTypes.MODULE_ERROR, self._handle_error)
        
    def _handle_price_update(self, event: Event):
        """Handle price updates"""
        data = event.data
        pair = data["pair"]
        price = data["ticker"]["price"]
        dpg.set_value(f"price_{pair}", f"{pair}: {price:.2f}")

    def _handle_balance_update(self, event: Event):
        """Handle balance updates"""
        balances = event.data["balances"]
        # Update balance display
        pass

    def _handle_error(self, event: Event):
        """Handle error events"""
        error = event.data["error"]
        self.logger.error(error)
        # Show error in GUI
        pass

    def _save_config(self):
        """Save application configuration"""
        try:
            config = {
                "window": {
                    "width": dpg.get_viewport_width(),
                    "height": dpg.get_viewport_height(),
                },
                "modules": {
                    module_id: module.save_state()
                    for module_id, module in self._modules.items()
                },
                "active_windows": list(self._active_windows),
                "trading": {
                    "selected_pair": dpg.get_value("trading_pair_selector"),
                    "order_type": dpg.get_value("order_type"),
                },
                "layout": self._save_layout_state()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            self.logger.info("Configuration saved successfully")
            dpg.show_item("save_success_popup")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            self._show_error("Save Error", f"Could not save configuration: {str(e)}")

    def _load_config(self):
        """Load application configuration"""
        try:
            if not self.config_file.exists():
                self.logger.info("No configuration file found")
                return
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Apply window settings
            if "window" in config:
                dpg.set_viewport_width(config["window"]["width"])
                dpg.set_viewport_height(config["window"]["height"])
            
            # Load module states
            if "modules" in config:
                for module_id, state in config["modules"].items():
                    if module_id in self._modules:
                        self._modules[module_id].load_state(state)
            
            # Restore active windows
            if "active_windows" in config:
                for window in config["active_windows"]:
                    self.toggle_window(window, show=True)
            
            # Restore trading settings
            if "trading" in config:
                trading = config["trading"]
                if "selected_pair" in trading:
                    dpg.set_value("trading_pair_selector", trading["selected_pair"])
                if "order_type" in trading:
                    dpg.set_value("order_type", trading["order_type"])
            
            # Restore layout
            if "layout" in config:
                self._restore_layout_state(config["layout"])
            
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            self._show_error("Load Error", f"Could not load configuration: {str(e)}")

    def _save_layout_state(self) -> Dict:
        """Save the current layout state"""
        return {
            "left_sidebar_width": dpg.get_item_width("left_sidebar"),
            "tab_selected": dpg.get_value("main_tabs"),
            "window_positions": {
                window: dpg.get_item_pos(window)
                for window in self._active_windows
            }
        }

    def _restore_layout_state(self, layout: Dict):
        """Restore the saved layout state"""
        if "left_sidebar_width" in layout:
            dpg.set_item_width("left_sidebar", layout["left_sidebar_width"])
        
        if "tab_selected" in layout:
            dpg.set_value("main_tabs", layout["tab_selected"])
        
        if "window_positions" in layout:
            for window, pos in layout["window_positions"].items():
                if dpg.does_item_exist(window):
                    dpg.set_item_pos(window, pos)

    async def _place_order(self, side: str):
        """
        Place an order
        Args:
            side: "buy" or "sell"
        """
        try:
            pair = dpg.get_value("trading_pair_selector")
            order_type = dpg.get_value("order_type")
            amount = dpg.get_value("order_amount")
            price = dpg.get_value("order_price") if order_type == "Limit" else None
            
            if not pair or not amount:
                self._show_error("Order Error", "Please fill in all required fields")
                return
            
            # Validate amount
            if amount <= 0:
                self._show_error("Order Error", "Amount must be greater than 0")
                return
            
            # Validate price for limit orders
            if order_type == "Limit" and (not price or price <= 0):
                self._show_error("Order Error", "Invalid price for limit order")
                return
            
            # Get current balance
            balance = state_manager.get_state(f"balance_{pair.split('/')[1]}", 0.0)
            
            # Check if enough balance for buy orders
            if side == "buy":
                required_balance = amount * (price or float(dpg.get_value(f"price_{pair}")))
                if required_balance > balance:
                    self._show_error("Order Error", "Insufficient balance")
                    return
            
            # Create order
            order = {
                "pair": pair,
                "type": order_type.lower(),
                "side": side,
                "amount": amount,
                "price": price if order_type == "Limit" else None
            }
            
            # Send order event
            event_system.publish(Event(
                type=EventTypes.ORDER_REQUEST,
                data=order,
                source="MainWindow"
            ))
            
            # Clear form
            dpg.set_value("order_amount", 0.0)
            if order_type == "Limit":
                dpg.set_value("order_price", 0.0)
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            self._show_error("Order Error", f"Could not place order: {str(e)}")

    def _place_buy_order(self):
        """Place buy order"""
        asyncio.create_task(self._place_order("buy"))

    def _place_sell_order(self):
        """Place sell order"""
        asyncio.create_task(self._place_order("sell"))

    def _update_system_status(self):
        """Update system status information"""
        current_time = time.time()
        if current_time - self._last_system_update < self._system_update_interval:
            return
            
        try:
            # Update connection status
            connection_status = state_manager.get_state("data_manager_status", "unknown")
            dpg.set_value("connection_status", f"Connection: {connection_status}")
            
            # Update active pairs
            active_pairs = data_manager.get_status()["subscribed_pairs"]
            dpg.set_value("active_pairs", f"Active Pairs: {', '.join(active_pairs)}")
            
            # Update system resources
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = process.cpu_percent()
            
            dpg.set_value("memory_usage", f"Memory Usage: {memory_usage:.1f} MB")
            dpg.set_value("cpu_usage", f"CPU Usage: {cpu_usage:.1f}%")
            
            self._last_system_update = current_time
            
        except Exception as e:
            self.logger.error(f"Error updating system status: {str(e)}")

    def _show_error(self, title: str, message: str):
        """Show error popup"""
        with dpg.window(
            label=title,
            modal=True,
            show=True,
            tag="error_popup",
            width=400,
            height=150
        ):
            dpg.add_text(message)
            dpg.add_separator()
            dpg.add_button(
                label="OK",
                callback=lambda: dpg.delete_item("error_popup"),
                width=75
            )

    def _setup_popups(self):
        """Setup popup windows"""
        with dpg.window(
            label="Success",
            modal=True,
            show=False,
            tag="save_success_popup",
            width=200,
            height=100
        ):
            dpg.add_text("Configuration saved successfully")
            dpg.add_button(
                label="OK",
                callback=lambda: dpg.hide_item("save_success_popup"),
                width=75
            )

    def _exit_application(self):
        """Handle application exit"""
        try:
            # Cleanup and stop all modules
            for module in self._modules:
                module.cleanup()
            
            # Stop core systems
            event_system.stop()
            data_manager.stop()
            
            # Stop DPG
            dpg.stop_dearpygui()
            dpg.destroy_context()
            
        except Exception as e:
            self.logger.error(f"Error during application exit: {str(e)}")

    def run(self):
        """Start the main event loop"""
        try:
            # Start update loop
            async def update_loop():
                while dpg.is_dearpygui_running():
                    self._update_system_status()
                    await asyncio.sleep(0.1)
            
            # Run event loop
            loop = asyncio.get_event_loop()
            loop.create_task(update_loop())
            
            dpg.start_dearpygui()
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {str(e)}")
        finally:
            dpg.destroy_context()

    def _load_module_dialog(self):
        """Show dialog for loading a new module"""
        try:
            with dpg.window(
                label="Load Module",
                modal=True,
                show=True,
                tag="load_module_dialog",
                width=400,
                height=300
            ):
                dpg.add_text("Select Module Type:")
                
                # Module types list
                module_types = [
                    "Market Data Display",
                    "Order Management",
                    "Position Monitor",
                    "Account Balance",
                    "Moving Average Cross"
                ]
                
                dpg.add_listbox(
                    items=module_types,
                    tag="module_type_selector",
                    width=-1,
                    num_items=len(module_types)
                )
                
                dpg.add_input_text(
                    label="Module ID",
                    tag="module_id_input",
                    default_value=f"module_{len(self._modules) + 1}"
                )
                
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Load",
                        callback=self._create_new_module
                    )
                    dpg.add_button(
                        label="Cancel",
                        callback=lambda: dpg.delete_item("load_module_dialog")
                    )

        except Exception as e:
            self.logger.error(f"Error showing load module dialog: {str(e)}")
            self._show_error("Error", str(e))

    def _create_new_module(self):
        """Create a new module from the dialog selection"""
        try:
            module_type = dpg.get_value("module_type_selector")
            module_id = dpg.get_value("module_id_input")
            
            # Create the selected module type
            new_module = None
            if module_type == "Market Data Display":
                new_module = MarketDataDisplay(module_id)
            elif module_type == "Order Management":
                new_module = OrderManagement(module_id)
            elif module_type == "Position Monitor":
                new_module = PositionMonitor(module_id)
            elif module_type == "Account Balance":
                new_module = AccountBalance(module_id)
            elif module_type == "Moving Average Cross":
                new_module = MovingAverageCross(module_id)
                
            if new_module and new_module.initialize():
                self._modules.append(new_module)
                self.logger.info(f"Loaded new module: {module_type} ({module_id})")
            else:
                self._show_error("Error", f"Failed to initialize module: {module_type}")
                
            # Close the dialog
            dpg.delete_item("load_module_dialog")
            
        except Exception as e:
            self.logger.error(f"Error creating new module: {str(e)}")
            self._show_error("Error", str(e))

# Create global instance
main_window = MainWindow()