# database/db_manager.py
import sqlite3
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import pandas as pd

class DatabaseManager:
    """Manages database operations for the trading system"""
    
    def __init__(self):
        self.logger = logging.getLogger("DatabaseManager")
        self.db_dir = Path("database")
        self.db_dir.mkdir(exist_ok=True)
        self.db_path = self.db_dir / "trading_data.db"
        
        # Initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Trades table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        timestamp DATETIME,
                        pair TEXT,
                        side TEXT,
                        type TEXT,
                        price REAL,
                        volume REAL,
                        cost REAL,
                        fee REAL,
                        strategy_id TEXT,
                        extra_data TEXT
                    )
                ''')
                
                # Orders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        timestamp DATETIME,
                        pair TEXT,
                        side TEXT,
                        type TEXT,
                        price REAL,
                        volume REAL,
                        status TEXT,
                        strategy_id TEXT,
                        extra_data TEXT
                    )
                ''')
                
                # Balance history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS balance_history (
                        timestamp DATETIME,
                        asset TEXT,
                        total REAL,
                        available REAL,
                        in_orders REAL,
                        PRIMARY KEY (timestamp, asset)
                    )
                ''')
                
                # Strategy performance table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        timestamp DATETIME,
                        strategy_id TEXT,
                        metric_name TEXT,
                        value REAL,
                        PRIMARY KEY (timestamp, strategy_id, metric_name)
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise

    def save_trade(self, trade_data: Dict[str, Any]):
        """Save trade to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                extra_data = json.dumps(trade_data.get('extra_data', {}))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO trades (
                        trade_id, timestamp, pair, side, type, 
                        price, volume, cost, fee, strategy_id, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade_data['trade_id'],
                    trade_data['timestamp'],
                    trade_data['pair'],
                    trade_data['side'],
                    trade_data['type'],
                    trade_data['price'],
                    trade_data['volume'],
                    trade_data['cost'],
                    trade_data['fee'],
                    trade_data.get('strategy_id'),
                    extra_data
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving trade: {str(e)}")
            raise

    def save_order(self, order_data: Dict[str, Any]):
        """Save order to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                extra_data = json.dumps(order_data.get('extra_data', {}))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO orders (
                        order_id, timestamp, pair, side, type,
                        price, volume, status, strategy_id, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_data['order_id'],
                    order_data['timestamp'],
                    order_data['pair'],
                    order_data['side'],
                    order_data['type'],
                    order_data['price'],
                    order_data['volume'],
                    order_data['status'],
                    order_data.get('strategy_id'),
                    extra_data
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving order: {str(e)}")
            raise

    def save_balance(self, balance_data: Dict[str, Dict[str, float]]):
        """Save balance snapshot to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = datetime.utcnow()
                
                for asset, data in balance_data.items():
                    cursor.execute('''
                        INSERT INTO balance_history (
                            timestamp, asset, total, available, in_orders
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        timestamp,
                        asset,
                        data['total'],
                        data['available'],
                        data['in_orders']
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving balance: {str(e)}")
            raise

    def get_trades(
        self,
        pair: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        strategy_id: Optional[str] = None
    ) -> pd.DataFrame:
        """Get trades from database with optional filters"""
        try:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
                
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
                
            if strategy_id:
                query += " AND strategy_id = ?"
                params.append(strategy_id)
            
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
                
        except Exception as e:
            self.logger.error(f"Error getting trades: {str(e)}")
            raise

    def get_orders(
        self,
        status: Optional[str] = None,
        pair: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get orders from database with optional filters"""
        try:
            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
                
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
                
        except Exception as e:
            self.logger.error(f"Error getting orders: {str(e)}")
            raise

# Global database manager instance
db_manager = DatabaseManager()
