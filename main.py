# Main application entry point
import asyncio
import logging
import sys
from pathlib import Path
import dearpygui.dearpygui as dpg

from core.event_system import event_system
from core.state_manager import state_manager
from core.data_manager import data_manager
from gui.main_window import main_window
from modules.market_data_display import MarketDataDisplay
from modules.order_management import OrderManagement
from modules.position_monitor import PositionMonitor
from modules.account_balance import AccountBalance
from modules.strategies.moving_average_cross import MovingAverageCross
from config.config import TRADING_PAIRS

def setup_logging():
    """Setup logging configuration"""
    log_file = Path("logs/trading_system.log")
    log_file.parent.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
async def initialize_system():
    """Initialize all system components"""
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("trading_system.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Create necessary directories
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        Path("config").mkdir(exist_ok=True)

        logging.info("Starting system initialization...")
        # Initialize DearPyGui first
        dpg.create_context()
        dpg.create_viewport(title="Trading System", width=1920, height=1080)
        dpg.setup_dearpygui()
        
        # Initialize core components
        await data_manager.start()
        logging.info("Data manager started")
        
        # Initialize GUI
        main_window.setup()
        logging.info("GUI initialized")
        
        # Initialize modules
        modules = [
            MarketDataDisplay("market_data_1"),
            OrderManagement("order_management_1"),
            PositionMonitor("position_monitor_1"),
            AccountBalance("account_balance_1"),
            MovingAverageCross("ma_cross_1")
        ]
        
        for module in modules:
            try:
                if not module.initialize():
                    logging.error(f"Failed to initialize module: {module.module_name}")
                    return False
                logging.info(f"Initialized module: {module.module_name}")
            except Exception as e:
                logging.error(f"Error initializing module {module.module_name}: {str(e)}")
                return False
        
        logging.info("System initialization completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error during system initialization: {str(e)}", exc_info=True)
        return False

async def cleanup_system():
    """Cleanup system resources"""
    try:
        await data_manager.stop()
        # Add any other cleanup tasks here
        
    except Exception as e:
        logging.error(f"Error during system cleanup: {str(e)}")

async def main():
    """Main application entry point"""
    try:
        # Initialize system
        if not await initialize_system():
            logging.error("System initialization failed")
            return
        
        # Start main event loop
        while dpg.is_dearpygui_running():
            await asyncio.sleep(0.1)
            dpg.render_dearpygui_frame()
        
        # Cleanup
        await cleanup_system()
        
    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")
    finally:
        dpg.destroy_context()

if __name__ == "__main__":
    asyncio.run(main())