import dearpygui.dearpygui as dpg
import logging
import sys
from pathlib import Path

def main():
    # Setup basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("test.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("Starting test application")
    
    try:
        # Initialize DPG
        dpg.create_context()
        logging.info("Context created")
        
        dpg.create_viewport(title="Test Window", width=800, height=600)
        logging.info("Viewport created")
        
        dpg.setup_dearpygui()
        logging.info("DPG setup complete")
        
        # Create a simple window
        with dpg.window(label="Test Window"):
            dpg.add_text("Hello, World!")
            dpg.add_button(label="Click Me!")
        
        logging.info("Window created")
        
        # Show viewport
        dpg.show_viewport()
        logging.info("Viewport shown")
        
        # Start the render loop
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
        
    except Exception as e:
        logging.error(f"Error in test: {str(e)}", exc_info=True)
    finally:
        dpg.destroy_context()
        logging.info("Test complete")

if __name__ == "__main__":
    main() 