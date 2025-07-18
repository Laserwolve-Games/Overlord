import tkinter as tk
from tkinter import filedialog
import os
import subprocess
import sys
import webbrowser
import json
from PIL import Image, ImageTk
import psutil
import logging
from version import __version__ as overlord_version

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
    logging.info('Application launched')
    # Create the main window
    root = tk.Tk()
    root.title(f"Overlord {overlord_version}")
    root.iconbitmap(resource_path(os.path.join("images", "favicon.ico")))  # Set the application icon

    # ...existing code...

    # Maximize the application window
    root.state("zoomed")

    # Load and display the logo image
    logo = tk.PhotoImage(file=resource_path(os.path.join("images", "overlordLogo.png")))
    logo_label = tk.Label(root, image=logo, cursor="hand2")
    logo_label.image = logo  # Keep a reference to avoid garbage collection
    logo_label.place(anchor="nw", x=10, y=10)  # Place in upper left corner, 10px down and right

    # Add Laserwolve Games logo to upper right corner
    lwg_logo = tk.PhotoImage(file=resource_path(os.path.join("images", "laserwolveGamesLogo.png")))
    lwg_logo_label = tk.Label(root, image=lwg_logo, cursor="hand2")
    lwg_logo_label.image = lwg_logo  # Keep a reference to avoid garbage collection
    # Place in upper right using place geometry manager
    lwg_logo_label.place(anchor="nw", x=700)
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
    param_table_frame = tk.Frame(root)
    param_table_frame.pack(pady=(20, 10), anchor="nw", side="top")  # 20px down from file_table_frame

    # File/folder path parameters
    file_params = [
        "Source Sets",
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

        if param == "Source Sets":
            text_widget = tk.Text(file_table_frame, width=80, height=5, font=("Consolas", 10))  # Changed height to 5
            text_widget.grid(row=i+1, column=1, padx=10, pady=5, sticky="e")
            def browse_folders_append():
                # Start in user's Documents directory
                documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
                foldername = filedialog.askdirectory(
                    initialdir=documents_dir,
                    title="Select Source Set Folder"
                )
                # askdirectory only allows one folder at a time, so allow multiple by repeated selection
                if foldername:
                    foldername = foldername.replace('/', '\\')
                    current = text_widget.get("1.0", tk.END).strip().replace('/', '\\')
                    current_folders = set(current.split("\n")) if current else set()
                    if foldername not in current_folders:
                        if current:
                            text_widget.insert(tk.END, "\n" + foldername)
                        else:
                            text_widget.insert(tk.END, foldername)
            # Place Browse and Clear buttons vertically, aligned to the top right of the text box
            button_frame = tk.Frame(file_table_frame)
            button_frame.grid(row=i+1, column=2, padx=5, pady=5, sticky="n")

            browse_button = tk.Button(
                button_frame,
                text="Browse",
                command=browse_folders_append,
                width=8
            )
            browse_button.pack(side="top", fill="x", pady=(0, 2))

            def clear_source_sets():
                text_widget.delete("1.0", tk.END)
            clear_button = tk.Button(
                button_frame,
                text="Clear",
                command=clear_source_sets,
                width=8
            )
            clear_button.pack(side="top", fill="x")
            value_entries[param] = text_widget
        elif param == "Output Directory":
            value_entry = tk.Entry(file_table_frame, width=80, font=("Consolas", 10))
            default_img_dir = os.path.join(
                os.path.expanduser("~"),
                "Downloads", "output"
            )
            value_entry.insert(0, default_img_dir)
            value_entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="e")

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
            value_entries[param] = value_entry




    # Short/simple parameters table
    for i, param in enumerate(param_params):
        param_label = tk.Label(param_table_frame, text=param, font=("Arial", 10), anchor="w")
        param_label.grid(row=i+1, column=0, padx=10, pady=5, sticky="w")

        value_entry = tk.Entry(param_table_frame, width=5, font=("Consolas", 10))
        if param == "Number of Instances":
            value_entry.insert(0, "1")
        elif param == "Log File Size (MBs)":
            value_entry.insert(0, "100")
        elif param == "Frame Rate":
            value_entry.insert(0, "30")
        value_entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="e")
        value_entries[param] = value_entry

    # Add "Render shadows" label and checkbox under Log File Size
    render_shadows_var = tk.BooleanVar(value=True)
    # Label aligned under "Log File Size" label (column 0)
    render_shadows_label = tk.Label(param_table_frame, text="Render shadows", font=("Arial", 10), anchor="w")
    render_shadows_label.grid(row=len(param_params)+1, column=0, padx=10, pady=(0, 0), sticky="w")
    # Checkbox aligned under input boxes (column 1)
    render_shadows_checkbox = tk.Checkbutton(
        param_table_frame,
        variable=render_shadows_var,
        width=2,
        anchor="w"
    )
    render_shadows_checkbox.grid(row=len(param_params)+1, column=1, padx=10, pady=(0, 5), sticky="w")

    # --- Last Rendered Image Section ---
    right_frame = tk.Frame(root)
    right_frame.place(relx=0.73, rely=0.0, anchor="n", width=1024, height=1024)

    right_frame.config(highlightbackground="black", highlightthickness=1)

    # Place img_label directly in right_frame
    img_label = tk.Label(right_frame)
    img_label.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)

    # --- Image Details Column ---
    # Place details_frame to the right of param_table_frame
    details_frame = tk.Frame(root, width=350)
    details_frame.place(relx=0.25, rely=0.6, anchor="nw", width=350, height=200)
    details_frame.pack_propagate(False)

    details_title = tk.Label(details_frame, text="Last Rendered Image Details", font=("Arial", 14, "bold"))
    details_title.pack(anchor="nw", pady=(0, 10))

    # Show only the path (no "Path: " prefix)
    details_path = tk.Label(details_frame, text="", font=("Consolas", 9), wraplength=330, justify="left")
    details_path.pack(anchor="nw", pady=(0, 5))

    # Add a button to copy the path to clipboard
    def copy_path_to_clipboard():
        path = details_path.cget("text")
        if path:
            root.clipboard_clear()
            root.clipboard_append(path)
            root.update()  # Keeps clipboard after window closes

    copy_btn = tk.Button(details_frame, text="Copy Path", command=copy_path_to_clipboard, font=("Arial", 9))
    copy_btn.pack(anchor="nw", pady=(0, 8))

    details_size = tk.Label(details_frame, text="Size: ", font=("Arial", 10))
    details_size.pack(anchor="nw", pady=(0, 5))
    details_dim = tk.Label(details_frame, text="Dimensions: ", font=("Arial", 10))
    details_dim.pack(anchor="nw", pady=(0, 5))


    # --- Output Details Column ---
    output_details_frame = tk.Frame(root, width=350)
    output_details_frame.place(relx=0.01, rely=0.6, anchor="nw", width=350, height=200)
    output_details_frame.pack_propagate(False)

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
    estimated_time_remaining_label = tk.Label(
        root,
        textvariable=estimated_time_remaining_var,
        font=("Arial", 10, "bold"),
        anchor="e",
        justify="center"
    )
    estimated_completion_at_label = tk.Label(
        root,
        textvariable=estimated_completion_at_var,
        font=("Arial", 10, "bold"),
        anchor="e",
        justify="right"
    )
    images_remaining_label.place(relx=0.01, rely=0.55, anchor="nw", width=250, height=18)
    estimated_time_remaining_label.place(relx=0.11, rely=0.55, anchor="nw", width=250, height=18)
    estimated_completion_at_label.place(relx=0.245, rely=0.55, anchor="nw", width=400, height=18)

    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
    # Place the progress bar just above the output_details_frame, matching its width and alignment
    progress_bar.place(relx=0.01, rely=0.57, anchor="nw", width=850, height=18)

    output_details_title = tk.Label(output_details_frame, text="Output Details", font=("Arial", 14, "bold"))
    output_details_title.pack(anchor="nw", pady=(0, 10))

    output_folder_size = tk.Label(output_details_frame, text="Folder Size: ", font=("Arial", 10))
    output_folder_size.pack(anchor="nw", pady=(0, 5))
    output_png_count = tk.Label(output_details_frame, text="PNG Files: ", font=("Arial", 10))
    output_png_count.pack(anchor="nw", pady=(0, 5))
    output_zip_count = tk.Label(output_details_frame, text="ZIP Files: ", font=("Arial", 10))
    output_zip_count.pack(anchor="nw", pady=(0, 5))

    output_folder_count = tk.Label(output_details_frame, text="Sub-folders: ", font=("Arial", 10))
    output_folder_count.pack(anchor="nw", pady=(0, 5))

    # Add Total Images to Render label (updated only on Start Render)
    output_total_images = tk.Label(output_details_frame, text="Total Images to Render: ", font=("Arial", 10))
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
                # First, verify the image integrity
                with Image.open(newest_img_path) as verify_img:
                    verify_img.verify()  # Will raise if the image is incomplete or corrupt
                # If verification passes, reopen for display
                img = Image.open(newest_img_path).convert("RGBA")  # Ensure image is in RGBA mode
                # Handle transparency by adding a white background
                bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(bg, img)
                orig_img = Image.open(newest_img_path)
                width, height = orig_img.size
                file_size = os.path.getsize(newest_img_path)
                # Always display path with Windows separators
                details_path.config(text=newest_img_path.replace('/', '\\'))  # No "Path: " prefix
                details_dim.config(text=f"Dimensions: {width} x {height}")
                details_size.config(text=f"Size: {file_size/1024:.1f} KB")
                tk_img = ImageTk.PhotoImage(img)
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
            img_label.config(image="")
            img_label.image = None
            details_path.config(text="")
            details_dim.config(text="Dimensions: ")
            details_size.config(text="Size: ")
            no_img_label.lift()
            if not getattr(show_last_rendered_image, 'last_no_img_logged', False):
                logging.info('No images found in output directory or all images failed to load')
                show_last_rendered_image.last_no_img_logged = True
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
        source_sets = value_entries["Source Sets"].get("1.0", tk.END).strip().replace("\\", "/").split("\n")
        source_sets = [folder for folder in source_sets if folder]
        output_dir = value_entries["Output Directory"].get().strip()
        if not source_sets:
            from tkinter import messagebox
            messagebox.showerror("Missing Source Sets", "Please specify at least one Source Set before starting the render.")
            update_console("Start Render cancelled: No Source Sets specified.")
            logging.info("Start Render cancelled: No Source Sets specified.")
            return
        if not output_dir:
            from tkinter import messagebox
            messagebox.showerror("Missing Output Directory", "Please specify an Output Directory before starting the render.")
            update_console("Start Render cancelled: No Output Directory specified.")
            logging.info("Start Render cancelled: No Output Directory specified.")
            return

        # Calculate and display total images to render (update label)
        def find_total_images(source_sets):
            total_frames = 0
            for set_dir in source_sets:
                for root, dirs, files in os.walk(set_dir):
                    for fname in files:
                        if '_animation.duf' in fname:
                            try:
                                fpath = os.path.join(root, fname)
                                with open(fpath, 'r', encoding='utf-8') as f:
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
            if source_sets:
                total_images = find_total_images(source_sets)
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
        # Use "Source Sets" and treat as folders
        source_sets = value_entries["Source Sets"].get("1.0", tk.END).strip().replace("\\", "/").split("\n")
        source_sets = [folder for folder in source_sets if folder]  # Remove empty lines
        source_sets = json.dumps(source_sets)
        image_output_dir = value_entries["Output Directory"].get().replace("\\", "/")
        num_instances = value_entries["Number of Instances"].get()
        log_size = value_entries["Log File Size (MBs)"].get()
        log_size = int(log_size) * 1000000  # Convert MBs to bytes
        frame_rate = value_entries["Frame Rate"].get()

        try:
            num_instances_int = int(num_instances)
        except Exception:
            num_instances_int = 1

        # Add render_shadows to json_map
        render_shadows = render_shadows_var.get()
        json_map = (
            f'{{'
            f'"num_instances": "{num_instances}", '
            f'"image_output_dir": "{image_output_dir}", '
            f'"frame_rate": "{frame_rate}", '
            f'"source_sets": {source_sets}, '
            f'"template_path": "{template_path}", '
            f'"render_shadows": {str(render_shadows).lower()}'
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
    
    console_text = tk.Text(console_frame, width=60, height=6, font=("Consolas", 8), 
                          state=tk.DISABLED, wrap=tk.WORD, bg="#f0f0f0")
    console_text.pack(fill="both", expand=True)
    
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

    button = tk.Button(buttons_frame, text="Start Render", command=start_render, font=("Arial", 16, "bold"), width=16, height=2)
    button.pack(side="left", padx=(20, 10), pady=10)

    end_button = tk.Button(
        buttons_frame,
        text="End all Daz Studio Instances",
        command=end_all_daz_studio,
        font=("Arial", 16, "bold"),
        width=26,
        height=2
    )
    end_button.pack(side="left", padx=10, pady=10)

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
            # Use the same logic as for finding the script path
            if getattr(sys, 'frozen', False):
                install_dir = os.path.dirname(sys.executable)
                archive_script_path = os.path.join(install_dir, "scripts", "archiveFiles.py")
            else:
                install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                archive_script_path = os.path.join(install_dir, "scripts", "archiveFiles.py")
            subprocess.Popen([
                sys.executable,
                archive_script_path,
                value_entries["Output Directory"].get()
            ])
            logging.info(f'archiveFiles.py started with argument: {value_entries["Output Directory"].get()}')
            update_console('Archive process started successfully')
        except Exception as e:
            logging.error(f'Failed to execute archiveFiles.py: {e}')
            update_console(f'Failed to execute archiveFiles.py: {e}')

    zip_button = tk.Button(
        buttons_frame,
        text="Zip Outputted Files",
        command=zip_outputted_files,
        font=("Arial", 16, "bold"),
        width=18,
        height=2
    )
    zip_button.pack(side="left", padx=10, pady=10)

    # Run the application
    root.mainloop()

if __name__ == "__main__":
    main()