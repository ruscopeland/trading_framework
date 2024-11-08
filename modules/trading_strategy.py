import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from decimal import Decimal
import json
import numpy as np
from abc import ABC, abstractmethod

from core.base_module import ModuleBase
from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager

class TradingStrategy(ModuleBase, ABC):
    """Base class for trading strategies"""
    
    def __init__(self, module_id: str):
        super().__init__(module_id)
        self.module_name = "Trading Strategy Base"
        self.module_description = "Base class for trading strategies"
        
        # Strategy state
        self._active = False
        self._trading_pairs: List[str] = []
        self._position_sizes: Dict[str, float] = {}
        self._risk_per_trade: float = 0.01  # 1% default
        
        # Performance tracking
        self._trades_history: List[Dict] = []
        self._performance_metrics: Dict[str, float] = {}
        
        # Strategy parameters (to be overridden by specific strategies)
        self.parameters: Dict[str, Any] = {}
        
        # Risk management
        self._max_positions = 3
        self._max_risk_per_pair = 0.05  # 5% default
        self._correlation_threshold = 0.7

    def initialize(self) -> bool:
        """Initialize the strategy"""
        try:
            # Register event handlers
            event_system.subscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
            event_system.subscribe(EventTypes.ORDER_BOOK_UPDATE, self._handle_orderbook_update)
            event_system.subscribe(EventTypes.TRADE_UPDATE, self._handle_trade_update)
            event_system.subscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
            
            # Create strategy window
            self.create_window()
            
            # Load strategy configuration
            self._load_config()
            
            # Initialize strategy-specific components
            self._initialize_strategy()
            
            return True
        except Exception as e:
            self.logger.error(f"Error initializing strategy: {str(e)}")
            return False

    def _setup_window_contents(self):
        """Setup the strategy window contents"""
        with dpg.tab_bar():
            # Strategy Control Tab
            with dpg.tab(label="Control"):
                self._setup_control_panel()
            
            # Strategy Parameters Tab
            with dpg.tab(label="Parameters"):
                self._setup_parameters_panel()
            
            # Performance Tab
            with dpg.tab(label="Performance"):
                self._setup_performance_panel()
            
            # Risk Management Tab
            with dpg.tab(label="Risk Management"):
                self._setup_risk_panel()

    def _setup_control_panel(self):
        """Setup strategy control panel"""
        with dpg.group():
            # Strategy status
            dpg.add_text("Strategy Status")
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Start",
                    callback=self.start_strategy,
                    tag=f"{self.module_id}_start_button"
                )
                dpg.add_button(
                    label="Stop",
                    callback=self.stop_strategy,
                    tag=f"{self.module_id}_stop_button"
                )
            
            dpg.add_text("Inactive", tag=f"{self.module_id}_status")
        
        dpg.add_separator()
        
        # Trading pairs
        with dpg.group():
            dpg.add_text("Trading Pairs")
            dpg.add_listbox(
                items=self._trading_pairs,
                num_items=5,
                callback=self._update_selected_pairs,
                tag=f"{self.module_id}_pairs_list"
            )
        
        dpg.add_separator()
        
        # Current positions
        with dpg.group():
            dpg.add_text("Current Positions")
            dpg.add_table(tag=f"{self.module_id}_positions_table", header_row=True)
            with dpg.table_row():
                dpg.add_table_column(label="Pair")
                dpg.add_table_column(label="Size")
                dpg.add_table_column(label="Entry")
                dpg.add_table_column(label="Current")
                dpg.add_table_column(label="P&L")

    def _setup_parameters_panel(self):
        """Setup strategy parameters panel"""
        with dpg.group():
            dpg.add_text("Strategy Parameters")
            dpg.add_separator()
            
            # Add parameter inputs dynamically based on strategy parameters
            for param_name, param_value in self.parameters.items():
                if isinstance(param_value, bool):
                    dpg.add_checkbox(
                        label=param_name,
                        default_value=param_value,
                        callback=lambda s, a, u: self._update_parameter(u, a),
                        user_data=param_name,
                        tag=f"{self.module_id}_param_{param_name}"
                    )
                elif isinstance(param_value, (int, float)):
                    dpg.add_input_float(
                        label=param_name,
                        default_value=param_value,
                        callback=lambda s, a, u: self._update_parameter(u, a),
                        user_data=param_name,
                        tag=f"{self.module_id}_param_{param_name}"
                    )
                elif isinstance(param_value, str):
                    dpg.add_input_text(
                        label=param_name,
                        default_value=param_value,
                        callback=lambda s, a, u: self._update_parameter(u, a),
                        user_data=param_name,
                        tag=f"{self.module_id}_param_{param_name}"
                    )
            
            dpg.add_button(
                label="Save Parameters",
                callback=self._save_parameters
            )

    def _setup_performance_panel(self):
        """Setup performance monitoring panel"""
        with dpg.group():
            # Performance metrics
            dpg.add_text("Performance Metrics")
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                # Left column
                with dpg.group():
                    dpg.add_text("Total Return: ")
                    dpg.add_text("0.00%", tag=f"{self.module_id}_total_return")
                    dpg.add_text("Win Rate: ")
                    dpg.add_text("0.00%", tag=f"{self.module_id}_win_rate")
                    dpg.add_text("Profit Factor: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_profit_factor")
                
                # Right column
                with dpg.group():
                    dpg.add_text("Sharpe Ratio: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_sharpe_ratio")
                    dpg.add_text("Max Drawdown: ")
                    dpg.add_text("0.00%", tag=f"{self.module_id}_max_drawdown")
                    dpg.add_text("Recovery Factor: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_recovery_factor")
        
        dpg.add_separator()
        
        # Performance chart
        with dpg.plot(
            label="Strategy Performance",
            height=300,
            width=-1,
            tag=f"{self.module_id}_performance_plot"
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Date")
            dpg.add_plot_axis(dpg.mvYAxis, label="Return %")

    def _setup_risk_panel(self):
        """Setup risk management panel"""
        with dpg.group():
            dpg.add_text("Risk Management")
            dpg.add_separator()
            
            # Risk parameters
            dpg.add_input_float(
                label="Risk Per Trade (%)",
                default_value=self._risk_per_trade * 100,
                callback=self._update_risk_settings,
                tag=f"{self.module_id}_risk_per_trade"
            )
            
            dpg.add_input_float(
                label="Max Risk Per Pair (%)",
                default_value=self._max_risk_per_pair * 100,
                callback=self._update_risk_settings,
                tag=f"{self.module_id}_max_risk_per_pair"
            )
            
            dpg.add_input_int(
                label="Max Concurrent Positions",
                default_value=self._max_positions,
                callback=self._update_risk_settings,
                tag=f"{self.module_id}_max_positions"
            )
            
            dpg.add_input_float(
                label="Correlation Threshold",
                default_value=self._correlation_threshold,
                callback=self._update_risk_settings,
                tag=f"{self.module_id}_correlation_threshold"
            )

    @abstractmethod
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        pass

    @abstractmethod
    def _process_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming market data
        Returns signal dict if a trading signal is generated
        """
        pass

    @abstractmethod
    def _generate_order(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate order from trading signal"""
        pass

    def start_strategy(self):
        """Start the strategy"""
        if not self._active:
            self._active = True
            dpg.set_value(f"{self.module_id}_status", "Active")
            self.logger.info("Strategy started")

    def stop_strategy(self):
        """Stop the strategy"""
        if self._active:
            self._active = False
            dpg.set_value(f"{self.module_id}_status", "Inactive")
            self.logger.info("Strategy stopped")

    def _handle_price_update(self, event: Event):
        """Handle price updates"""
        if not self._active:
            return
            
        try:
            # Process data for signals
            signal = self._process_data(event.data)
            
            if signal:
                # Generate and validate order
                order = self._generate_order(signal)
                
                if order and self._validate_order(order):
                    # Submit order
                    event_system.publish(Event(
                        type=EventTypes.ORDER_REQUEST,
                        data=order,
                        source=self.module_id
                    ))
                    
        except Exception as e:
            self.logger.error(f"Error processing price update: {str(e)}")

    def _validate_order(self, order: Dict[str, Any]) -> bool:
        """Validate order against risk management rules"""
        try:
            # Check max positions
            if len(self._position_sizes) >= self._max_positions:
                return False
            
            # Check risk per trade
            account_value = self._get_account_value()
            risk_amount = order.get("risk_amount", 0)
            if risk_amount / account_value > self._risk_per_trade:
                return False
            
            # Check correlation with existing positions
            if not self._check_correlation(order["pair"]):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False

    def _check_correlation(self, pair: str) -> bool:
        """Check correlation with existing positions"""
        try:
            if not self._position_sizes:
                return True
                
            # Get price history for correlation calculation
            prices = {}
            for existing_pair in self._position_sizes.keys():
                prices[existing_pair] = self._get_price_history(existing_pair)
            prices[pair] = self._get_price_history(pair)
            
            # Calculate correlations
            for existing_pair, existing_prices in prices.items():
                if existing_pair == pair:
                    continue
                    
                correlation = np.corrcoef(prices[pair], existing_prices)[0, 1]
                if abs(correlation) > self._correlation_threshold:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking correlation: {str(e)}")
            return False

    def update(self) -> None:
        """Update the module"""
        if self._active:
            self._update_performance_metrics()
            self._update_positions_table()

    def cleanup(self) -> None:
        """Cleanup module resources"""
        self.stop_strategy()
        event_system.unsubscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
        event_system.unsubscribe(EventTypes.ORDER_BOOK_UPDATE, self._handle_orderbook_update)
        event_system.unsubscribe(EventTypes.TRADE_UPDATE, self._handle_trade_update)
        event_system.unsubscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
        self._save_config()

    def get_data(self) -> Dict[str, Any]:
        """Get module data"""
        return {
            "active": self._active,
            "parameters": self.parameters,
            "position_sizes": self._position_sizes,
            "trades_history": self._trades_history,
            "performance_metrics": self._performance_metrics
        } 