import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from decimal import Decimal

from core.base_module import ModuleBase
from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager

class PositionMonitor(ModuleBase):
    def __init__(self, module_id: str):
        super().__init__(module_id)
        self.module_name = "Position Monitor"
        self.module_description = "Monitors and manages trading positions"
        
        # Position tracking
        self._positions: Dict[str, Dict] = {}
        self._pnl_history: List[Dict] = []
        
        # Display settings
        self._price_precision = 2
        self._size_precision = 6
        self._pnl_precision = 2
        
        # Risk metrics
        self._position_alerts: Dict[str, Dict] = {}
        self._risk_levels = {
            "warning": 0.05,  # 5% drawdown
            "danger": 0.10    # 10% drawdown
        }

    def initialize(self) -> bool:
        """Initialize the module"""
        try:
            # Register event handlers
            event_system.subscribe(EventTypes.POSITION_UPDATE, self._handle_position_update)
            event_system.subscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
            event_system.subscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
            
            # Create main window
            self.create_window()
            
            # Initialize position tracking
            self._load_positions()
            
            return True
        except Exception as e:
            self.logger.error(f"Error initializing PositionMonitor: {str(e)}")
            return False

    def _setup_window_contents(self):
        """Setup the module's window contents"""
        with dpg.tab_bar():
            # Active Positions Tab
            with dpg.tab(label="Active Positions"):
                self._setup_positions_view()
            
            # PnL Analysis Tab
            with dpg.tab(label="PnL Analysis"):
                self._setup_pnl_analysis()
            
            # Risk Metrics Tab
            with dpg.tab(label="Risk Metrics"):
                self._setup_risk_metrics()

    def _setup_positions_view(self):
        """Setup positions view"""
        # Summary section
        with dpg.group():
            dpg.add_text("Position Summary")
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_text("Total PnL: ")
                dpg.add_text("0.00", tag=f"{self.module_id}_total_pnl")
                dpg.add_text("  Daily PnL: ")
                dpg.add_text("0.00", tag=f"{self.module_id}_daily_pnl")
        
        dpg.add_separator()
        
        # Positions table
        dpg.add_table(
            tag=f"{self.module_id}_positions_table",
            header_row=True
        )
        with dpg.table_row():
            dpg.add_table_column(label="Pair")
            dpg.add_table_column(label="Size")
            dpg.add_table_column(label="Entry Price")
            dpg.add_table_column(label="Current Price")
            dpg.add_table_column(label="Unrealized PnL")
            dpg.add_table_column(label="Realized PnL")
            dpg.add_table_column(label="Return %")
            dpg.add_table_column(label="Actions")

    def _setup_pnl_analysis(self):
        """Setup PnL analysis view"""
        # Time period selector
        dpg.add_combo(
            label="Time Period",
            items=["Today", "1 Week", "1 Month", "3 Months", "YTD", "All Time"],
            default_value="Today",
            callback=self._update_pnl_analysis,
            tag=f"{self.module_id}_time_period"
        )
        
        dpg.add_separator()
        
        # PnL metrics
        with dpg.group():
            dpg.add_text("PnL Metrics")
            with dpg.group(horizontal=True):
                # Left column
                with dpg.group():
                    dpg.add_text("Total Return: ")
                    dpg.add_text("0.00%", tag=f"{self.module_id}_total_return")
                    dpg.add_text("Win Rate: ")
                    dpg.add_text("0.00%", tag=f"{self.module_id}_win_rate")
                
                # Right column
                with dpg.group():
                    dpg.add_text("Profit Factor: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_profit_factor")
                    dpg.add_text("Sharpe Ratio: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_sharpe_ratio")
        
        dpg.add_separator()
        
        # PnL chart
        with dpg.plot(
            label="PnL History",
            height=300,
            width=-1,
            tag=f"{self.module_id}_pnl_plot"
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Date")
            dpg.add_plot_axis(dpg.mvYAxis, label="PnL")
            
            # Add line series for cumulative PnL
            dpg.add_line_series(
                [],  # x values (dates)
                [],  # y values (PnL)
                label="Cumulative PnL",
                parent=dpg.last_item(),
                tag=f"{self.module_id}_pnl_series"
            )

    def _setup_risk_metrics(self):
        """Setup risk metrics view"""
        # Risk settings
        with dpg.group():
            dpg.add_text("Risk Alert Settings")
            dpg.add_separator()
            
            dpg.add_input_float(
                label="Warning Level (%)",
                default_value=self._risk_levels["warning"] * 100,
                callback=self._update_risk_levels,
                tag=f"{self.module_id}_warning_level"
            )
            
            dpg.add_input_float(
                label="Danger Level (%)",
                default_value=self._risk_levels["danger"] * 100,
                callback=self._update_risk_levels,
                tag=f"{self.module_id}_danger_level"
            )
        
        dpg.add_separator()
        
        # Risk metrics table
        dpg.add_table(
            tag=f"{self.module_id}_risk_table",
            header_row=True
        )
        with dpg.table_row():
            dpg.add_table_column(label="Pair")
            dpg.add_table_column(label="Position Value")
            dpg.add_table_column(label="% of Portfolio")
            dpg.add_table_column(label="Daily Volatility")
            dpg.add_table_column(label="VaR")
            dpg.add_table_column(label="Max Drawdown")
            dpg.add_table_column(label="Risk Level")

    def _handle_position_update(self, event: Event):
        """Handle position updates"""
        try:
            position = event.data
            pair = position["pair"]
            
            # Update position tracking
            self._positions[pair] = position
            
            # Update displays
            self._update_positions_table()
            self._update_risk_metrics()
            self._check_risk_alerts(pair)
            
        except Exception as e:
            self.logger.error(f"Error handling position update: {str(e)}")

    def _handle_price_update(self, event: Event):
        """Handle price updates"""
        try:
            data = event.data
            pair = data["pair"]
            price = data["ticker"]["price"]
            
            if pair in self._positions:
                # Update unrealized PnL
                position = self._positions[pair]
                entry_price = position["entry_price"]
                size = position["size"]
                
                if size > 0:  # Long position
                    pnl = (price - entry_price) * size
                else:  # Short position
                    pnl = (entry_price - price) * abs(size)
                
                position["unrealized_pnl"] = pnl
                position["current_price"] = price
                position["return_pct"] = (pnl / (abs(size) * entry_price)) * 100
                
                # Update displays
                self._update_positions_table()
                self._update_risk_metrics()
                
        except Exception as e:
            self.logger.error(f"Error handling price update: {str(e)}")

    def _update_positions_table(self):
        """Update positions table display"""
        try:
            # Clear existing rows
            dpg.delete_item(f"{self.module_id}_positions_table", children_only=True, slot=1)
            
            total_pnl = 0
            
            # Add position rows
            for pair, position in self._positions.items():
                with dpg.table_row(parent=f"{self.module_id}_positions_table"):
                    dpg.add_text(pair)
                    dpg.add_text(f"{position['size']:.{self._size_precision}f}")
                    dpg.add_text(f"{position['entry_price']:.{self._price_precision}f}")
                    dpg.add_text(f"{position['current_price']:.{self._price_precision}f}")
                    dpg.add_text(f"{position['unrealized_pnl']:.{self._pnl_precision}f}")
                    dpg.add_text(f"{position['realized_pnl']:.{self._pnl_precision}f}")
                    dpg.add_text(f"{position['return_pct']:.2f}%")
                    
                    # Close position button
                    dpg.add_button(
                        label="Close",
                        callback=lambda s, a, u: self._close_position(u),
                        user_data=pair
                    )
                
                total_pnl += position['unrealized_pnl'] + position['realized_pnl']
            
            # Update total PnL
            dpg.set_value(f"{self.module_id}_total_pnl", f"{total_pnl:.{self._pnl_precision}f}")
            
        except Exception as e:
            self.logger.error(f"Error updating positions table: {str(e)}")

    def _close_position(self, pair: str):
        """Request to close a position"""
        try:
            position = self._positions[pair]
            
            # Create market order to close position
            order = {
                "pair": pair,
                "type": "market",
                "side": "sell" if position["size"] > 0 else "buy",
                "size": abs(position["size"])
            }
            
            # Publish order request
            event_system.publish(Event(
                type=EventTypes.ORDER_REQUEST,
                data=order,
                source=self.module_id
            ))
            
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")
            self._show_error("Close Position Error", str(e))

    def update(self) -> None:
        """Update the module"""
        pass  # Updates are handled by event callbacks

    def cleanup(self) -> None:
        """Cleanup module resources"""
        event_system.unsubscribe(EventTypes.POSITION_UPDATE, self._handle_position_update)
        event_system.unsubscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
        event_system.unsubscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)

    def get_data(self) -> Dict[str, Any]:
        """Get module data"""
        return {
            "positions": self._positions,
            "pnl_history": self._pnl_history,
            "risk_levels": self._risk_levels,
            "position_alerts": self._position_alerts
        } 