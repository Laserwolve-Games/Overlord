import os
import zipfile
import sys
import logging

# Setup logging to match overlord.py
def setup_logger():
    appdata = os.environ.get('APPDATA')
    if appdata:
        log_dir = os.path.join(appdata, 'Overlord')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), 'Overlord')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'log.txt')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler()]
    )


import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

setup_logger()
logging.info('archiveFiles.py started')

base_path = sys.argv[1]

# Collect all (inner_path, archive_path) pairs to process
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

# Use ThreadPoolExecutor to archive in parallel
max_workers = min(8, os.cpu_count() or 1)
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(archive_and_delete, inner_path, archive_path) for inner_path, archive_path in to_archive]
    for future in as_completed(futures):
        pass  # All logging is handled in the function