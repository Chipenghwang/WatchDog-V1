import os
import shutil
import time
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from tqdm import tqdm

class MyEventHandler(FileSystemEventHandler):
    def __init__(self, src_path, dest_path):
        self.src_path = src_path
        self.dest_path = dest_path

    def on_any_event(self, event: FileSystemEvent) -> None:
        try:
            relative_path = os.path.relpath(event.src_path, self.src_path)
            dest_path = os.path.join(self.dest_path, relative_path)

            with tqdm(total=1, desc=f"Handling {event.event_type} event") as pbar:
                if event.event_type == 'created':
                    if os.path.isdir(event.src_path):
                        os.makedirs(dest_path, exist_ok=True)
                        print(f"Directory created: {event.src_path} -> {dest_path}")
                    else:
                        shutil.copy2(event.src_path, dest_path)
                        print(f"File created: {event.src_path} -> {dest_path}")
                elif event.event_type == 'modified':
                    if not os.path.isdir(event.src_path):
                        shutil.copy2(event.src_path, dest_path)
                        print(f"File modified: {event.src_path} -> {dest_path}")
                elif event.event_type == 'deleted':
                    if os.path.isdir(dest_path):
                        shutil.rmtree(dest_path)
                        print(f"Directory deleted: {dest_path}")
                    else:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                            print(f"File deleted: {dest_path}")
                elif event.event_type == 'moved':
                    new_dest_path = os.path.join(self.dest_path, os.path.relpath(event.dest_path, self.src_path))
                    shutil.move(dest_path, new_dest_path)
                    print(f"Moved: {event.src_path} -> {new_dest_path}")
                pbar.update(1)
        except Exception as e:
            print(f"Error handling event {event.event_type} for {event.src_path}: {e}")

def sync_folders_with_progress(src, dest):
    src_files = []
    for src_dir, _, files in os.walk(src):
        for file in files:
            src_files.append(os.path.join(src_dir, file))

    with tqdm(total=len(src_files), desc="Syncing from src to dest") as pbar:
        for src_dir, _, files in os.walk(src):
            relative_dir = os.path.relpath(src_dir, src)
            dest_dir = os.path.join(dest, relative_dir)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            for file in files:
                src_file = os.path.join(src_dir, file)
                dest_file = os.path.join(dest_dir, file)
                if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                    shutil.copy2(src_file, dest_file)
                pbar.update(1)

    dest_files = []
    for dest_dir, _, files in os.walk(dest):
        for file in files:
            dest_files.append(os.path.join(dest_dir, file))

    with tqdm(total=len(dest_files), desc="Syncing from dest to src") as pbar:
        for dest_dir, _, files in os.walk(dest):
            relative_dir = os.path.relpath(dest_dir, dest)
            src_dir = os.path.join(src, relative_dir)
            if not os.path.exists(src_dir):
                os.makedirs(src_dir)
            for file in files:
                dest_file = os.path.join(dest_dir, file)
                src_file = os.path.join(src_dir, file)
                if not os.path.exists(src_file) or os.path.getmtime(dest_file) > os.path.getmtime(src_file):
                    shutil.copy2(dest_file, src_file)
                pbar.update(1)

event_handler = MyEventHandler("A", "B")
observer = Observer()

# Sync folders with progress before starting the observer
sync_folders_with_progress("A", "B")
sync_folders_with_progress("B", "A")

observer.schedule(event_handler, "A", recursive=True)

observer.start()
try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
