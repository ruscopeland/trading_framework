from typing import Dict, Any, Optional, List
import numpy as np
from modules.trading_strategy import TradingStrategy

class MovingAverageCross(TradingStrategy):
    def __init__(self, module_id: str):
        super().__init__(module_id)
        self.module_name = "Moving Average Cross"
        self.module_description = "Simple MA crossover strategy"
        
        # Strategy parameters
        self.parameters = {
            "fast_ma": 10,
            "slow_ma": 20,
            "min_volume": 1.0,
            "entry_threshold": 0.001,  # 0.1%
            "exit_threshold": 0.0005   # 0.05%
        }
        
        # Strategy state
        self._price_history: Dict[str, List[float]] = {}
        self._last_cross: Dict[str, str] = {}  # "up" or "down"

    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        # Initialize price history for each pair
        for pair in self._trading_pairs:
            self._price_history[pair] = []
            self._last_cross[pair] = ""

    def _process_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process price updates and generate signals"""
        pair = data["pair"]
        if pair not in self._trading_pairs:
            return None
            
        price = data["ticker"]["price"]
        volume = data["ticker"]["volume"]
        
        # Update price history
        self._price_history[pair].append(price)
        
        # Keep only needed history
        max_length = max(self.parameters["fast_ma"], self.parameters["slow_ma"]) * 2
        if len(self._price_history[pair]) > max_length:
            self._price_history[pair] = self._price_history[pair][-max_length:]
        
        # Check for sufficient history
        if len(self._price_history[pair]) < self.parameters["slow_ma"]:
            return None
            
        # Check volume
        if volume < self.parameters["min_volume"]:
            return None
            
        # Calculate moving averages
        fast_ma = np.mean(self._price_history[pair][-self.parameters["fast_ma"]:])
        slow_ma = np.mean(self._price_history[pair][-self.parameters["slow_ma"]:])
        
        # Generate signals
        signal = None
        
        # Check for crossover
        if fast_ma > slow_ma:
            if self._last_cross[pair] != "up":
                signal = {
                    "pair": pair,
                    "direction": "buy",
                    "strength": (fast_ma - slow_ma) / slow_ma,
                    "price": price
                }
                self._last_cross[pair] = "up"
        else:
            if self._last_cross[pair] != "down":
                signal = {
                    "pair": pair,
                    "direction": "sell",
                    "strength": (slow_ma - fast_ma) / slow_ma,
                    "price": price
                }
                self._last_cross[pair] = "down"
        
        return signal

    def _generate_order(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate order from signal"""
        # Check signal strength against thresholds
        if signal["direction"] == "buy":
            if signal["strength"] < self.parameters["entry_threshold"]:
                return None
        else:
            if signal["strength"] < self.parameters["exit_threshold"]:
                return None
        
        # Calculate position size based on risk
        account_value = self._get_account_value()
        risk_amount = account_value * self._risk_per_trade
        
        # Simple position sizing based on account value and risk
        position_size = risk_amount / signal["price"]
        
        return {
            "pair": signal["pair"],
            "type": "market",
            "side": signal["direction"],
            "size": position_size,
            "risk_amount": risk_amount
        } 