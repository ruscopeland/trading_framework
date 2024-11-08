import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from decimal import Decimal
import json

from core.base_module import ModuleBase
from core.event_system import event_system, Event, EventTypes
from core.state_manager import state_manager

class AccountBalance(ModuleBase):
    def __init__(self, module_id: str):
        super().__init__(module_id)
        self.module_name = "Account Balance"
        self.module_description = "Monitors account balances and equity"
        
        # Balance tracking
        self._balances: Dict[str, float] = {}
        self._equity_history: List[Dict] = []
        self._balance_history: Dict[str, List[Dict]] = {}
        
        # Display settings
        self._value_precision = 8  # For crypto amounts
        self._fiat_precision = 2   # For fiat values
        
        # Tracking settings
        self._track_interval = 3600  # 1 hour in seconds
        self._last_track_time = 0
        self._base_currency = "USD"  # For value calculations

    def initialize(self) -> bool:
        """Initialize the module"""
        try:
            # Register event handlers
            event_system.subscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
            event_system.subscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
            
            # Create main window
            self.create_window()
            
            # Load historical data
            self._load_history()
            
            return True
        except Exception as e:
            self.logger.error(f"Error initializing AccountBalance: {str(e)}")
            return False

    def _setup_window_contents(self):
        """Setup the module's window contents"""
        with dpg.tab_bar():
            # Current Balances Tab
            with dpg.tab(label="Current Balances"):
                self._setup_current_balances()
            
            # Balance History Tab
            with dpg.tab(label="Balance History"):
                self._setup_balance_history()
            
            # Portfolio Analysis Tab
            with dpg.tab(label="Portfolio Analysis"):
                self._setup_portfolio_analysis()

    def _setup_current_balances(self):
        """Setup current balances view"""
        # Total Equity Display
        with dpg.group():
            dpg.add_text("Total Equity")
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_text("Total Value (USD): ")
                dpg.add_text("0.00", tag=f"{self.module_id}_total_value")
                dpg.add_text("  24h Change: ")
                dpg.add_text("0.00%", tag=f"{self.module_id}_24h_change")
        
        dpg.add_separator()
        
        # Balances Table
        dpg.add_table(
            tag=f"{self.module_id}_balances_table",
            header_row=True
        )
        with dpg.table_row():
            dpg.add_table_column(label="Asset")
            dpg.add_table_column(label="Available")
            dpg.add_table_column(label="In Orders")
            dpg.add_table_column(label="Total")
            dpg.add_table_column(label="Value (USD)")
            dpg.add_table_column(label="% of Portfolio")

    def _setup_balance_history(self):
        """Setup balance history view"""
        # Time period selector
        dpg.add_combo(
            label="Time Period",
            items=["24 Hours", "7 Days", "30 Days", "90 Days", "YTD", "All Time"],
            default_value="7 Days",
            callback=self._update_history_view,
            tag=f"{self.module_id}_time_period"
        )
        
        dpg.add_separator()
        
        # Balance history chart
        with dpg.plot(
            label="Balance History",
            height=300,
            width=-1,
            tag=f"{self.module_id}_balance_plot"
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Date")
            dpg.add_plot_axis(dpg.mvYAxis, label="Value (USD)")
            
            # Line series will be added dynamically

    def _setup_portfolio_analysis(self):
        """Setup portfolio analysis view"""
        # Asset allocation chart
        with dpg.plot(
            label="Asset Allocation",
            height=200,
            width=300,
            tag=f"{self.module_id}_allocation_plot"
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True)
            dpg.add_plot_axis(dpg.mvYAxis, no_tick_labels=True)
        
        dpg.add_separator()
        
        # Portfolio metrics
        with dpg.group():
            dpg.add_text("Portfolio Metrics")
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                # Left column
                with dpg.group():
                    dpg.add_text("Total Assets: ")
                    dpg.add_text("0", tag=f"{self.module_id}_total_assets")
                    dpg.add_text("Most Valuable: ")
                    dpg.add_text("-", tag=f"{self.module_id}_most_valuable")
                
                # Right column
                with dpg.group():
                    dpg.add_text("Portfolio Score: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_portfolio_score")
                    dpg.add_text("Diversity Index: ")
                    dpg.add_text("0.00", tag=f"{self.module_id}_diversity_index")

    def _handle_balance_update(self, event: Event):
        """Handle balance updates"""
        try:
            balances = event.data["balances"]
            
            # Update balance tracking
            self._balances = balances
            
            # Track historical data
            current_time = datetime.utcnow().timestamp()
            if current_time - self._last_track_time >= self._track_interval:
                self._track_balance_history()
                self._last_track_time = current_time
            
            # Update displays
            self._update_balances_table()
            self._update_portfolio_analysis()
            
        except Exception as e:
            self.logger.error(f"Error handling balance update: {str(e)}")

    def _handle_price_update(self, event: Event):
        """Handle price updates for value calculations"""
        try:
            data = event.data
            pair = data["pair"]
            price = data["ticker"]["price"]
            
            # Update value calculations if the price is for a held asset
            asset = pair.split('/')[0]
            if asset in self._balances:
                self._update_balances_table()
                self._update_portfolio_analysis()
                
        except Exception as e:
            self.logger.error(f"Error handling price update: {str(e)}")

    def _update_balances_table(self):
        """Update balances table display"""
        try:
            # Clear existing rows
            dpg.delete_item(f"{self.module_id}_balances_table", children_only=True, slot=1)
            
            total_value = 0
            
            # Add balance rows
            for asset, balance in self._balances.items():
                # Get asset value in USD
                value = self._get_asset_value_usd(asset, balance["total"])
                total_value += value
                
                with dpg.table_row(parent=f"{self.module_id}_balances_table"):
                    dpg.add_text(asset)
                    dpg.add_text(f"{balance['available']:.{self._value_precision}f}")
                    dpg.add_text(f"{balance['in_orders']:.{self._value_precision}f}")
                    dpg.add_text(f"{balance['total']:.{self._value_precision}f}")
                    dpg.add_text(f"${value:.{self._fiat_precision}f}")
                    dpg.add_text("0.00%")  # Will be updated after total calculation
            
            # Update percentages
            if total_value > 0:
                for row in dpg.get_item_children(f"{self.module_id}_balances_table", slot=1):
                    asset = dpg.get_item_children(row)[0]
                    value_cell = dpg.get_item_children(row)[4]
                    pct_cell = dpg.get_item_children(row)[5]
                    
                    value = float(dpg.get_value(value_cell).replace('$', ''))
                    percentage = (value / total_value) * 100
                    dpg.set_value(pct_cell, f"{percentage:.2f}%")
            
            # Update total value display
            dpg.set_value(f"{self.module_id}_total_value", f"${total_value:.{self._fiat_precision}f}")
            
            # Update 24h change
            self._update_24h_change(total_value)
            
        except Exception as e:
            self.logger.error(f"Error updating balances table: {str(e)}")

    def _get_asset_value_usd(self, asset: str, amount: float) -> float:
        """Get USD value of an asset amount"""
        try:
            if asset == "USD":
                return amount
            
            # Get price from state manager
            price = state_manager.get_state(f"price_{asset}/USD", None)
            if price is None:
                # Try to get price through another pair (e.g., USDT)
                price = state_manager.get_state(f"price_{asset}/USDT", 0.0)
            
            return amount * price
            
        except Exception as e:
            self.logger.error(f"Error calculating asset value: {str(e)}")
            return 0.0

    def _track_balance_history(self):
        """Track current balances in history"""
        try:
            timestamp = datetime.utcnow()
            
            # Track individual asset balances
            for asset, balance in self._balances.items():
                if asset not in self._balance_history:
                    self._balance_history[asset] = []
                
                self._balance_history[asset].append({
                    "timestamp": timestamp,
                    "amount": balance["total"],
                    "value_usd": self._get_asset_value_usd(asset, balance["total"])
                })
            
            # Track total equity
            total_value = sum(
                self._get_asset_value_usd(asset, balance["total"])
                for asset, balance in self._balances.items()
            )
            
            self._equity_history.append({
                "timestamp": timestamp,
                "value": total_value
            })
            
            # Save history to file
            self._save_history()
            
        except Exception as e:
            self.logger.error(f"Error tracking balance history: {str(e)}")

    def _save_history(self):
        """Save balance history to file"""
        try:
            history_data = {
                "equity_history": [
                    {
                        "timestamp": entry["timestamp"].isoformat(),
                        "value": entry["value"]
                    }
                    for entry in self._equity_history
                ],
                "balance_history": {
                    asset: [
                        {
                            "timestamp": entry["timestamp"].isoformat(),
                            "amount": entry["amount"],
                            "value_usd": entry["value_usd"]
                        }
                        for entry in history
                    ]
                    for asset, history in self._balance_history.items()
                }
            }
            
            with open("data/balance_history.json", "w") as f:
                json.dump(history_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving balance history: {str(e)}")

    def update(self) -> None:
        """Update the module"""
        pass  # Updates are handled by event callbacks

    def cleanup(self) -> None:
        """Cleanup module resources"""
        event_system.unsubscribe(EventTypes.BALANCE_UPDATE, self._handle_balance_update)
        event_system.unsubscribe(EventTypes.PRICE_UPDATE, self._handle_price_update)
        self._save_history()

    def get_data(self) -> Dict[str, Any]:
        """Get module data"""
        return {
            "balances": self._balances,
            "equity_history": self._equity_history,
            "balance_history": self._balance_history
        } 