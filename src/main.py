import os
import shutil
import time
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from tqdm import tqdm
import configparser

class MyEventHandler(FileSystemEventHandler):
    """
    文件系统事件处理程序类，用于处理文件系统事件并执行相应的操作。

    Attributes:
        src_path (str): 源路径，监视的目录路径。
        dest_path (str): 目标路径，事件处理后文件或目录的目标路径。

    Methods:
        on_any_event(event: FileSystemEvent) -> None:
            处理任何文件系统事件，根据事件类型执行相应的操作。
            参数:
                event (FileSystemEvent): 文件系统事件对象，包含事件类型和源路径等信息。
    """
    def __init__(self, src_path, dest_path):
        self.src_path = src_path # 源路径
        self.dest_path = dest_path # 目标路径

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        处理任何文件系统事件（创建、修改、删除、移动）。

        参数:
            event (FileSystemEvent): 要处理的文件系统事件。

        异常:
            Exception: 处理事件时发生错误。

        事件类型:
            - 'created': 处理文件和目录的创建。
            - 'modified': 处理文件的修改。
            - 'deleted': 处理文件和目录的删除。
            - 'moved': 处理文件和目录的移动。

        操作:
            - 对于 'created' 事件，创建目录或将文件复制到目标路径。
            - 对于 'modified' 事件，将修改后的文件复制到目标路径。
            - 对于 'deleted' 事件，从目标路径中删除目录或文件。
            - 对于 'moved' 事件，将文件或目录移动到新的目标路径。

        进度:
            显示每个事件处理的进度条。
        """
        try:
            relative_path = os.path.relpath(event.src_path, self.src_path)
            dest_path = os.path.join(self.dest_path, relative_path)

            with tqdm(total=1, desc=f"Handling {event.event_type} event") as pbar:
                # 创建事件
                if event.event_type == 'created':
                    if os.path.isdir(event.src_path):
                        os.makedirs(dest_path, exist_ok=True)
                        print(f"Directory created: {event.src_path} -> {dest_path}")
                    else:
                        shutil.copy2(event.src_path, dest_path)
                        print(f"File created: {event.src_path} -> {dest_path}")

                # 修改事件
                elif event.event_type == 'modified':
                    if not os.path.isdir(event.src_path):
                        shutil.copy2(event.src_path, dest_path)
                        print(f"File modified: {event.src_path} -> {dest_path}")

                # 删除事件
                elif event.event_type == 'deleted':
                    if os.path.isdir(dest_path):
                        shutil.rmtree(dest_path)
                        print(f"Directory deleted: {dest_path}")
                    else:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                            print(f"File deleted: {dest_path}")

                # 移动事件
                elif event.event_type == 'moved':
                    new_dest_path = os.path.join(self.dest_path, os.path.relpath(event.dest_path, self.src_path))
                    shutil.move(dest_path, new_dest_path)
                    print(f"Moved: {event.src_path} -> {new_dest_path}")
                pbar.update(1) # 更新进度条

        except Exception as e:
            print(f"Error handling event {event.event_type} for {event.src_path}: {e}")

# 同步文件夹并显示进度
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

def read_ini(ini_path='./config.ini'):
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read(ini_path)

    # 获取 server1 和 server2 的 folder 参数
    server1_folder = config.get('server1', 'folder')
    server2_folder = config.get('server2', 'folder')

    return server1_folder, server2_folder

# 读取配置文件
server1_folder, server2_folder = read_ini()
event_handler = MyEventHandler(server1_folder, server2_folder) # 创建事件处理程序对象
observer = Observer() # 创建观察者对象

# 同步文件夹 A 和 B
sync_folders_with_progress(server1_folder, server2_folder) # 同步 A 到 B
sync_folders_with_progress(server2_folder, server1_folder) # 同步 B 到 A

observer.schedule(event_handler, server1_folder, recursive=True) # 监视 A 目录
observer.start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()