
import os
import sys
import zipfile
import shutil
import subprocess
import webbrowser
import json
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import winreg
from PIL import Image, ImageTk
import psutil
import logging
import atexit
import tempfile
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from version import __version__ as overlord_version

def detect_windows_theme():
    """Detect if Windows is using dark or light theme"""
    try:
        # Check Windows registry for theme setting
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                     r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(registry_key, "AppsUseLightTheme")
        winreg.CloseKey(registry_key)
        return "light" if value else "dark"
    except Exception:
        # Default to light theme if detection fails
        return "light"

class ThemeManager:
    def __init__(self):
        self.current_theme = detect_windows_theme()
        self.themes = {
            "light": {
                "bg": "#f0f0f0",
                "fg": "#000000",
                "entry_bg": "#ffffff",
                "entry_fg": "#000000",
                "button_bg": "#e1e1e1",
                "button_fg": "#000000",
                "frame_bg": "#f0f0f0",
                "text_bg": "#ffffff",
                "text_fg": "#000000",
                "console_bg": "#f0f0f0",
                "console_fg": "#000000",
                "select_bg": "#0078d4",
                "select_fg": "#ffffff",
                "highlight_bg": "#cccccc"
            },
            "dark": {
                "bg": "#2d2d30",
                "fg": "#ffffff",
                "entry_bg": "#3c3c3c",
                "entry_fg": "#ffffff",
                "button_bg": "#404040",
                "button_fg": "#ffffff",
                "frame_bg": "#2d2d30",
                "text_bg": "#1e1e1e",
                "text_fg": "#ffffff",
                "console_bg": "#1e1e1e",
                "console_fg": "#ffffff",
                "select_bg": "#0078d4",
                "select_fg": "#ffffff",
                "highlight_bg": "#404040"
            }
        }
        self.widgets_to_theme = []
        self.ttk_style = None
        
    def get_color(self, color_name):
        return self.themes[self.current_theme][color_name]
    
    def setup_ttk_style(self):
        """Setup ttk styles for themed widgets"""
        if self.ttk_style is None:
            self.ttk_style = ttk.Style()
        
        # Configure progress bar style
        self.ttk_style.configure("Themed.Horizontal.TProgressbar",
                                background=self.get_color("select_bg"),
                                troughcolor=self.get_color("entry_bg"),
                                bordercolor=self.get_color("highlight_bg"),
                                lightcolor=self.get_color("select_bg"),
                                darkcolor=self.get_color("select_bg"))
    
    def register_widget(self, widget, widget_type="default"):
        """Register a widget to be themed"""
        self.widgets_to_theme.append((widget, widget_type))
        self.apply_theme_to_widget(widget, widget_type)
    
    def apply_theme_to_widget(self, widget, widget_type="default"):
        """Apply current theme to a specific widget"""
        try:
            if widget_type == "root":
                widget.configure(bg=self.get_color("bg"))
            elif widget_type == "frame":
                widget.configure(bg=self.get_color("frame_bg"))
            elif widget_type == "label":
                widget.configure(bg=self.get_color("bg"), fg=self.get_color("fg"))
            elif widget_type == "entry":
                widget.configure(bg=self.get_color("entry_bg"), fg=self.get_color("entry_fg"),
                               insertbackground=self.get_color("entry_fg"))
            elif widget_type == "text":
                widget.configure(bg=self.get_color("text_bg"), fg=self.get_color("text_fg"),
                               insertbackground=self.get_color("text_fg"),
                               selectbackground=self.get_color("select_bg"),
                               selectforeground=self.get_color("select_fg"))
            elif widget_type == "button":
                widget.configure(bg=self.get_color("button_bg"), fg=self.get_color("button_fg"),
                               activebackground=self.get_color("highlight_bg"),
                               activeforeground=self.get_color("fg"))
            elif widget_type == "checkbutton":
                widget.configure(bg=self.get_color("bg"), fg=self.get_color("fg"),
                               activebackground=self.get_color("bg"),
                               activeforeground=self.get_color("fg"),
                               selectcolor=self.get_color("entry_bg"))
            elif widget_type == "console":
                widget.configure(bg=self.get_color("console_bg"), fg=self.get_color("console_fg"))
            elif widget_type == "progressbar":
                # Apply ttk style to progress bar
                if self.ttk_style is None:
                    self.setup_ttk_style()
                widget.configure(style="Themed.Horizontal.TProgressbar")
        except Exception:
            # Some widgets might not support all options
            pass
    
    def apply_theme_to_all(self):
        """Apply current theme to all registered widgets"""
        if self.ttk_style is None:
            self.setup_ttk_style()
        for widget, widget_type in self.widgets_to_theme:
            self.apply_theme_to_widget(widget, widget_type)

# Global theme manager instance
theme_manager = ThemeManager()

# Global cleanup manager
class CleanupManager:
    def __init__(self):
        self.temp_files = []
        self.image_references = []
        self.executor = None
        self.cleanup_registered = False
    
    def register_temp_file(self, filepath):
        """Register a temporary file for cleanup"""
        self.temp_files.append(filepath)
    
    def register_image_reference(self, image_ref):
        """Register an image reference for cleanup"""
        self.image_references.append(image_ref)
    
    def register_executor(self, executor):
        """Register a thread pool executor for cleanup"""
        self.executor = executor
    
    def cleanup_all(self):
        """Clean up all registered resources"""
        try:
            # Clear image references first
            for img_ref in self.image_references:
                try:
                    if hasattr(img_ref, 'close'):
                        img_ref.close()
                    del img_ref
                except Exception:
                    pass
            self.image_references.clear()
            
            # Force garbage collection
            gc.collect()
            
            # Shutdown executor if exists
            if self.executor:
                try:
                    self.executor.shutdown(wait=False)
                except Exception:
                    pass
            
            # Clean up temporary files
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception:
                    pass
            self.temp_files.clear()
            
            # Additional cleanup for PIL temporary files
            try:
                # Clear PIL's internal cache
                Image._initialized = 0
                # Force cleanup of any remaining temporary files
                temp_dir = tempfile.gettempdir()
                for filename in os.listdir(temp_dir):
                    if filename.startswith('tmp') and ('PIL' in filename or 'Tk' in filename):
                        try:
                            temp_path = os.path.join(temp_dir, filename)
                            if os.path.isfile(temp_path):
                                os.unlink(temp_path)
                        except Exception:
                            pass
            except Exception:
                pass
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

cleanup_manager = CleanupManager()

def register_cleanup():
    """Register cleanup function to be called on exit"""
    if not cleanup_manager.cleanup_registered:
        atexit.register(cleanup_manager.cleanup_all)
        cleanup_manager.cleanup_registered = True

def archive_and_delete(inner_path, archive_path):
    logging.info(f"Archiving {inner_path} to {archive_path}")
    try:
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(inner_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, inner_path)
                    zipf.write(file_path, arcname)
        logging.info(f"Successfully archived {inner_path} to {archive_path}")
        try:
            shutil.rmtree(inner_path)
            logging.info(f"Deleted folder {inner_path}")
        except Exception as e:
            logging.error(f"Failed to delete folder {inner_path}: {e}")
    except Exception as e:
        logging.error(f"Failed to archive {inner_path}: {e}")

def archive_all_inner_folders(base_path):
    """Archive all inner folders in the structure base_path/*/*/* to zip, then delete the folder."""
    to_archive = []
    for folder_name in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder_name)
        if os.path.isdir(folder_path):
            for subfolder_name in os.listdir(folder_path):
                subfolder_path = os.path.join(folder_path, subfolder_name)
                if os.path.isdir(subfolder_path):
                    for inner_name in os.listdir(subfolder_path):
                        inner_path = os.path.join(subfolder_path, inner_name)
                        if os.path.isdir(inner_path):
                            archive_path = os.path.join(subfolder_path, f"{inner_name}.zip")
                            if not os.path.exists(archive_path):
                                to_archive.append((inner_path, archive_path))
    DEFAULT_MAX_WORKERS = int(os.environ.get('DEFAULT_MAX_WORKERS', 8))
    max_workers = min(DEFAULT_MAX_WORKERS, os.cpu_count() or 1)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        cleanup_manager.register_executor(executor)
        futures = [executor.submit(archive_and_delete, inner_path, archive_path) for inner_path, archive_path in to_archive]
        for future in as_completed(futures):
            try:
                future.result()  # Ensure any exceptions are raised here
            except Exception as e:
                logging.error(f"An error occurred while processing a future: {e}")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def setup_logger():
    # Try to write log to %APPDATA%/Overlord/log.txt (user-writable)
    appdata = os.environ.get('APPDATA')
    if appdata:
        log_dir = os.path.join(appdata, 'Overlord')
    else:
        # Fallback to user's home directory
        log_dir = os.path.join(os.path.expanduser('~'), 'Overlord')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'log.txt')
    from logging.handlers import RotatingFileHandler
    max_bytes = 100 * 1024 * 1024  # 100 MB
    file_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=1, encoding='utf-8')
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[file_handler, stream_handler]
    )
    logging.info(f'--- Overlord started --- (log file: {log_path}, max size: 100 MB)')

def main():
    import re

    def update_estimated_time_remaining(images_remaining):
        # Get user profile directory
        user_profile = os.environ.get('USERPROFILE') or os.path.expanduser('~')
        base_log_dir = os.path.join(user_profile, "AppData", "Roaming", "DAZ 3D")
        avg_times = []
        num_instances_str = value_entries.get("Number of Instances", None)
        try:
            num_instances = int(num_instances_str.get()) if num_instances_str else 1
        except Exception:
            num_instances = 1

        for i in range(1, num_instances + 1):
            # Always use Studio4 [i] for all instances, including i==1
            studio_dir = os.path.join(base_log_dir, f"Studio4 [{i}]")
            log_path = os.path.join(studio_dir, "log.txt")
            if not os.path.exists(log_path):
                continue
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    # Collect all matching times in this log
                    times = [float(m.group(1)) for line in f if (m := re.search(r"Total Rendering Time: (\d+(?:\.\d+)?) seconds", line))]
                    avg_times.extend(times)
            except Exception:
                continue

        # Use only the 25 most recent render times (from all logs combined)
        if avg_times and len(avg_times) > 0:
            import datetime
            recent_times = avg_times[-25:] if len(avg_times) > 25 else avg_times
            avg_time = sum(recent_times) / len(recent_times)
            total_seconds = int(avg_time * images_remaining)
            # Format as H:MM:SS
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                formatted = f"Estimated time remaining: {hours}:{minutes:02}:{seconds:02}"
            else:
                formatted = f"Estimated time remaining: {minutes}:{seconds:02}"
            estimated_time_remaining_var.set(formatted)
            # Set estimated completion at
            completion_time = datetime.datetime.now() + datetime.timedelta(seconds=total_seconds)
            # Format: "Thursday, July 10th, 2025 2:35 PM"
            def ordinal(n):
                if 10 <= n % 100 <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
                return str(n) + suffix

            weekday = completion_time.strftime('%A')
            month = completion_time.strftime('%B')
            day = ordinal(completion_time.day)
            year = completion_time.year
            hour = completion_time.strftime('%I').lstrip('0') or '12'
            minute = completion_time.strftime('%M')
            ampm = completion_time.strftime('%p')
            completion_str = f"Estimated completion at: {weekday}, {month} {day}, {year} {hour}:{minute} {ampm}"
            estimated_completion_at_var.set(completion_str)
        else:
            estimated_time_remaining_var.set("Estimated time remaining: --")
            estimated_completion_at_var.set("Estimated completion at: --")
    setup_logger()
    register_cleanup()  # Register cleanup functions
    logging.info('Application launched')
    logging.info(f'Windows theme detected: {theme_manager.current_theme} mode')
    # Create the main window
    root = tk.Tk()
    root.title(f"Overlord {overlord_version}")
    root.iconbitmap(resource_path(os.path.join("images", "favicon.ico")))  # Set the application icon
    
    # Apply theme to root window
    theme_manager.register_widget(root, "root")
    # Setup ttk styles early
    theme_manager.setup_ttk_style()
    
    # Register proper window close handler
    def on_closing():
        """Handle window closing event"""
        logging.info('Application closing...')
        cleanup_manager.cleanup_all()
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # ...existing code...

    # Maximize the application window
    root.state("zoomed")

    # Load and display the logo image
    logo = tk.PhotoImage(file=resource_path(os.path.join("images", "overlordLogo.png")))
    logo_label = tk.Label(root, image=logo, cursor="hand2")
    logo_label.image = logo  # Keep a reference to avoid garbage collection
    logo_label.place(anchor="nw", x=10, y=10)  # Place in upper left corner, 10px down and right
    theme_manager.register_widget(logo_label, "label")

    # Add Laserwolve Games logo to upper right corner
    lwg_logo = tk.PhotoImage(file=resource_path(os.path.join("images", "laserwolveGamesLogo.png")))
    lwg_logo_label = tk.Label(root, image=lwg_logo, cursor="hand2")
    lwg_logo_label.image = lwg_logo  # Keep a reference to avoid garbage collection
    # Place in upper right using place geometry manager
    lwg_logo_label.place(anchor="nw", x=700)
    theme_manager.register_widget(lwg_logo_label, "label")
    def open_lwg_link(event):
        logging.info('Laserwolve Games logo clicked')
        webbrowser.open("https://www.laserwolvegames.com/")
    lwg_logo_label.bind("<Button-1>", open_lwg_link)

    def open_github_link(event):
        logging.info('Overlord GitHub logo clicked')
        webbrowser.open("https://github.com/Laserwolve-Games/Overlord")
    logo_label.bind("<Button-1>", open_github_link)

    # Create frames for the two tables
    file_table_frame = tk.Frame(root)
    file_table_frame.pack(pady=(150, 10), anchor="nw", side="top")  # Add top padding to move down
    theme_manager.register_widget(file_table_frame, "frame")
    
    param_table_frame = tk.Frame(root)
    param_table_frame.pack(pady=(20, 10), anchor="nw", side="top")  # 20px down from file_table_frame
    theme_manager.register_widget(param_table_frame, "frame")

    # File/folder path parameters
    file_params = [
        "Source Files",
        "Output Directory"
    ]
    # Short/simple parameters
    param_params = [
        "Number of Instances",
        "Frame Rate",
        "Log File Size (MBs)"
    ]
    value_entries = {}

    # Replace file_table_frame headers with a centered "Options" header
    options_header = tk.Label(file_table_frame, text="Options", font=("Arial", 14, "bold"))
    options_header.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    theme_manager.register_widget(options_header, "label")
    file_table_frame.grid_columnconfigure(0, weight=1)
    file_table_frame.grid_columnconfigure(1, weight=1)
    file_table_frame.grid_columnconfigure(2, weight=1)

    def make_browse_file(entry, initialdir=None, filetypes=None, title="Select file"):
        def browse_file():
            filename = filedialog.askopenfilename(
                initialdir=initialdir or "",
                title=title,
                filetypes=filetypes or (("All files", "*.*"),)
            )
            if filename:
                entry.delete(0, tk.END)
                entry.insert(0, filename)
        return browse_file

    def make_browse_folder(entry, initialdir=None, title="Select folder"):
        def browse_folder():
            foldername = filedialog.askdirectory(
                initialdir=initialdir or "",
                title=title
            )
            if foldername:
                entry.delete(0, tk.END)
                entry.insert(0, foldername)
        return browse_folder

    def make_browse_files(text_widget, initialdir=None, filetypes=None, title="Select files"):
        def browse_files():
            filenames = filedialog.askopenfilenames(
                initialdir=initialdir or "",
                title=title,
                filetypes=filetypes or (("All files", "*.*"),)
            )
            if filenames:
                text_widget.delete("1.0", tk.END)
                text_widget.insert(tk.END, "\n".join(filenames))
        return browse_files

    # File/folder path parameters table
    for i, param in enumerate(file_params):
        param_label = tk.Label(file_table_frame, text=param, font=("Arial", 10), anchor="w")
        param_label.grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
        theme_manager.register_widget(param_label, "label")

        if param == "Source Files":
            text_widget = tk.Text(file_table_frame, width=80, height=5, font=("Consolas", 10))
            text_widget.grid(row=i+1, column=1, padx=10, pady=5, sticky="e")
            theme_manager.register_widget(text_widget, "text")
            def browse_files_append():
                # Start in user's Documents directory
                documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
                filenames = filedialog.askopenfilenames(
                    initialdir=documents_dir,
                    title="Select Source Files",
                    filetypes=(("DSON User File", "*.duf"),)
                )
                if filenames:
                    filenames = [fname.replace('/', '\\') for fname in filenames]
                    current = text_widget.get("1.0", tk.END).strip().replace('/', '\\')
                    current_files = set(current.split("\n")) if current else set()
                    new_files = [fname for fname in filenames if fname not in current_files]
                    if new_files:
                        # If textbox is not empty, append new files each on a new line
                        if current:
                            text_widget.insert(tk.END, "\n" + "\n".join(new_files))
                        else:
                            text_widget.insert(tk.END, "\n".join(new_files))
            button_frame = tk.Frame(file_table_frame)
            button_frame.grid(row=i+1, column=2, padx=5, pady=5, sticky="n")
            theme_manager.register_widget(button_frame, "frame")

            browse_button = tk.Button(
                button_frame,
                text="Browse",
                command=browse_files_append,
                width=8
            )
            browse_button.pack(side="top", fill="x", pady=(0, 2))
            theme_manager.register_widget(browse_button, "button")

            def clear_source_files():
                text_widget.delete("1.0", tk.END)
            clear_button = tk.Button(
                button_frame,
                text="Clear",
                command=clear_source_files,
                width=8
            )
            clear_button.pack(side="top", fill="x")
            theme_manager.register_widget(clear_button, "button")
            value_entries[param] = text_widget
        elif param == "Output Directory":
            value_entry = tk.Entry(file_table_frame, width=80, font=("Consolas", 10))
            default_img_dir = os.path.join(
                os.path.expanduser("~"),
                "Downloads", "output"
            )
            value_entry.insert(0, default_img_dir)
            value_entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="e")
            theme_manager.register_widget(value_entry, "entry")

            browse_button = tk.Button(
                file_table_frame,
                text="Browse",
                command=make_browse_folder(
                    value_entry,
                    initialdir=default_img_dir,
                    title="Select Output Directory"
                ),
                width=8
            )
            browse_button.grid(row=i+1, column=2, padx=5, pady=5)
            theme_manager.register_widget(browse_button, "button")
            value_entries[param] = value_entry




    # Short/simple parameters table
    for i, param in enumerate(param_params):
        param_label = tk.Label(param_table_frame, text=param, font=("Arial", 10), anchor="w")
        param_label.grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
        theme_manager.register_widget(param_label, "label")

        value_entry = tk.Entry(param_table_frame, width=5, font=("Consolas", 10))
        if param == "Number of Instances":
            value_entry.insert(0, "1")
        elif param == "Log File Size (MBs)":
            value_entry.insert(0, "100")
        elif param == "Frame Rate":
            value_entry.insert(0, "30")
        value_entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="e")
        theme_manager.register_widget(value_entry, "entry")
        value_entries[param] = value_entry

    # Add "Render shadows" label and checkbox under Log File Size
    render_shadows_var = tk.BooleanVar(value=True)
    render_shadows_label = tk.Label(param_table_frame, text="Render shadows", font=("Arial", 10), anchor="w")
    render_shadows_label.grid(row=len(param_params)+1, column=0, padx=10, pady=(0, 0), sticky="w")
    theme_manager.register_widget(render_shadows_label, "label")
    render_shadows_checkbox = tk.Checkbutton(
        param_table_frame,
        variable=render_shadows_var,
        width=2,
        anchor="w"
    )
    render_shadows_checkbox.grid(row=len(param_params)+1, column=1, padx=10, pady=(0, 5), sticky="w")
    theme_manager.register_widget(render_shadows_checkbox, "checkbutton")

    # Add "Close Overlord After Starting Render" label and checkbox below Render Shadows
    close_after_render_var = tk.BooleanVar(value=False)
    close_after_render_label = tk.Label(param_table_frame, text="Close Overlord After Starting Render", font=("Arial", 10), anchor="w")
    close_after_render_label.grid(row=len(param_params)+2, column=0, padx=10, pady=(0, 0), sticky="w")
    theme_manager.register_widget(close_after_render_label, "label")
    close_after_render_checkbox = tk.Checkbutton(
        param_table_frame,
        variable=close_after_render_var,
        width=2,
        anchor="w"
    )
    close_after_render_checkbox.grid(row=len(param_params)+2, column=1, padx=10, pady=(0, 5), sticky="w")
    theme_manager.register_widget(close_after_render_checkbox, "checkbutton")

    # Add "Close Daz Studio on Finish" label and checkbox below Close Overlord
    close_daz_on_finish_var = tk.BooleanVar(value=True)
    close_daz_on_finish_label = tk.Label(param_table_frame, text="Close Daz Studio on Finish", font=("Arial", 10), anchor="w")
    close_daz_on_finish_label.grid(row=len(param_params)+3, column=0, padx=10, pady=(0, 0), sticky="w")
    theme_manager.register_widget(close_daz_on_finish_label, "label")
    close_daz_on_finish_checkbox = tk.Checkbutton(
        param_table_frame,
        variable=close_daz_on_finish_var,
        width=2,
        anchor="w"
    )
    close_daz_on_finish_checkbox.grid(row=len(param_params)+3, column=1, padx=10, pady=(0, 5), sticky="w")
    theme_manager.register_widget(close_daz_on_finish_checkbox, "checkbutton")

    # --- Last Rendered Image Section ---
    right_frame = tk.Frame(root)
    right_frame.place(relx=0.73, rely=0.0, anchor="n", width=1024, height=1024)
    theme_manager.register_widget(right_frame, "frame")

    # Set border color based on theme
    border_color = "#cccccc" if theme_manager.current_theme == "light" else "#555555"
    right_frame.config(highlightbackground=border_color, highlightthickness=1)

    # Place img_label directly in right_frame
    img_label = tk.Label(right_frame)
    img_label.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)
    theme_manager.register_widget(img_label, "label")

    # --- Image Details Column ---
    # Place details_frame to the right of param_table_frame
    details_frame = tk.Frame(root, width=350)
    details_frame.place(relx=0.25, rely=0.6, anchor="nw", width=350, height=200)
    details_frame.pack_propagate(False)
    theme_manager.register_widget(details_frame, "frame")

    details_title = tk.Label(details_frame, text="Last Rendered Image Details", font=("Arial", 14, "bold"))
    details_title.pack(anchor="nw", pady=(0, 10))
    theme_manager.register_widget(details_title, "label")

    # Show only the path (no "Path: " prefix)
    details_path = tk.Label(details_frame, text="", font=("Consolas", 9), wraplength=330, justify="left")
    details_path.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(details_path, "label")

    # Add a button to copy the path to clipboard
    def copy_path_to_clipboard():
        path = details_path.cget("text")
        if path:
            root.clipboard_clear()
            root.clipboard_append(path)
            root.update()  # Keeps clipboard after window closes

    copy_btn = tk.Button(details_frame, text="Copy Path", command=copy_path_to_clipboard, font=("Arial", 9))
    copy_btn.pack(anchor="nw", pady=(0, 8))
    theme_manager.register_widget(copy_btn, "button")

    details_size = tk.Label(details_frame, text="Size: ", font=("Arial", 10))
    details_size.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(details_size, "label")
    details_dim = tk.Label(details_frame, text="Dimensions: ", font=("Arial", 10))
    details_dim.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(details_dim, "label")


    # --- Output Details Column ---
    output_details_frame = tk.Frame(root, width=350)
    output_details_frame.place(relx=0.01, rely=0.6, anchor="nw", width=350, height=200)
    output_details_frame.pack_propagate(False)
    theme_manager.register_widget(output_details_frame, "frame")
    theme_manager.register_widget(output_details_frame, "frame")

    # Progress Bar for Render Completion (directly above Output Details title, not inside output_details_frame)
    from tkinter import ttk
    progress_var = tk.DoubleVar(master=root, value=0)
    # Label for images remaining (above progress bar)
    images_remaining_var = tk.StringVar(master=root, value="Images remaining: --")
    estimated_time_remaining_var = tk.StringVar(master=root, value="Estimated time remaining: --")
    estimated_completion_at_var = tk.StringVar(master=root, value="Estimated completion at: --")
    images_remaining_label = tk.Label(
        root,
        textvariable=images_remaining_var,
        font=("Arial", 10, "bold"),
        anchor="w",
        justify="left"
    )
    theme_manager.register_widget(images_remaining_label, "label")
    estimated_time_remaining_label = tk.Label(
        root,
        textvariable=estimated_time_remaining_var,
        font=("Arial", 10, "bold"),
        anchor="e",
        justify="center"
    )
    theme_manager.register_widget(estimated_time_remaining_label, "label")
    estimated_completion_at_label = tk.Label(
        root,
        textvariable=estimated_completion_at_var,
        font=("Arial", 10, "bold"),
        anchor="e",
        justify="right"
    )
    theme_manager.register_widget(estimated_completion_at_label, "label")
    images_remaining_label.place(relx=0.01, rely=0.55, anchor="nw", width=250, height=18)
    theme_manager.register_widget(images_remaining_label, "label")
    estimated_time_remaining_label.place(relx=0.11, rely=0.55, anchor="nw", width=250, height=18)
    theme_manager.register_widget(estimated_time_remaining_label, "label")
    estimated_completion_at_label.place(relx=0.245, rely=0.55, anchor="nw", width=400, height=18)
    theme_manager.register_widget(estimated_completion_at_label, "label")

    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
    # Place the progress bar just above the output_details_frame, matching its width and alignment
    progress_bar.place(relx=0.01, rely=0.57, anchor="nw", width=850, height=18)
    theme_manager.register_widget(progress_bar, "progressbar")

    output_details_title = tk.Label(output_details_frame, text="Output Details", font=("Arial", 14, "bold"))
    output_details_title.pack(anchor="nw", pady=(0, 10))
    theme_manager.register_widget(output_details_title, "label")

    output_folder_size = tk.Label(output_details_frame, text="Folder Size: ", font=("Arial", 10))
    output_folder_size.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(output_folder_size, "label")
    output_png_count = tk.Label(output_details_frame, text="PNG Files: ", font=("Arial", 10))
    output_png_count.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(output_png_count, "label")
    output_zip_count = tk.Label(output_details_frame, text="ZIP Files: ", font=("Arial", 10))
    output_zip_count.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(output_zip_count, "label")

    output_folder_count = tk.Label(output_details_frame, text="Sub-folders: ", font=("Arial", 10))
    output_folder_count.pack(anchor="nw", pady=(0, 5))
    theme_manager.register_widget(output_folder_count, "label")

    # Add Total Images to Render label (updated only on Start Render)
    output_total_images = tk.Label(output_details_frame, text="Total Images to Render: ", font=("Arial", 10))
    theme_manager.register_widget(output_total_images, "label")
    # output_total_images.pack(anchor="nw", pady=(0, 5))

    def update_output_details():
        """Update the output details with current folder statistics"""
        output_dir = value_entries["Output Directory"].get()
        if not os.path.exists(output_dir):
            output_folder_size.config(text="Folder Size: N/A")
            output_png_count.config(text="PNG Files: N/A")
            output_zip_count.config(text="ZIP Files: N/A")
            output_folder_count.config(text="Sub-folders: N/A")
            progress_var.set(0)
            images_remaining_var.set("Images remaining: --")
            return
        try:
            total_size = 0
            png_count = 0
            zip_count = 0
            folder_count = 0
            for rootdir, dirs, files in os.walk(output_dir):
                for dir_name in dirs:
                    folder_count += 1
                for file in files:
                    file_path = os.path.join(rootdir, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        if file.lower().endswith('.png'):
                            png_count += 1
                        elif file.lower().endswith('.zip'):
                            zip_count += 1
                    except (OSError, IOError):
                        continue
            if total_size < 1024:
                size_str = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            elif total_size < 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"
            output_folder_size.config(text=f"Folder Size: {size_str}")
            output_png_count.config(text=f"PNG Files: {png_count}")
            output_zip_count.config(text=f"ZIP Files: {zip_count}")
            output_folder_count.config(text=f"Sub-folders: {folder_count}")
            # Update progress bar and images remaining label
            try:
                total_images_str = output_total_images.cget("text").replace("Total Images to Render: ", "").strip()
                if not total_images_str:
                    progress_var.set(0)
                    images_remaining_var.set("Images remaining: --")
                    estimated_time_remaining_var.set("Estimated time remaining: --")
                    estimated_completion_at_var.set("Estimated completion at: --")
                    return
                total_images = int(total_images_str) if total_images_str.isdigit() else None
                if total_images and total_images > 0:
                    percent = min(100, (png_count / total_images) * 100)
                    progress_var.set(percent)
                    remaining = max(0, total_images - png_count)
                    images_remaining_var.set(f"Images remaining: {remaining}")
                    update_estimated_time_remaining(remaining)
                else:
                    progress_var.set(0)
                    images_remaining_var.set("Images remaining: --")
                    estimated_time_remaining_var.set("Estimated time remaining: --")
                    estimated_completion_at_var.set("Estimated completion at: --")
            except Exception:
                progress_var.set(0)
                images_remaining_var.set("Images remaining: --")
                estimated_time_remaining_var.set("Estimated time remaining: --")
                estimated_completion_at_var.set("Estimated completion at: --")
        except Exception as e:
            output_folder_size.config(text="Folder Size: Error")
            output_png_count.config(text="PNG Files: Error")
            output_zip_count.config(text="ZIP Files: Error")
            output_folder_count.config(text="Sub-folders: Error")
            progress_var.set(0)
            images_remaining_var.set("Images remaining: --")

    no_img_label = tk.Label(right_frame, text="No images found in output directory", font=("Arial", 12))
    no_img_label.place(relx=0.5, rely=0.5, anchor="center")
    no_img_label.lower()  # Hide initially
    theme_manager.register_widget(no_img_label, "label")

    def find_newest_image(directory):
        image_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
        # Collect all image files and their modification times
        image_files = []
        for rootdir, _, files in os.walk(directory):
            for fname in files:
                if fname.lower().endswith(image_exts):
                    fpath = os.path.join(rootdir, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        image_files.append((mtime, fpath))
                    except Exception:
                        continue
        # Sort by most recent first
        image_files.sort(reverse=True)
        return [fpath for mtime, fpath in image_files]

    def show_last_rendered_image():
        output_dir = value_entries["Output Directory"].get()
        image_paths = find_newest_image(output_dir)
        displayed = False
        for newest_img_path in image_paths:
            if not os.path.exists(newest_img_path):
                continue
            try:
                # Clean up previous image reference if it exists
                if hasattr(img_label, 'image') and img_label.image:
                    try:
                        old_img = img_label.image
                        if hasattr(old_img, 'close'):
                            old_img.close()
                        del old_img
                    except Exception:
                        pass
                
                # First, verify the image integrity
                with Image.open(newest_img_path) as verify_img:
                    verify_img.verify()  # Will raise if the image is incomplete or corrupt
                
                # If verification passes, reopen for display
                with Image.open(newest_img_path) as img:
                    img = img.convert("RGBA")  # Ensure image is in RGBA mode
                    # Handle transparency by adding a theme-appropriate background
                    if theme_manager.current_theme == "dark":
                        # Dark grey background for dark theme
                        bg_color = (60, 60, 60, 255)  # Dark grey
                    else:
                        # White background for light theme
                        bg_color = (255, 255, 255, 255)  # White
                    bg = Image.new("RGBA", img.size, bg_color)
                    img = Image.alpha_composite(bg, img)
                    
                    # Create a copy to avoid keeping the file handle open
                    img_copy = img.copy()
                    width, height = img.size
                
                with Image.open(newest_img_path) as orig_img:
                    width, height = orig_img.size
                
                file_size = os.path.getsize(newest_img_path)
                # Always display path with Windows separators
                details_path.config(text=newest_img_path.replace('/', '\\'))  # No "Path: " prefix
                details_dim.config(text=f"Dimensions: {width} x {height}")
                details_size.config(text=f"Size: {file_size/1024:.1f} KB")
                
                tk_img = ImageTk.PhotoImage(img_copy)
                cleanup_manager.register_image_reference(tk_img)  # Register for cleanup
                img_label.config(image=tk_img)
                img_label.image = tk_img
                no_img_label.lower()
                
                # Only log if the image path has changed
                if getattr(show_last_rendered_image, 'last_logged_img_path', None) != newest_img_path:
                    logging.info(f'Displaying image: {newest_img_path}')
                    show_last_rendered_image.last_logged_img_path = newest_img_path
                show_last_rendered_image.last_no_img_logged = False
                displayed = True
                break
            except Exception:
                continue
        
        if not displayed:
            # Clean up image reference
            if hasattr(img_label, 'image') and img_label.image:
                try:
                    old_img = img_label.image
                    if hasattr(old_img, 'close'):
                        old_img.close()
                    del old_img
                except Exception:
                    pass
            
            img_label.config(image="")
            img_label.image = None
            details_path.config(text="")
            details_dim.config(text="Dimensions: ")
            details_size.config(text="Size: ")
            no_img_label.lift()
            if not getattr(show_last_rendered_image, 'last_no_img_logged', False):
                logging.info('No images found in output directory or all images failed to load')
                show_last_rendered_image.last_no_img_logged = True
        
        # Force garbage collection to clean up any remaining references
        gc.collect()
        
        # Schedule to check again in 1 second
        root.after(1000, show_last_rendered_image)

    def periodic_update_output_details():
        """Periodically update output details every 5 seconds"""
        update_output_details()
        root.after(5000, periodic_update_output_details)

    # Update image when output directory changes or after render
    def on_output_dir_change(*args):
        logging.info(f'Output Directory changed to: {value_entries["Output Directory"].get()}')
        update_console(f'Output dir: {os.path.basename(value_entries["Output Directory"].get())}')
        root.after(200, show_last_rendered_image)
        root.after(200, update_output_details)
    value_entries["Output Directory"].bind("<FocusOut>", lambda e: on_output_dir_change())
    value_entries["Output Directory"].bind("<Return>", lambda e: on_output_dir_change())

    def start_render():
        # Validate Source Sets and Output Directory before launching render
        source_files = value_entries["Source Files"].get("1.0", tk.END).strip().replace("\\", "/").split("\n")
        source_files = [file for file in source_files if file]
        output_dir = value_entries["Output Directory"].get().strip()
        if not source_files:
            from tkinter import messagebox
            messagebox.showerror("Missing Source Files", "Please specify at least one Source File before starting the render.")
            update_console("Start Render cancelled: No Source Files specified.")
            logging.info("Start Render cancelled: No Source Files specified.")
            return
        if not output_dir:
            from tkinter import messagebox
            messagebox.showerror("Missing Output Directory", "Please specify an Output Directory before starting the render.")
            update_console("Start Render cancelled: No Output Directory specified.")
            logging.info("Start Render cancelled: No Output Directory specified.")
            return

        # Calculate and display total images to render (update label)
        def find_total_images(source_files):
            total_frames = 0
            for file_path in source_files:
                if '_animation.duf' in file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            json_start = content.find('{')
                            if json_start == -1:
                                continue
                            data = json.loads(content[json_start:])
                            animations = data.get('scene', {}).get('animations', [])
                            for anim in animations:
                                keys = anim.get('keys', [])
                                if len(keys) != 1:
                                    total_frames += len(keys)
                                    break
                    except Exception:
                        continue
            return total_frames

        total_images = None
        try:
            if source_files:
                total_images = find_total_images(source_files)
        except Exception:
            total_images = None
        if total_images is not None:
            # TODO: This should be read from the JSON of the _subject files.
            total_images *= 16
            # If Render Shadows is checked, double the total images
            if render_shadows_var.get():
                total_images *= 2
            output_total_images.config(text=f"Total Images to Render: {total_images}")
        else:
            output_total_images.config(text="Total Images to Render: ")

        # Check if any DAZ Studio instances are running
        daz_running = False
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and 'DAZStudio' in proc.info['name']:
                        daz_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        # Show confirmation dialog if DAZ Studio is running
        if daz_running:
            from tkinter import messagebox
            result = messagebox.askyesno(
                "DAZ Studio Running", 
                "DAZ Studio is already running.\n\nDo you want to continue?",
                icon="warning"
            )
            if not result:
                update_console('Start Render cancelled - DAZ Studio running')
                logging.info('Start Render cancelled by user - DAZ Studio running')
                return

        logging.info('Start Render button clicked')
        update_console('Start Render button clicked')
        # Hardcoded Daz Studio Executable Path
        daz_executable_path = os.path.join(
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            "DAZ 3D", "DAZStudio4", "DAZStudio.exe"
        )
        # Use local scripts directory if running in VS Code (not frozen), else use user-writable scripts directory
        if getattr(sys, 'frozen', False):
            install_dir = os.path.dirname(sys.executable)
            appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
            user_scripts_dir = os.path.join(appdata, 'Overlord', 'scripts')
            os.makedirs(user_scripts_dir, exist_ok=True)
            render_script_path = os.path.join(user_scripts_dir, "masterRenderer.dsa").replace("\\", "/")
            install_script_path = os.path.join(install_dir, "scripts", "masterRenderer.dsa")
            try:
                if (not os.path.exists(render_script_path)) or (
                    os.path.getmtime(install_script_path) > os.path.getmtime(render_script_path)):
                    import shutil
                    shutil.copy2(install_script_path, render_script_path)
                    logging.info(f'Copied masterRenderer.dsa to user scripts dir: {render_script_path}')
                    update_console('Copied masterRenderer.dsa to scripts dir')
            except Exception as e:
                logging.error(f'Could not copy masterRenderer.dsa to user scripts dir: {e}')
                update_console(f'Error copying script: {e}')
            # Path to masterTemplate.duf in appData
            template_path = os.path.join(appdata, 'Overlord', 'templates', 'masterTemplate.duf').replace("\\", "/")
        else:
            # Use scripts directly from the repository for development/VS Code preview
            install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            render_script_path = os.path.join(install_dir, "scripts", "masterRenderer.dsa").replace("\\", "/")
            template_path = os.path.join(install_dir, "templates", "masterTemplate.duf").replace("\\", "/")
        # Use "Source Files" and treat as files
        source_files = value_entries["Source Files"].get("1.0", tk.END).strip().replace("\\", "/").split("\n")
        source_files = [file for file in source_files if file]  # Remove empty lines
        source_files = json.dumps(source_files)
        image_output_dir = value_entries["Output Directory"].get().replace("\\", "/")
        num_instances = value_entries["Number of Instances"].get()
        log_size = value_entries["Log File Size (MBs)"].get()
        log_size = int(log_size) * 1000000  # Convert MBs to bytes
        frame_rate = value_entries["Frame Rate"].get()

        try:
            num_instances_int = int(num_instances)
        except Exception:
            num_instances_int = 1

        # Add render_shadows and close_daz_on_finish to json_map
        render_shadows = render_shadows_var.get()
        close_daz_on_finish = close_daz_on_finish_var.get()
        json_map = (
            f'{{'
            f'"num_instances": "{num_instances}", '
            f'"image_output_dir": "{image_output_dir}", '
            f'"frame_rate": "{frame_rate}", '
            f'"source_files": {source_files}, '
            f'"template_path": "{template_path}", '
            f'"render_shadows": {str(render_shadows).lower()}, '
            f'"close_daz_on_finish": {str(close_daz_on_finish).lower()}'
            f'}}'
        )

        def run_instance():
            logging.info('Launching Daz Studio render instance')
            update_console('Launching Daz Studio instance...')
            command = [
                daz_executable_path,
                "-scriptArg", json_map,
                "-instanceName", "#",  # Hardcoded value
                "-logSize", str(log_size),
                "-noPrompt",           # Always add -noPrompt
                render_script_path
            ]
            logging.info(f'Command executed: {command}')
            try:
                subprocess.Popen(command)
                logging.info('Daz Studio instance started successfully')
                update_console('Daz Studio instance started')
            except Exception as e:
                logging.error(f'Failed to start Daz Studio instance: {e}')
                update_console(f'Failed to start instance: {e}')
        def run_all_instances(i=0):
            if i < num_instances_int:
                run_instance()
                root.after(5000, lambda: run_all_instances(i + 1))
            else:
                logging.info('All render instances launched')
                update_console(f'All {num_instances_int} instances launched')
                root.after(1000, show_last_rendered_image)  # Update image after render

        run_all_instances()
        # If "Close Overlord After Starting Render" is checked, close after 2 seconds
        if close_after_render_var.get():
            def delayed_close():
                cleanup_manager.cleanup_all()
                root.quit()
                root.destroy()
            root.after(2000, delayed_close)

    def end_all_daz_studio():
        logging.info('End all Daz Studio Instances button clicked')
        update_console('Ending all Daz Studio instances...')
        killed = 0
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and 'DAZStudio' in proc.info['name']:
                        proc.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            main.dazstudio_killed_by_user = True
            logging.info(f'Killed {killed} DAZStudio process(es)')
            update_console(f'Killed {killed} DAZStudio process(es)')
        except Exception as e:
            logging.error(f'Failed to kill DAZStudio processes: {e}')
            update_console(f'Failed to kill processes: {e}')
        # Reset progress and time labels, and total images label (always reset regardless of error)
        output_total_images.config(text="Total Images to Render: ")
        images_remaining_var.set("Images remaining: --")
        estimated_time_remaining_var.set("Estimated time remaining: --")
        estimated_completion_at_var.set("Estimated completion at: --")
        progress_var.set(0)

    # --- Console Area Setup (early in the code) ---
    console_frame = tk.Frame(root)
    console_frame.place(relx=0.01, rely=0.85, anchor="nw", width=850, height=120)
    theme_manager.register_widget(console_frame, "frame")
    
    console_text = tk.Text(console_frame, width=60, height=6, font=("Consolas", 8), 
                          state=tk.DISABLED, wrap=tk.WORD)
    console_text.pack(fill="both", expand=True)
    theme_manager.register_widget(console_text, "console")
    
    # Store console messages
    console_messages = []
    
    # Get log file path (same as setup_logger)
    appdata = os.environ.get('APPDATA')
    if appdata:
        log_dir = os.path.join(appdata, 'Overlord')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), 'Overlord')
    log_file_path = os.path.join(log_dir, 'log.txt')
    
    # Track log file reading
    log_file_position = 0
    if os.path.exists(log_file_path):
        # Start from end of existing log file
        with open(log_file_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # Seek to end
            log_file_position = f.tell()
    
    def update_console(message):
        console_messages.append(message)
        if len(console_messages) > 5:
            console_messages.pop(0)
        
        console_text.config(state=tk.NORMAL)
        console_text.delete("1.0", tk.END)
        console_text.insert(tk.END, "\n".join(console_messages))
        console_text.config(state=tk.DISABLED)
        console_text.see(tk.END)
    
    def extract_message_from_log_line(line):
        """Extract just the message part from a log line, removing timestamp and level"""
        line = line.strip()
        if not line:
            return None
        
        # Format is: "2025-01-08 12:34:56,789 INFO: message"
        # Find the first colon after the log level
        parts = line.split(' ', 2)  # Split into at most 3 parts
        if len(parts) >= 3:
            # parts[0] = date, parts[1] = time, parts[2] = "LEVEL: message"
            level_and_msg = parts[2]
            if ':' in level_and_msg:
                level, message = level_and_msg.split(':', 1)
                return message.strip()
        
        # Fallback: return the whole line if parsing fails
        return line
    
    def monitor_log_file():
        """Check for new lines in the log file and add them to console"""
        nonlocal log_file_position
        
        try:
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    f.seek(log_file_position)
                    new_lines = f.readlines()
                    log_file_position = f.tell()
                    
                    for line in new_lines:
                        message = extract_message_from_log_line(line)
                        if message:
                            update_console(message)
        except Exception as e:
            # Silently handle file reading errors to avoid spam
            pass
        
        # Schedule next check in 1 second
        root.after(1000, monitor_log_file)

    # Initialize console with startup messages
    update_console(f'Overlord {overlord_version} started')
    update_console('Ready for rendering operations')
    
    # Start monitoring log file
    root.after(2000, monitor_log_file)  # Start after 2 seconds to avoid startup spam

    # Initial display
    root.after(500, show_last_rendered_image)
    root.after(1000, update_output_details)  # Initial output details update
    root.after(2000, periodic_update_output_details)  # Start periodic updates

    # --- Buttons Section ---
    buttons_frame = tk.Frame(root)
    buttons_frame.place(relx=0.0, rely=0.78, anchor="nw")
    theme_manager.register_widget(buttons_frame, "frame")

    button = tk.Button(buttons_frame, text="Start Render", command=start_render, font=("Arial", 16, "bold"), width=16, height=2)
    button.pack(side="left", padx=(20, 10), pady=10)
    theme_manager.register_widget(button, "button")

    end_button = tk.Button(
        buttons_frame,
        text="End all Daz Studio Instances",
        command=end_all_daz_studio,
        font=("Arial", 16, "bold"),
        width=26,
        height=2
    )
    end_button.pack(side="left", padx=10, pady=10)
    theme_manager.register_widget(end_button, "button")

    def zip_outputted_files():
        logging.info('Zip Outputted Files button clicked')
        update_console('Zip Outputted Files button clicked')
        
        # Check if any DAZ Studio instances are running
        daz_running = False
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and 'DAZStudio' in proc.info['name']:
                        daz_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        # Show confirmation dialog if DAZ Studio is running
        if daz_running:
            from tkinter import messagebox
            result = messagebox.askyesno(
                "DAZ Studio Running", 
                "DAZ Studio is currently running. Archiving while rendering may cause issues.\n\nDo you want to continue anyway?",
                icon="warning"
            )
            if not result:
                update_console('Archive cancelled - DAZ Studio running')
                logging.info('Archive cancelled by user - DAZ Studio running')
                return
        
        try:
            output_dir = value_entries["Output Directory"].get()
            archive_all_inner_folders(output_dir)
            logging.info(f'Archiving completed for: {output_dir}')
            update_console('Archiving completed successfully')
        except Exception as e:
            logging.error(f'Failed to archive output files: {e}')
            update_console(f'Failed to archive output files: {e}')

    zip_button = tk.Button(
        buttons_frame,
        text="Zip Outputted Files",
        command=zip_outputted_files,
        font=("Arial", 16, "bold"),
        width=18,
        height=2
    )
    zip_button.pack(side="left", padx=10, pady=10)
    theme_manager.register_widget(zip_button, "button")

    # Run the application
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info('Application interrupted by user')
    finally:
        # Ensure cleanup happens even if mainloop exits abnormally
        cleanup_manager.cleanup_all()
        logging.info('Application cleanup completed')

if __name__ == "__main__":
    main()