# gui/theme.py
import dearpygui.dearpygui as dpg

def setup_theme():
    """Setup custom theme for the application"""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window padding
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 6)
            
            # Colors
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (32, 32, 32))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (49, 49, 49))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (62, 62, 62))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (72, 72, 72))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (82, 82, 82))
            
            # Text colors
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (128, 128, 128))
            
            # Headers
            dpg.add_theme_color(dpg.mvThemeCol_Header, (66, 150, 250))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (76, 160, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (86, 170, 255))
            
    dpg.bind_theme(global_theme)
