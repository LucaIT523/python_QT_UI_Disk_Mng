from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QStackedWidget,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QSizePolicy,
    QDialog,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QFileDialog,
)
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtCore import Qt
import os
import sys
import re
import subprocess
import psutil  # Library to access system information
from Crypto.Hash import SHA256
import sqlite3
from sqlite3 import Error

app_title = "Disk Manager"
app_version = "1.0.0.1"
copyright = "Copyright © 2005 - 2024 Anas Boss,\n Inc. All rights reserved."
app_build = "10/17/2024"
contact_info = "+1-212-456-7890"
res_path = os.path.join(os.path.dirname(__file__), 'res')
if hasattr(sys, '_MEIPASS'):
    res_path = os.path.join(sys._MEIPASS, 'res')
class ProcessWorker_shell(QtCore.QThread):
    output_received = QtCore.pyqtSignal(str)
    error_received = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)

    def __init__(self, command):
        super().__init__()
        self.command = command
        #print(self.command)

    def run(self):
        try:
            process = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Read stdout
            for stdout_line in iter(process.stdout.readline, b''):
                self.output_received.emit(stdout_line.decode().strip())
            # Read stderr
            for stderr_line in iter(process.stderr.readline, b''):
                if stderr_line and stderr_line.decode().strip() !='':
                    self.error_received.emit(f"{stderr_line.decode().strip()}")
            process.stdout.close()
            process.stderr.close()
            process.wait()
                # Emit the finished signal with the return code
            self.finished.emit(process.returncode)
        except Exception as e:
            self.error_received.emit(f"Execution Error: {e}")

    def stop(self):
        if self.process:
            self.process.terminate()  
            self.process.wait()  
            self.finished.emit(1)

class ProcessWorker(QtCore.QThread):
    output_received = QtCore.pyqtSignal(str)
    error_received = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        self.cmd_stop = False
        #print(self.command)

    def run(self):
        try:
            self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Read stdout
            for stdout_line in iter(self.process.stdout.readline, b''):
                self.output_received.emit(stdout_line.decode().strip())
            # Read stderr
            for stderr_line in iter(self.process.stderr.readline, b''):
                if stderr_line and stderr_line.decode().strip() !='':
                    self.error_received.emit(f" {stderr_line.decode().strip()}")
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.wait()
            if self.cmd_stop:
                self.finished.emit(1)
            else:
                self.finished.emit(self.process.returncode)
        except Exception as e:
            self.error_received.emit(f"Execution Error: {e}")
    def stop(self):
        if self.process:
            self.cmd_stop = True
            self.process.kill() 
            self.process.wait()  
            #self.finished.emit(1)

class DiskManager: 
    def run_command(self, command):
        if not command:
            return False
        try:
            subprocess.check_call(command)
            #print(f"{command} is completed.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False   
    def run_command_shell(self, command):
        if not command:
            return False
        try:
            subprocess.check_call(command, shell=True)
            #print(f"{command} is completed.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False  
    def is_mount_point(self, mountpoint):
        """Check if the given mountpoint is currently mounted."""
        if not mountpoint:  # Check if the mountpoint is valid
            #print("Mountpoint is empty.")
            return False        
        try:
            # Use findmnt to check if the mountpoint exists
            output = subprocess.check_output(['sudo', 'findmnt', mountpoint], text=True)
            if not output.strip():
                return False
            #print(f"{mountpoint} exists.")
            return True  # If no exception was raised, the mountpoint is valid
        except subprocess.CalledProcessError as e:
            # If findmnt fails, it means the mountpoint is not mounted
            #print(f"{mountpoint} does not exist.")
            return False

    def umount_point(self, mountpoint):
        """Unmount the given mountpoint if it is mounted."""
        try:
            if self.is_mount_point(mountpoint):
                # Call umount to unmount the mountpoint
                subprocess.check_call(['sudo', 'umount', mountpoint])
                #print(f"{mountpoint} has been unmounted.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False
    
    def xmount_image(self, image_path, cache_path, mountpoint):
        # Check if the mount point directory exists, and create it if it doesn't
        if not os.path.exists(mountpoint):
            try:
                subprocess.run(["sudo", "mkdir", "-p", mountpoint], check=True)  # Create the directory
            except subprocess.CalledProcessError as e:
                print(f"Except Error: {str(e)}")
                return False
        cache_dir = os.path.dirname(cache_path)
        if not os.path.exists(cache_dir):
            try:
                subprocess.run(["sudo", "mkdir", "-p", cache_dir], check=True)  # Create the directory
            except subprocess.CalledProcessError as e:
                print(f"Except Error: {str(e)}")
                return False
        self.umount_point(mountpoint)
        command = [
            'sudo', 'xmount', 
            '--in', 'ewf', 
            '--out', 'vdi', 
            '--cache', cache_path, 
            image_path, 
            mountpoint
        ]
        #print(command)
        try:
            subprocess.check_call(command)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False

    def mount_device(self, device, mountpoint):
        # Check if the mount point directory exists, and create it if it doesn't
        if not os.path.exists(mountpoint):
            try:
                subprocess.run(["sudo", "mkdir", "-p", mountpoint], check=True)  # Create the directory
            except subprocess.CalledProcessError as e:
                print(f"Except Error: {str(e)}")
                return False
        self.umount_point(mountpoint)
        try:
            subprocess.check_call(['sudo', 'mount', device, mountpoint])
            #print(f"{device} is mounted on {mountpoint}.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False
    
    def mount_image(self, image, mountpoint):
        # Check if the mount point directory exists, and create it if it doesn't
        if not os.path.exists(mountpoint):
            try:
                subprocess.run(["sudo", "mkdir", "-p", mountpoint], check=True)  # Create the directory
            except subprocess.CalledProcessError as e:
                print(f"Except Error: {str(e)}")
                return False
        self.umount_point(mountpoint)
        try:
            subprocess.check_call(['sudo', 'ewfmount', image, mountpoint], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            #print(f"{image} is mounted on {mountpoint}.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False

    def find_loops(self, file_path):
        try:
            # Run the 'losetup -a' command and capture the output
            result = subprocess.run(['sudo', 'losetup', '-a'], capture_output=True, text=True, check=True)            
            # Filter the lines that contain the file_path
            loops = []
            for line in result.stdout.splitlines():
                if file_path in line:
                    loop_device = line.split(':')[0]
                    loops.append(loop_device)            
            return loops
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {e}")
            return []

    def loop_setup_file(self, file_path):
        if not file_path:
            return None
        try: # sudo losetup --find --show /mnt/ewf/ewf1
            device = subprocess.check_output(['sudo', 'losetup', '--find', '--show', file_path], text=True)
            if not device.strip():
                #print(f"{file_path} cannot be set up as a loop device.")
                return None
            #print(f"{file_path} is set to {device}.")
            return device.split('\n')[0]  # /dev/loop0
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return None

    def loop_remove(self, device):
        if not device:
            return False
        try: # sudo losetup -d /dev/loop0
            subprocess.run(["sudo", "losetup", "-d", device], check=True)
            #print(f"{device} is un setup.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False
    
    def check_VBox_exists(self, disk_path):
        try:
            result = subprocess.run(['sudo', 'VBoxManage', 'list', 'hdds'], capture_output=True, text=True, check=True)
            if disk_path in result.stdout:
                #print(f"{disk_path} exists.")
                return True
            else:
                #print(f"{disk_path} does not exist.")
                return False
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {e}")
            return False

    def remove_VBox_disks(self, disk_path):
        if self.check_VBox_exists(disk_path):
            try:
                result = subprocess.run(['sudo', 'VBoxManage', 'closemedium', 'disk', disk_path, '--delete'], 
                                        capture_output=True, text=True, check=True)
                #print(f"{disk_path} has been removed.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Except Error: {e}")
                return False
        else:            
            return True

    def get_os_user(self):
        current_user = os.getlogin()
        return current_user

    def get_os_user_env(self):
        current_user = os.getenv("USER")
        return current_user

    def get_os_user_pwuid(self):
        import pwd
        current_user = pwd.getpwuid(os.getuid())[0]
        return current_user

    def change_ownership(self, user, path):
        try:
            command = ['sudo', 'chown', user, path]
            result = subprocess.run(command, capture_output=True, text=True, check=True)            
            #print(f"Ownership of '{path}' changed to '{user}' successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {e}")
            return False

    def remove_dir(self, path):
        if not path:
            return False
        try: # sudo rmdir /mnt/ewf
            subprocess.run(["sudo", "rmdir", path], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False

    def remove_file(self, path):
        if not path:
            return False
        try: # sudo rmdir /mnt/ewf
            subprocess.run(["sudo", "rm", path], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return False

    def change_owner(self, user, path):
        if user and path:
            try: # sudo chown ans:ans /dev/loop18
                # subprocess.run(["sudo", "chown", user, ":", user, path], check=True)
                subprocess.run(["sudo", "chown", f"{user}:{user}", path], check=True)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Except Error: {str(e)}")
                return False
        return False

    def find_image_files(self,mountpoint, combo):   
        combo.clear()   
        for root, dirs, files in os.walk(mountpoint):
            for file in files:
                if file.endswith(".E01"):
                    image_name = file
                    image_path = f'{root}/{image_name}'
                    combo.addItem(image_name, image_path)

    def source_devices(self, combo):
        """Populate the combo box with available drives."""
        command = ['lsblk', '-P', '-o', 'NAME,SIZE,LABEL,MODEL,TRAN,TYPE', '-d', '-e', '2,11', '-x', 'NAME']
        try:
            output = subprocess.check_output(command, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return
        regex = re.compile(r'^(x?[hsv][a-z]|mmcblk|nvme)')
        combo.clear()
        for line in output.strip().split('\n'):
            info = {}
            for part in re.findall(r'(\w+)="([^"]*)"', line):
                key, value = part
                info[key] = value
            name = info.get('NAME')
            if name and regex.match(name):
                device_path = f'/dev/{name}'
                size = info.get('SIZE', '')
                model = info.get('MODEL', '')
                display_str = f"{device_path} - Size: {size}"
                if model:
                    display_str += f" - Model: {model}"
                combo.addItem(display_str, device_path)

    def destination_devices(self, combo):
        """Get a list of USB storage devices and populate the combo box."""
        command = ['lsblk', '-P', '-o', 'NAME,SIZE,LABEL,MODEL,TRAN,TYPE,MOUNTPOINT', '-e', '2,11', '-x', 'NAME']
        try:
            output = subprocess.check_output(command, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Except Error: {str(e)}")
            return
        regex = re.compile(r'^(x?[hsv][a-z]|mmcblk|nvme)')
        device_path = None
        combo.clear()
        for line in output.strip().split('\n'):
            info = {}
            for part in re.findall(r'(\w+)="([^"]*)"', line):
                key, value = part
                info[key] = value
            name = info.get('NAME')
            tran = info.get('TRAN')
            size = info.get('SIZE', '')
            model = info.get('MODEL', '')
            types = info.get('TYPE', '')
            mountpoint = info.get('MOUNTPOINT', '')
            if name and regex.match(name) and tran == "usb":
                device_path = f'/dev/{name}'                
                display_str = f"{device_path} - Size: {size}"
                if model:
                    display_str += f" - Model: {model}"
                if types:
                    display_str += f" - Type: {types}"
                if mountpoint:
                    display_str += f" - Mountpoint: {mountpoint}"
                combo.addItem(display_str, device_path)
            elif device_path and regex.match(name) and name.startswith(device_path[5:]):
                drive_path = f'/dev/{name}'                
                display_str = f"{drive_path} - Size: {size}"
                if model:
                    display_str += f" - Model: {model}"
                if types:
                    display_str += f" - Type: {types}"
                if mountpoint:
                    display_str += f" - Mountpoint: {mountpoint}"
                combo.addItem(display_str, drive_path)

    def get_all_disks(self): # ALL_DISKS
        command = ['lsblk', '-o', 'NAME,SIZE,MODEL,TRAN,TYPE', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            physical_disks = []            
            for line in output.splitlines():
                if 'TYPE="disk"' in line and 'SIZE="0B"' not in line:
                    disk_info = {}
                    for part in re.findall(r'(\w+)="([^"]*)"', line):
                        key, value = part
                        disk_info[key] = value                    
                    # Constructing path and info strings
                    path = f'/dev/{disk_info.get("NAME")}'
                    info = f"{path} - Size: {disk_info.get('SIZE')} - Model: {disk_info.get('MODEL')} - Transport: {disk_info.get('TRAN')} - Type: {disk_info.get('TYPE')}"
                    # Append the path and info as a tuple for better structure
                    physical_disks.append((path, info)) 
            return physical_disks
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def get_internal_disks(self): # INTERNAL_DISKS
        command = ['lsblk', '-o', 'NAME,SIZE,MODEL,TRAN,TYPE', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            internal_disks = []
            for line in output.splitlines():
                if 'TYPE="disk"' in line and 'TRAN="usb"' not in line:
                    disk_info = {}
                    for part in re.findall(r'(\w+)="([^"]*)"', line):
                        key, value = part
                        disk_info[key] = value                    
                    path = f'/dev/{disk_info.get("NAME")}'
                    info = f"{path} - Size: {disk_info.get('SIZE')} - Model: {disk_info.get('MODEL')} - Transport: {disk_info.get('TRAN')}"
                    internal_disks.append((path, info))  # Add to list
            
            return internal_disks
        
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def get_external_disks(self): # EXTERNAL_DISKS
        command = ['lsblk', '-o', 'NAME,SIZE,MODEL,TRAN,TYPE', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            external_disks = []                    
            for line in output.splitlines():
                if 'TYPE="disk"' in line and 'TRAN="usb"' in line:  # Check for external transport type
                    disk_info = {}
                    for part in re.findall(r'(\w+)="([^"]*)"', line):
                        key, value = part
                        disk_info[key] = value                    
                    path = f'/dev/{disk_info.get("NAME")}'
                    info = f"{path} - Size: {disk_info.get('SIZE')} - Model: {disk_info.get('MODEL')} - Transport: {disk_info.get('TRAN')}"
                    external_disks.append((path, info))  # Add to list            
            return external_disks        
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def get_all_parts(self): # ALL_PARTS
        command = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            parts = []              
            for line in output.splitlines():
                part_info = {}
                for part in re.findall(r'(\w+)="([^"]*)"', line):
                    key, value = part
                    part_info[key] = value            
                # Check if the type is partition ('part') or LVM ('lvm')
                if part_info.get('TYPE') in ['part', 'lvm']:
                    path = f'/dev/{part_info.get("NAME")}'
                    info = f"{path} - Size: {part_info.get('SIZE')} - Type: {part_info.get('TYPE')}"                
                    # Include mount point if it exists
                    if part_info.get('MOUNTPOINT'):
                        info += f" - Mountpoint: {part_info.get('MOUNTPOINT')}"                
                    parts.append((path, info))  # Add to the list        
            return parts    
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def get_internal_parts(self): # INTERNAL_PARTS
        command = ['lsblk', '-o', 'NAME,SIZE,TRAN,TYPE,MOUNTPOINT', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            internal_parts = []
            internal_disk = None
            for line in output.splitlines():
                part_info = {}
                for part in re.findall(r'(\w+)="([^"]*)"', line):
                    key, value = part
                    part_info[key] = value
                if part_info.get('TRAN') != 'usb' and part_info.get('TYPE') == "disk":
                    internal_disk = part_info.get("NAME")
                # Exclude external drives (TRAN="usb") and check if TYPE is 'part' or 'lvm'
                elif internal_disk and part_info.get("NAME").startswith(internal_disk) and part_info.get('TYPE') in ['part', 'lvm']:
                    path = f'/dev/{part_info.get("NAME")}'
                    info = f"{path} - Size: {part_info.get('SIZE')} - Type: {part_info.get('TYPE')}"
                    # Include mount point if it exists
                    if part_info.get('MOUNTPOINT'):
                        info += f" - Mountpoint: {part_info.get('MOUNTPOINT')}"
                    internal_parts.append((path, info))  # Add to the list
            return internal_parts        
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def get_external_parts(self): # EXTERNAL_PARTS
        command = ['lsblk', '-o', 'NAME,SIZE,TRAN,TYPE,MOUNTPOINT', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            external_parts = [] 
            external_disk = None
            for line in output.splitlines():
                part_info = {}
                for part in re.findall(r'(\w+)="([^"]*)"', line):
                    key, value = part
                    part_info[key] = value
                if part_info.get('TRAN') == 'usb' and part_info.get('TYPE') == "disk":
                    external_disk = part_info.get("NAME")
                # Check if the transport is 'usb' and the type is 'part' or 'lvm'
                elif external_disk and part_info.get("NAME").startswith(external_disk) and part_info.get('TYPE') in ['part', 'lvm']:
                    path = f'/dev/{part_info.get("NAME")}'
                    info = f"{path} - Size: {part_info.get('SIZE')} - Type: {part_info.get('TYPE')}"
                    # Include mount point if it exists
                    if part_info.get('MOUNTPOINT'):
                        info += f" - Mountpoint: {part_info.get('MOUNTPOINT')}"
                    external_parts.append((path, info))  # Add to the list
            return external_parts        
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def get_parts(slef, disk):
        command = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT', '-P', '-n', disk]
        try:
            parts = []
            output = subprocess.check_output(command, text=True)            
            for line in output.splitlines():
                part_info = {}
                for part in re.findall(r'(\w+)="([^"]*)"', line):
                    key, value = part
                    part_info[key] = value                
                # Check if TYPE is 'part' or 'lvm'
                if part_info.get('TYPE') in ['part', 'lvm']:
                    path = f'/dev/{part_info.get("NAME")}'
                    info = f"{path} - Size: {part_info.get('SIZE')} - Type: {part_info.get('TYPE')}"
                    # Include mount point if it exists
                    if part_info.get('MOUNTPOINT'):
                        info += f" - Mountpoint: {part_info.get('MOUNTPOINT')}"
                    parts.append((path, info))  # Add to list            
            return parts        
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def set_drive_combo(self, combo, types):
        data = None
        combo.clear()
        if types == "ALL_DISKS":
            data = self.get_all_disks()
        elif types == "INTERNAL_DISKS":
            data = self.get_internal_disks()
        elif types == "EXTERNAL_DISKS":
            data = self.get_external_disks()
        elif types == "ALL_PARTS":
            data = self.get_all_parts()
        elif types == "INTERNAL_PARTS":
            data = self.get_internal_parts()
        elif types == "EXTERNAL_PARTS":
            data = self.get_external_parts()
        elif types == "INTERNAL_DISKS_EXTERNAL_PARTS":
            data = self.get_internal_disks()
            data += self.get_external_parts()
        elif types == "ALL_LOOP_DRIVES":
            data = self.get_all_loop_drives()
        elif types == "INTERNAL_DISKS_ALL_LOOP_DRIVES":
            data = self.get_internal_disks()
            data += self.get_all_loop_drives()
        if data:
            for path, info in data:
                combo.addItem(info, path)
    
    def get_all_loop_drives(slef): # ALL_LOOP_DRIVES
        command = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT', '-P', '-n']
        try:
            output = subprocess.check_output(command, text=True)
            loop_drives = []              
            for line in output.splitlines():
                drive_info = {}
                for part in re.findall(r'(\w+)="([^"]*)"', line):
                    key, value = part
                    drive_info[key] = value            
                if drive_info.get('TYPE') == 'loop':
                    path = f'/dev/{drive_info.get("NAME")}'
                    info = f"{path} - Size: {drive_info.get('SIZE')} - Type: {drive_info.get('TYPE')}"                
                    # Include mount point if it exists
                    if drive_info.get('MOUNTPOINT'):
                        info += f" - Mountpoint: {drive_info.get('MOUNTPOINT')}"                
                    loop_drives.append((path, info))  # Add to the list        
            return loop_drives    
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return None
    
    def test_devices(self, combo):
        """Get a list of physical storage devices and their logical partitions, and populate the combo box."""
        command = ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,TRAN']        
        try:
            output = subprocess.check_output(command, text=True)
        except subprocess.CalledProcessError as e:
            print(f'Except Error: {e}')
            return
        combo.clear()
        current_device = ''
        for line in output.strip().split('\n'):
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 3:
                name = parts[0]
                size = parts[1]
                types = parts[2]
                mountpoint = ''
                transport = ''
                if len(parts) >=4:
                    mountpoint = parts[3]
                if len(parts) >=5:
                    transport = parts[4] 
                if name.startswith('├─') or name.startswith('└─'):
                    current_device = f'/dev/{name[2:]}'
                else:
                    current_device = f'/dev/{name}'
                display_str = f"{current_device} - Size: {size} - Type: {types} - Mountpoint: {mountpoint} - Tran: {transport}"
                combo.addItem(display_str, current_device)

class ImagesPage(QWidget):
    def __init__(self, user_id, user_name):
        super(ImagesPage, self).__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.statue_line = -1
        self.acquired_line = -1
        self.completion_line = -1
        self.mountpoint = os.path.expanduser("/media/images1")
        self.isStartAcquiry = False
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        diskManager = DiskManager()

        # Source Selection
        self.source_label = QLabel("Source Device:", self)
        layout.addWidget(self.source_label)

        self.source_combo = QComboBox(self)
        diskManager.set_drive_combo(self.source_combo, "ALL_DISKS")
        # Debug_Code
        #diskManager.set_drive_combo(self.source_combo, "INTERNAL_DISKS_ALL_LOOP_DRIVES")
        layout.addWidget(self.source_combo)

        # Destination Selection
        self.destination_label = QLabel("Destination Device:", self)
        layout.addWidget(self.destination_label)

        self.destination_combo = QComboBox(self)
        diskManager.set_drive_combo(self.destination_combo, "EXTERNAL_PARTS")
        # Debug_Code
        #diskManager.set_drive_combo(self.destination_combo, "INTERNAL_DISKS_ALL_LOOP_DRIVES")
        layout.addWidget(self.destination_combo)

        # Label Input
        self.image_label = QLabel("Image Label (no spaces):", self)
        layout.addWidget(self.image_label)

        self.image_name = QLineEdit(self)
        self.image_name.setPlaceholderText("test")
        layout.addWidget(self.image_name)

        # Acquire Button
        self.acquire_button = QPushButton("Start Acquisition", self)
        self.acquire_button.clicked.connect(self.acquire_disk_image)
        layout.addWidget(self.acquire_button)
        self.acquire_button.setStyleSheet("background-color: #8acd5e; color: white;")

        layout.addSpacing(0)

        # Text Area for logs or messages
        #self.log_area = QTextEdit(self)
        #self.log_area.setReadOnly(True)  # Make the text area read-only
        self.log_area = QListWidget(self)
        #self.log_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Allow log area to expand
        layout.addWidget(self.log_area)
    
    def acquire_disk_image(self):
        """Acquire disk image based on user selections."""
        if self.isStartAcquiry:
            self.acquire_button.setEnabled(False)
            self.stop_acquisition()
            return
        source_device = self.source_combo.currentData()
        destination_device = self.destination_combo.currentData()
        image_name = self.image_name.text()

        if not source_device:
            QMessageBox.warning(self, "Invalid Input", "Source Device cannot be empty.")
            return
        if not destination_device:
            QMessageBox.warning(self, "Invalid Input", "Destination Device cannot be empty.")
            return
        if not image_name or " " in image_name:
            QMessageBox.warning(self, "Invalid Input", "Image Label cannot be empty or contain spaces.")
            return
        # Show the Case Details Dialog
        dialog = CaseDetailsDialog(self.user_name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.log_area.clear() 
            self.statue_line = -1
            self.acquired_line = -1
            self.completion_line = -1
            
            # Get the entered case details
            case_details = dialog.get_case_details()
            case_number = case_details["case_number"]
            examiner_name = case_details["examiner_name"]
            evidence_number = case_details["evidence_number"]
            description = case_details["description"]
            notes = case_details["notes"]
                
            diskManager = DiskManager()
            diskManager.mount_device(destination_device, self.mountpoint)
            
            command = [
                "sudo", "ewfacquire",
                "-uC", case_number,      # Case Number
                "-E", evidence_number,   # Evidence Number
                "-e", examiner_name,     # Examiner Name
                "-D", description,       # Description
                "-N", notes,             # Notes
                "-f", "encase6",         # Format option (change if needed)
                "-t", self.mountpoint + "/" + image_name,  # Target file path
                source_device            # Source device
            ]
            self.isStartAcquiry = True
            self.update_data_acquire_button(self.isStartAcquiry)
            #self.acquire_button.setEnabled(False)
            db = DatabaseManager()
            db.add_log(self.user_id, self.user_name, "Acquiry started")
            db.close()
            # Start the acquisition in a separate thread
            self.worker = ProcessWorker(command)
            self.worker.output_received.connect(self.log_output)
            self.worker.error_received.connect(self.log_error)
            self.worker.finished.connect(self.acquisition_finished)

            self.worker.start()            

    def log_output(self, message):
        if "Status: at " in message and "%" in message:
            if self.statue_line == -1:
                self.log_area.addItem(f" {message}")
                self.statue_line = self.log_area.count() - 1 
            else:
                statue_line = self.log_area.item(self.statue_line)
                statue_line.setText(f" {message}")
        # elif "acquired " in message and " of total " in message:
        #     if self.acquired_line == -1:
        #         self.log_area.addItem(f"   {message}")
        #         self.acquired_line = self.log_area.count() - 1 
        #     else:
        #         acquired_line = self.log_area.item(self.acquired_line) 
        #         acquired_line.setText(f"   {message}")
        # elif "completion in " in message and " with " in message:
        #     if self.completion_line == -1:
        #         if self.acquired_line == -1:
        #             self.log_area.addItem(f"   {message}")
        #             self.completion_line = self.log_area.count() - 1 
        #         elif self.acquired_line != -1 and self.acquired_line == self.log_area.count() - 1:
        #             self.log_area.addItem(f"   {message}")
        #             self.completion_line = self.log_area.count() - 1 
        #         else:
        #             self.completion_line = self.acquired_line + 1 
        #             completion_line = self.log_area.item(self.completion_line) 
        #             completion_line.setText(f"   {message}")
        #     else:
        #         completion_line = self.log_area.item(self.completion_line) 
        #         completion_line.setText(f"   {message}")
        elif "Acquiry started at: " in message:
            item = QListWidgetItem(f"{message}")
            item.setForeground(QColor(0, 0, 255))
            self.log_area.addItem(item) 
        elif "Acquiry completed at:" in message:
            if self.statue_line > 0:
                statue_line = self.log_area.item(self.statue_line)
                statue_line.setText(f" Status: at 100%")
            item = QListWidgetItem(f"{message}")
            item.setForeground(QColor(0, 0, 255))
            self.log_area.addItem(item) 
        # elif "Written: " in message and " in " in message and "bytes" in message:
        #     self.log_area.addItem(f" {message}")
        #else:
        #    last_item = self.log_area.item(self.log_area.count() - 1)  # Get the last item
        #    if last_item.text() != message:
        #        self.log_area.addItem(message)
        self.log_area.scrollToBottom()   # Scroll to the bottom to ensure visibility

    def log_error(self, message):
        #self.log_area.addItem(message)  # Add general messages
        #self.log_area.scrollToBottom()  # Scroll to the bottom to ensure visibility
        return
    
    def acquisition_finished(self, return_code):
        self.isStartAcquiry = not self.isStartAcquiry
        self.update_data_acquire_button(self.isStartAcquiry)
        self.acquire_button.setEnabled(True)
        diskManager = DiskManager()
        diskManager.umount_point(self.mountpoint)
        db = DatabaseManager()
        if return_code == 1:
            item = QListWidgetItem(f"The acquisition has been suspended.")
            item.setForeground(QColor(255, 108, 84))
            self.log_area.addItem(item) 
            db.add_log(self.user_id, self.user_name, "Acquisition stopped")
        elif return_code == 0:
            #self.log_area.addItem("Disk image acquisition complete.")  # Add success message
            db.add_log(self.user_id, self.user_name, "Acquisition completed")
        else:
            item = QListWidgetItem(f"Acquiry failed with return code {return_code}.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
            db.add_log(self.user_id, self.user_name, "Acquisition failed")
        db.close()
        self.log_area.scrollToBottom()  # Scroll to the bottom to ensure visibility

    def stop_acquisition(self):
        if self.worker:
            self.worker.stop()

    def update_data_acquire_button(self, state):
        if state:
            self.acquire_button.setText("Stop Acquisition")
            self.acquire_button.setStyleSheet("background-color: #cd735e; color: white;")
        else:
            self.acquire_button.setText("Start Acquisition")
            self.acquire_button.setStyleSheet("background-color: #8acd5e; color: white;")

class ConvertPage(QWidget):
    def __init__(self, user_id, user_name):
        super(ConvertPage, self).__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.statue_line = -1
        self.acquired_line = -1
        self.completion_line = -1
        self.source_loop_device = None
        self.vm_name = "WIN001"
        self.cache_path = os.path.expanduser("/media/cache.img")
        self.mountpoint_i = os.path.expanduser("/mnt/ewf")
        self.mountpoint_x = os.path.expanduser("/mnt/xmount")
        self.mountpoint_s = os.path.expanduser("/media/images2")
        self.mountpoint_d = os.path.expanduser("/media/images1")
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        diskManager = DiskManager()

        # Source Selection
        self.source_label = QLabel("Source Device:", self)
        layout.addWidget(self.source_label)

        self.source_combo = QComboBox(self)
        diskManager.set_drive_combo(self.source_combo, "INTERNAL_DISKS_EXTERNAL_PARTS")
        # Debug_Code
        #diskManager.set_drive_combo(self.source_combo, "INTERNAL_DISKS_ALL_LOOP_DRIVES")
        layout.addWidget(self.source_combo)
        # Connect the source_combo change event to the slot
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)

        # Image List Selection
        self.image_list_label = QLabel("Image List:", self)
        layout.addWidget(self.image_list_label)

        # Create horizontal layout
        hi_layout = QHBoxLayout()

        self.image_list_combo = QComboBox(self)
        diskManager.find_image_files(self.mountpoint_s, self.image_list_combo)
        
        self.open_button = QPushButton("Open Image", self)
        self.open_button.clicked.connect(self.open_image)
        self.open_button.setFixedWidth(120)
        self.open_button.setEnabled(True)
        self.open_button.setStyleSheet("background-color: #8acd5e; color: white;")

        hi_layout.addWidget(self.image_list_combo)
        hi_layout.addWidget(self.open_button)

        layout.addLayout(hi_layout)

        # Destination Selection
        self.destination_label = QLabel("Destination Device:", self)
        layout.addWidget(self.destination_label)

        # Create horizontal layout
        hd_layout = QHBoxLayout()

        self.destination_combo = QComboBox(self)
        diskManager.set_drive_combo(self.destination_combo, "INTERNAL_DISKS_EXTERNAL_PARTS")
        # Debug_Code
        #diskManager.set_drive_combo(self.destination_combo, "INTERNAL_DISKS_ALL_LOOP_DRIVES")
        self.destination_combo.currentIndexChanged.connect(self.on_destination_changed)
        
        self.save_button = QPushButton("Save File", self)
        self.save_button.clicked.connect(self.save_file)
        self.save_button.setFixedWidth(120)
        self.save_button.setEnabled(True)
        self.save_button.setStyleSheet("background-color: #8acd5e; color: white;")

        hd_layout.addWidget(self.destination_combo)
        hd_layout.addWidget(self.save_button)
        layout.addLayout(hd_layout)

        # Label Input
        self.image_label = QLabel("Conversion Label (no spaces):", self)
        layout.addWidget(self.image_label)

        self.convert_name = QLineEdit(self)
        self.convert_name.setPlaceholderText("test")
        self.convert_name.setEnabled(False)
        layout.addWidget(self.convert_name)

        hb_layout = QHBoxLayout()
        hb_layout.addStretch(1)
        # Convert Button
        self.convert_button = QPushButton("Convert Image", self)
        self.convert_button.clicked.connect(self.convert_disk_image)
        self.convert_button.setStyleSheet("background-color: #8acd5e; color: white;")
        self.convert_button.setFixedWidth(150)
        
        # run VM Button
        self.run_vm_button = QPushButton("Run VM", self)
        self.run_vm_button.clicked.connect(lambda: self.run_vm(self.vm_name))
        self.run_vm_button.setStyleSheet("background-color: blue; color: white;")
        self.run_vm_button.setFixedWidth(150)
        self.run_vm_button.setVisible(False)

        hb_layout.addWidget(self.convert_button)
        hb_layout.addWidget(self.run_vm_button)
        layout.addLayout(hb_layout)        

        layout.addSpacing(0)

        self.log_area = QListWidget(self)
        layout.addWidget(self.log_area)        
    
    def open_image(self):
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Image file (*.E01)", options=options)
        if file_path:
            self.run_vm_button.setVisible(False)
            self.image_list_combo.clear()
            file_name = os.path.basename(file_path)
            self.image_list_combo.addItem(file_name, file_path)
    
    def save_file(self, types = "vdi"):
        file_type = "VDI file (*.vdi)"
        if types == "vmdk":
            file_type = "VDI file (*.vmdk)"
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Conversion File", "", file_type, options=options)
        if file_path:
            self.run_vm_button.setVisible(False)
            directory = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            file_name_without_ext, _ = os.path.splitext(file_name)
            full_path_without_ext = os.path.join(directory, file_name_without_ext)
            self.convert_name.setText(full_path_without_ext)

    def on_source_changed(self):
        """Handle changes in the source_combo."""
        source_device = self.source_combo.currentData()  # Get the current selected data
        if source_device:
            self.run_vm_button.setVisible(False)
            if 'Model:' in self.source_combo.currentText():
                self.image_list_combo.clear()
                self.open_button.setEnabled(True)
            else:
                self.open_button.setEnabled(False)
                diskManager = DiskManager()
                diskManager.mount_device(source_device, self.mountpoint_s)
                diskManager.find_image_files(self.mountpoint_s, self.image_list_combo)
    
    def on_destination_changed(self):
        """Handle changes in the destination_combo."""
        destination_device = self.destination_combo.currentData()  # Get the current selected data
        if destination_device:
            self.run_vm_button.setVisible(False)
            self.convert_name.clear()
            if 'Model:' in self.destination_combo.currentText():
                self.convert_name.setEnabled(False)
                self.save_button.setEnabled(True)
            else:
                self.convert_name.setEnabled(True)
                self.save_button.setEnabled(False)

    def convert_disk_image(self):
        """convert disk image based on user selections."""
        source_device = self.source_combo.currentData()
        image_path = self.image_list_combo.currentData()
        destination_device = self.destination_combo.currentData()
        convert_name = self.convert_name.text()

        if not image_path:
            QMessageBox.warning(self, "Invalid Input", "Image cannot be empty.")
            return
        if not destination_device:
            QMessageBox.warning(self, "Invalid Input", "Destination Device cannot be empty.")
            return
        if not convert_name or " " in convert_name:
            QMessageBox.warning(self, "Invalid Input", "VDI Label cannot be empty or contain spaces.")
            return
        self.make_vdi(image_path, destination_device, convert_name)
        #self.make_vmdk(image_path, destination_device, convert_name)

    def run_vm(self, vm_name):
        self.run_vm_button.setVisible(False)
        convert_name = self.convert_name.text()
        if not vm_name or not convert_name:
            return 
        diskManager = DiskManager()
        if 'Model:' not in self.destination_combo.currentText():
            if not diskManager.mount_device(destination_device, self.mountpoint_d):
                diskManager.umount_point(self.mountpoint_d)
                return
            convert_name = self.mountpoint_d + f"/{convert_name}"
        convert_name = f"/{convert_name}.vdi"  
        if not os.path.exists(convert_name):
            return
        command = f'VBoxManage list vms | grep "{vm_name}"'
        if diskManager.run_command_shell(command):
            command = ["VBoxManage", "unregistervm", vm_name, "--delete"]
            if not diskManager.run_command(command):                
                item = QListWidgetItem(f"{vm_name} exists and can't remove it. Can't create VM.")
                item.setForeground(QColor(255, 0, 0))
                self.log_area.addItem(item) 
                return
        command = ["VBoxManage", "createvm", "--name", vm_name, "--ostype", "Windows10_64", "--register"]
        if not diskManager.run_command(command):
            item = QListWidgetItem(f"Create VM command failed.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
            return

        command = ["VBoxManage", "modifyvm", vm_name, 
            "--memory", "4096", "--vram", "128", "--cpus", "2", 
            "--chipset", "ich9", "--firmware", "efi", "--boot1", "disk", 
            "--nic1", "nat", "--audio", "none", "--usb", "off", 
            "--usbehci", "off", "--usbxhci", "off", "--rtcuseutc", "on", 
            "--graphicscontroller", "vmsvga"
        ]
        if not diskManager.run_command(command):
            item = QListWidgetItem(f"Modify VM command failed.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
            return

        command = ["VBoxManage", "storagectl", vm_name, 
            "--name", "SATA Controller", "--add", "sata", "--controller", "IntelAHCI",
            "--portcount", "1", "--hostiocache", "on"
        ]
        if not diskManager.run_command(command):
            item = QListWidgetItem(f"Storage ctl command failed.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
            return

        command = ["VBoxManage", "storageattach", vm_name, 
            "--storagectl", "SATA Controller", "--port", "0", "--device", "0", 
            "--type", "hdd", "--medium", convert_name
        ]
        if not diskManager.run_command(command):
            item = QListWidgetItem(f"Storage attach command failed.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
            return

        command = ["VBoxManage", "startvm", vm_name, "--type", "gui"]

        item = QListWidgetItem(f"Image conversion started.")
        item.setForeground(QColor(0, 0, 255))
        self.log_area.addItem(item) 

        self.worker = ProcessWorker(command)
        self.worker.output_received.connect(self.log_output)
        self.worker.error_received.connect(self.log_error)
        self.worker.finished.connect(self.run_vm_finished)

        self.worker.start()        
        self.log_area.addItem(" Please wait...") 

    def make_vdi(self,image_path, destination_device, convert_name):
        diskManager = DiskManager()
        if 'Model:' not in self.destination_combo.currentText():
            if not diskManager.mount_device(destination_device, self.mountpoint_d):
                diskManager.umount_point(self.mountpoint_d)
                return
            convert_name = self.mountpoint_d + f"/{convert_name}"
        convert_name = f"{convert_name}.vdi"
        diskManager.xmount_image(image_path, self.cache_path, self.mountpoint_x)        
        # cp /mnt/xmount/*.vdi /media/image1/test.vdi
        command = f"sudo cp {self.mountpoint_x}/*.vdi {convert_name}"
        self.log_area.clear()
        self.convert_button.setEnabled(False)
        db = DatabaseManager()
        db.add_log(self.user_id, self.user_name, "Image converting started")
        db.close()
        item = QListWidgetItem(f"Image conversion started.")
        item.setForeground(QColor(0, 0, 255))
        self.log_area.addItem(item) 
        
        self.worker = ProcessWorker_shell(command)
        self.worker.output_received.connect(self.log_output)
        self.worker.error_received.connect(self.log_error)
        self.worker.finished.connect(self.conversion_finished)

        self.worker.start()
        self.log_area.addItem(" Please wait...") 
               
    def make_vmdk(self,image_path, destination_device, convert_name):
        diskManager = DiskManager()
        if not diskManager.mount_image(image_path, self.mountpoint_i):
            loops = diskManager.find_loops(f"{self.mountpoint_i}/ewf1")
            for loop in loops:
                diskManager.loop_remove(loop)
            diskManager.umount_point(self.mountpoint_i)
            diskManager.mount_image(image_path, self.mountpoint_i)
        self.source_loop_device = diskManager.loop_setup_file(f"{self.mountpoint_i}/ewf1")
        if not self.source_loop_device: 
            diskManager.umount_point(self.mountpoint_i)           
            return
        if 'Model:' not in self.destination_combo.currentText():
            if not diskManager.mount_device(destination_device, self.mountpoint_d):
                diskManager.umount_point(self.mountpoint_d)
                return
            convert_name = self.mountpoint_d + f"/{convert_name}.vmdk"
        diskManager.remove_VBox_disks(convert_name)        
        #VBoxManage createmedium disk --filename /media/device1/test.vmdk --format VMDK --variant RawDisk --property RawDrive=/dev/loop18
        command = [
            "sudo", "VBoxManage", 'createmedium', "disk",
            "--filename", convert_name,                     # Target vdi path 
            "--format", "VMDK",
            "--variant", "RawDisk",
            "--property", f"RawDrive={self.source_loop_device}"  # Source ewf1 path              
        ]
        self.log_area.clear()
        self.convert_button.setEnabled(False)
        db = DatabaseManager()
        db.add_log(self.user_id, self.user_name, "Image converting started")
        db.close()
        item = QListWidgetItem(f"Image conversion started.")
        item.setForeground(QColor(0, 0, 255))
        self.log_area.addItem(item) 
        
        self.worker = ProcessWorker(command)
        self.worker.output_received.connect(self.log_output)
        self.worker.error_received.connect(self.log_error)
        self.worker.finished.connect(self.conversion_finished)

        self.worker.start()
        self.log_area.addItem(" Please wait...") 

    def make_vdi_qemu(self, image_path, destination_device, convert_name):
        diskManager = DiskManager()
        if not diskManager.mount_image(image_path, self.mountpoint_i):
            return         
        
        if 'Model:' not in self.destination_combo.currentText():
            if not diskManager.mount_device(destination_device, self.mountpoint_d):
                return
            convert_name = self.mountpoint_d + f"/{convert_name}"
        
        command = [
            "sudo", "qemu-img", "convert",
            "-f", "raw",
            "-O", "vdi",
            self.mountpoint_i + "/ewf1",                # Source ewf1 path
            f"/{convert_name}.vdi"    # Target vdi path                
        ]
        self.log_area.clear()
        self.convert_button.setEnabled(False)
        db = DatabaseManager()
        db.add_log(self.user_id, self.user_name, "Image converting started")
        db.close()
        item = QListWidgetItem(f"Image conversion started.")
        item.setForeground(QColor(0, 0, 255))
        self.log_area.addItem(item) 
        # Start the conversion/export in a separate thread
        self.worker = ProcessWorker(command)
        self.worker.output_received.connect(self.log_output)
        self.worker.error_received.connect(self.log_error)
        self.worker.finished.connect(self.conversion_finished)

        self.worker.start()
        self.log_area.addItem(" Please wait...")  

    def log_output(self, message):
        self.log_area.addItem(message)  # Add general messages
        self.log_area.scrollToBottom()   # Scroll to the bottom to ensure visibility

    def log_error(self, message):
        self.log_area.addItem(message)  # Add general messages
        self.log_area.scrollToBottom()  # Scroll to the bottom to ensure visibility
        return

    def conversion_finished(self, return_code):
        self.convert_button.setEnabled(True)
        diskManager = DiskManager()
        if self.source_loop_device:
            diskManager.loop_remove(self.source_loop_device)
        diskManager.umount_point(self.mountpoint_x)
        diskManager.remove_dir(self.mountpoint_x)
        diskManager.umount_point(self.mountpoint_i)
        diskManager.umount_point(self.mountpoint_d)

        db = DatabaseManager()
        if return_code == 0:
            item = QListWidgetItem(f"Image conversion complete.")
            item.setForeground(QColor(0, 0, 255))
            self.log_area.addItem(item) 
            db.add_log(self.user_id, self.user_name, "Conversion complete")
            self.run_vm_button.setVisible(True)
        else:
            item = QListWidgetItem(f"Conversion failed with return code {return_code}.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
            db.add_log(self.user_id, self.user_name, "Conversion failed")
            self.run_vm_button.setVisible(False)
        db.close()
        self.log_area.scrollToBottom()  # Scroll to the bottom to ensure visibility

    def run_vm_finished(self, return_code):
        if return_code == 0:
            item = QListWidgetItem(f"VM launch complete.")
            item.setForeground(QColor(0, 0, 255))
            self.log_area.addItem(item) 
        else:
            item = QListWidgetItem(f"VM launch failed with return code {return_code}.")
            item.setForeground(QColor(255, 0, 0))
            self.log_area.addItem(item) 
        self.log_area.scrollToBottom()  # Scroll to the bottom to ensure visibility

class ReadPage(QWidget):
    def __init__(self, user_id, user_name):
        super(ReadPage, self).__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.mountpoint_i = os.path.expanduser("/mnt/ewf")
        self.mountpoint_s = os.path.expanduser("/media/images2")
        self.mountpoint_d = os.path.expanduser("/media/images1")
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        diskManager = DiskManager()
        # Source Selection
        self.source_label = QLabel("Source Device:", self)
        layout.addWidget(self.source_label)
        self.source_label.setFixedHeight(30)  # Fixed height
        self.source_combo = QComboBox(self)
        diskManager.set_drive_combo(self.source_combo, "INTERNAL_DISKS_EXTERNAL_PARTS")
        # Debug_Code
        #diskManager.set_drive_combo(self.source_combo, "INTERNAL_DISKS_ALL_LOOP_DRIVES")
        layout.addWidget(self.source_combo)
        # Connect the source_combo change event to the slot
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        
        # Image List Selection
        self.image_list_label = QLabel("Image List:", self)
        layout.addWidget(self.image_list_label)
        self.image_list_label.setFixedHeight(30)  # Fixed height
        # Create horizontal layout
        h_layout = QHBoxLayout()

        self.image_list_combo = QComboBox(self)
        diskManager.find_image_files(self.mountpoint_s, self.image_list_combo)
        self.image_list_combo.currentIndexChanged.connect(self.on_image_changed)
        
        self.open_button = QPushButton("Open Image", self)
        self.open_button.clicked.connect(self.open_image)
        self.open_button.setFixedWidth(120)
        self.open_button.setEnabled(True)
        self.open_button.setStyleSheet("background-color: #8acd5e; color: white;")

        h_layout.addWidget(self.image_list_combo)
        h_layout.addWidget(self.open_button)

        layout.addLayout(h_layout)
     
        layout.addSpacing(5)
        self.add_statistics_section(layout)

    def add_statistics_section(self, layout):
        border_widget = QWidget(self)
        border_widget.setObjectName("borderWidget")  # Set an object name for this widget

        stats_layout = QVBoxLayout(border_widget)

        border_widget.setStyleSheet("""
            QWidget#borderWidget { 
                border: 1px solid #d3d3d3;
                border-radius: 10px;
                padding: 10px;
                background-color: white;
            }
        """)

        info_label = QLabel("Image information", self)
        info_label.setStyleSheet("font-weight: bold ; color: #000064; font-size: 25px;")
        info_label.setMaximumHeight(70)
        stats_layout.addWidget(info_label)

        h1_layout = QHBoxLayout()
        label = QLabel("   Examiner name:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.examiner_name_value = QLabel("", self)
        self.examiner_name_value.setStyleSheet("color: red;")
        label.setMaximumHeight(35)
        self.examiner_name_value.setMaximumHeight(35)
        h1_layout.addWidget(label)
        h1_layout.addWidget(self.examiner_name_value)
        stats_layout.addLayout(h1_layout)

        h2_layout = QHBoxLayout()
        label = QLabel("   Case number:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.case_number_value = QLabel("", self)
        self.case_number_value.setStyleSheet("color: green;")
        label.setMaximumHeight(35)
        self.case_number_value.setMaximumHeight(35)
        h2_layout.addWidget(label)
        h2_layout.addWidget(self.case_number_value)
        stats_layout.addLayout(h2_layout)

        h3_layout = QHBoxLayout()
        label = QLabel("   Evidence number:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.evidence_number_value = QLabel("", self)
        self.evidence_number_value.setStyleSheet("color: blue;")
        label.setMaximumHeight(35)
        self.evidence_number_value.setMaximumHeight(35)
        h3_layout.addWidget(label)
        h3_layout.addWidget(self.evidence_number_value)
        stats_layout.addLayout(h3_layout)

        h4_layout = QHBoxLayout()
        label = QLabel("   Description:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.description_value = QLabel("", self)
        self.description_value.setStyleSheet("color: Navy;")
        label.setMaximumHeight(35)
        self.description_value.setMaximumHeight(35)
        h4_layout.addWidget(label)
        h4_layout.addWidget(self.description_value)
        stats_layout.addLayout(h4_layout)

        h5_layout = QHBoxLayout()
        label = QLabel("   Notes:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.notes_value = QLabel("", self)
        self.notes_value.setStyleSheet("color: Orange;")
        label.setMaximumHeight(35)
        self.notes_value.setMaximumHeight(35)
        h5_layout.addWidget(label)
        h5_layout.addWidget(self.notes_value)
        stats_layout.addLayout(h5_layout)

        h6_layout = QHBoxLayout()
        label = QLabel("   Media size:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.media_size_value = QLabel("", self)
        self.media_size_value.setStyleSheet("color: Teal;")
        label.setMaximumHeight(35)
        self.media_size_value.setMaximumHeight(35)
        h6_layout.addWidget(label)
        h6_layout.addWidget(self.media_size_value)
        stats_layout.addLayout(h6_layout)

        h7_layout = QHBoxLayout()
        label = QLabel("   MD5:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.MD5_value = QLabel("", self)
        self.MD5_value.setStyleSheet("color: Pink;")
        label.setMaximumHeight(35)
        self.MD5_value.setMaximumHeight(35)
        h7_layout.addWidget(label)
        h7_layout.addWidget(self.MD5_value)
        stats_layout.addLayout(h7_layout)

        h8_layout = QHBoxLayout()
        label = QLabel("   Acquisition date:", self)
        label.setFixedWidth(label.sizeHint().width())
        self.acquisition_date_value = QLabel("", self)
        self.acquisition_date_value.setStyleSheet("color: gray;")
        label.setMaximumHeight(35)
        self.acquisition_date_value.setMaximumHeight(35)
        h8_layout.addWidget(label)
        h8_layout.addWidget(self.acquisition_date_value)
        stats_layout.addLayout(h8_layout)

        label = QLabel("  ", self)
        label.setMinimumHeight(1)
        stats_layout.addWidget(label)

        layout.addWidget(border_widget)

    def open_image(self):
        options = QFileDialog.Option.DontUseNativeDialog
        file_pah, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Image file (*.E01)", options=options)
        if file_pah:
            self.image_list_combo.clear()
            file_name = os.path.basename(file_pah)
            self.image_list_combo.addItem(file_name, file_pah)
    def on_source_changed(self):
        """Handle changes in the source_combo."""
        source_device = self.source_combo.currentData()  # Get the current selected data
        if source_device:
            if 'Model:' in self.source_combo.currentText():
                self.image_list_combo.clear()
                self.open_button.setEnabled(True)
            else:
                self.open_button.setEnabled(False)
                diskManager = DiskManager()
                diskManager.mount_device(source_device, self.mountpoint_s)
                diskManager.find_image_files(self.mountpoint_s, self.image_list_combo)
    
    def on_image_changed(self):
        """Handle changes in the convert_type_combo."""
        self.clear_data()
        self.acquiry_info_flag = -1
        image_path = self.image_list_combo.currentData()
        if image_path:
            command = [
                "sudo", "ewfinfo",
                image_path                # Image path
            ]           
            self.image_list_combo.setEnabled(True)
            self.worker = ProcessWorker(command)
            self.worker.output_received.connect(self.log_output)
            self.worker.error_received.connect(self.log_error)
            self.worker.finished.connect(self.acquisition_finished)

            self.worker.start()  
    
    def log_output(self, message):
        if "Examiner name:" in message:            
            self.examiner_name_value.setText(message.split('Examiner name:')[1].strip())
        elif "Case number:" in message:
            self.case_number_value.setText(message.split('Case number:')[1].strip())
        elif "Evidence number:" in message:
            self.evidence_number_value.setText(message.split('Evidence number:')[1].strip())
        elif "Description:" in message:
            self.description_value.setText(message.split('Description:')[1].strip())
        elif "Notes:" in message:
            self.notes_value.setText(message.split('Notes:')[1].strip())
        elif "Media size:" in message:
            self.media_size_value.setText(message.split('Media size:')[1].strip())
        elif "MD5:" in message:
            self.MD5_value.setText(message.split('MD5:')[1].strip())
        elif "Acquisition date:" in message:
            self.acquisition_date_value.setText(message.split('Acquisition date:')[1].strip())
        
    def log_error(self, message):
        return 
    
    def acquisition_finished(self, return_code):
        self.image_list_combo.setEnabled(True)

    def clear_data(self):
        self.examiner_name_value.clear()
        self.case_number_value.clear()
        self.evidence_number_value.clear()
        self.description_value.clear()
        self.notes_value.clear()
        self.media_size_value.clear()
        self.MD5_value.clear()
        self.acquisition_date_value.clear()
        
class CaseDetailsDialog(QDialog):
    """Dialog to collect case details before acquisition."""
    def __init__(self, user_name, parent=None):
        super(CaseDetailsDialog, self).__init__(parent)
        self.setWindowTitle('Case Details Dialog')
        self.user_name = user_name
        
        # Create the layout
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Case Number
        self.case_number_input = QLineEdit(self)
        form_layout.addRow("Case Number:", self.case_number_input)
        
        # Examiner Name
        self.examiner_name_input = QLineEdit(self)
        form_layout.addRow("Examiner Name:", self.examiner_name_input)
        self.examiner_name_input.setReadOnly(True)
        self.examiner_name_input.setText(self.user_name)

        # Evidence Number
        self.evidence_number_input = QLineEdit(self)
        form_layout.addRow("Evidence Number:", self.evidence_number_input)
        
        # Description
        self.description_input = QTextEdit(self)
        form_layout.addRow("Description:", self.description_input)
        
        # Notes
        self.notes_input = QTextEdit(self)
        form_layout.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        # Add OK and Cancel buttons
        self.ok_button = QPushButton('OK', self)
        self.cancel_button = QPushButton('Cancel', self)
        layout.addWidget(self.ok_button)
        layout.addWidget(self.cancel_button)
        
        # Connect the buttons to their actions
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
    
    def get_case_details(self):
        """Return a dictionary of the entered case details."""
        return {
            "case_number": self.case_number_input.text(),
            "examiner_name": self.examiner_name_input.text(),
            "evidence_number": self.evidence_number_input.text(),
            "description": self.description_input.toPlainText(),
            "notes": self.notes_input.toPlainText()
        }
    
    def validate_inputs(self):
        """Check that necessary fields are filled."""
        if not self.case_number_input.text().strip():
            QMessageBox.warning(self, 'Invalid Input', 'Case Number cannot be empty.')
            return False
        if not self.examiner_name_input.text().strip():
            QMessageBox.warning(self, 'Invalid Input', 'Examiner Name cannot be empty.')
            return False
        if not self.evidence_number_input.text().strip():
            QMessageBox.warning(self, 'Invalid Input', 'Evidence Number cannot be empty.')
            return False
        return True
    
    def accept(self):
        """Override accept method to validate before closing the dialog."""
        if self.validate_inputs():
            super().accept()

class UsersPage(QWidget):
    def __init__(self):
        super(UsersPage, self).__init__()
        self.users_data = []  # List to hold user data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Create the table for displaying users
        self.users_table = QTableWidget(self)
        #self.users_table.verticalHeader().setFixedWidth(70)
        self.users_table.verticalHeader().hide()

        self.users_table.setColumnCount(3)  # Two columns: No, UserName and UserRole
        self.users_table.setHorizontalHeaderLabels(["No", "User_Name", "User_Role"])
        layout.addWidget(self.users_table)
        self.users_table.setColumnWidth(1, 200)
        self.users_table.setColumnWidth(2, 350)

        # Create buttons for user management
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add User", self)
        self.edit_button = QPushButton("Edit User", self)
        self.delete_button = QPushButton("Delete User", self)

        # Connect buttons to their respective functions
        self.add_button.clicked.connect(self.add_user)
        self.edit_button.clicked.connect(self.edit_user)
        self.delete_button.clicked.connect(self.delete_user)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        # Load initial user data (for demonstration purposes)
        self.load_initial_data()

    def load_initial_data(self):
        db = DatabaseManager()
        """Load initial data into the users table."""
        self.users_data = db.get_allusers()
        self.populate_users_table()
        db.close()
    
    def populate_users_table(self):
        """Populate the users table with data."""
        self.users_table.setRowCount(len(self.users_data))
        for row, (user_id, username, role) in enumerate(self.users_data):
            # Create a read-only User No item
            user_no_item = QTableWidgetItem(str(row+1))
            user_no_item.setFlags(user_no_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Create a read-only Username item
            username_item = QTableWidgetItem(username)
            username_item.setFlags(username_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Create a read-only Role item
            role_item = QTableWidgetItem(role)
            role_item.setFlags(role_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Set the items in the table
            self.users_table.setItem(row, 0, user_no_item)
            self.users_table.setItem(row, 1, username_item)
            self.users_table.setItem(row, 2, role_item)

    def add_user(self):
        """Add a new user."""
        dialog = UserDialog(-1)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_initial_data()

    def edit_user(self):
        """Edit the selected user."""
        selected_row = self.users_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Edit User", "Please select a user to edit.")
            return
        dialog = UserDialog(self.users_data[selected_row][0])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_initial_data()
    
    def delete_user(self):
        """Delete the selected user."""
        selected_row = self.users_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Delete User", "Please select a user to delete.")
            return
        # Confirmation dialog
        reply = QMessageBox.question(self, "Confirm Deletion",
                                    "Are you sure you want to delete this user?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db = DatabaseManager()
            res = db.remove_user(self.users_data[selected_row][0])
            db.close()
            if res:
                self.load_initial_data()

class UserDialog(QDialog):
    def __init__(self, user_id):
        super().__init__()
        # Set the border color and style using a stylesheet
        self.setStyleSheet("""
            QDialog {
                border: 2px solid gray;  /* Set the border color and thickness */
                border-radius: 10px;    /* Optional: Set rounded corners */
            }
        """)
        self.user_id = user_id
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Username
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Enter user name")
        form_layout.addRow("User Name: ", self.username_input)

        # Password
        self.password_input_old = QLineEdit(self)
        self.password_input_old.setPlaceholderText("Enter current password")
        self.password_input_old.setEchoMode(QLineEdit.EchoMode.Password)
        if self.user_id != -1:
            form_layout.addRow("Current Password: ", self.password_input_old)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password: ", self.password_input)

        self.password_input_conform = QLineEdit(self)
        self.password_input_conform.setPlaceholderText("Enter conform password")
        self.password_input_conform.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Conform Password: ", self.password_input_conform)

        # Role
        self.role_combo = QComboBox(self)
        self.role_combo.addItems(['admin', 'user'])
        form_layout.addRow("Select Role: ", self.role_combo)

        layout.addLayout(form_layout)

        # Add Apply and Cancel buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply", self)
        self.cancel_button = QPushButton("Cancel", self)
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        if user_id == -1:
            self.setWindowTitle("User Insert Dialog")
            self.password_input_old.setVisible(False)
        else:
            self.setWindowTitle("User Edit Dialog")
            db = DatabaseManager()
            user_data = db.get_user(user_id)
            self.username_input.setText(user_data[1])
            if user_data[3] != "admin":
                self.role_combo.setCurrentText("user")
            db.close()            

    def get_user_data(self):
        return {
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'role': self.role_combo.currentText()
        }
    
    def validate_inputs(self):
        """Check that necessary fields are filled."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        role = self.role_combo.currentText()
        if not username:
            QMessageBox.warning(self, 'Invalid Input', 'Username cannot be empty.')
            return False
        if password != self.password_input_conform.text():
            self.password_input.clear()
            self.password_input_conform .clear()
            QMessageBox.warning(self, 'Invalid Input', 'Confirm password is not equal.')
            return False
        if self.user_id == -1:
            db = DatabaseManager()
            res = db.add_user(username, password, role)
            db.close()
            if not res:
                QMessageBox.critical(self, 'Insert Error', f"{username} is duplicated.")
                return False
            return True     
        else:
            db = DatabaseManager()
            password_old = self.password_input_old.text()
            user = db.authenticate_user_byID(self.user_id, password_old)
            db.close()
            if user:
                db = DatabaseManager()
                res = db.update_user(self.user_id, username, password, role)
                db.close()
                if not res:
                    QMessageBox.critical(self, 'Insert Error', f"{username} is duplicated.")
                    return False
                return True 
            else:
                self.password_input_old.clear()
                self.password_input.clear()
                self.password_input_conform .clear()
                QMessageBox.critical(self, 'Input Error', f"Password incorrect.")
                return False
        return True
    
    def accept(self):
        """Override accept method to validate before closing the dialog."""
        if self.validate_inputs():
            super().accept()
        
class LogsPage(QWidget):
    def __init__(self):
        super(LogsPage, self).__init__()
        self.logs_data = []  # List to hold log data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Create the table for displaying logs
        self.logs_table = QTableWidget(self)
        #self.logs_table.verticalHeader().setFixedWidth(70)
        self.logs_table.verticalHeader().hide()

        self.logs_table.setColumnCount(4)  # Two columns: No, UserName, UserAction and ActionTime
        self.logs_table.setHorizontalHeaderLabels(["No", "User_Name", "User_Action", "Action_Time"])
        layout.addWidget(self.logs_table)

        # Create buttons for user management
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Logs", self)
        self.delete_button = QPushButton("Delete Log", self)

        # Connect buttons to their respective functions
        self.refresh_button.clicked.connect(self.refresh_logs)
        self.delete_button.clicked.connect(self.delete_log)

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        # Load initial log data (for demonstration purposes)
        self.load_initial_data()

    def load_initial_data(self):
        db = DatabaseManager()
        """Load initial data into the logs table."""
        self.logs_data = db.get_alllogs()
        self.populate_logs_table()
        db.close()
    
    def populate_logs_table(self):
        """Populate the logs table with data."""
        self.logs_table.setRowCount(len(self.logs_data))
        for row, (log_id, username, action, time, user_id) in enumerate(self.logs_data):
            # Create a read-only log No item
            log_no_item = QTableWidgetItem(str(row+1))
            log_no_item.setFlags(log_no_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Create a read-only Username item
            username_item = QTableWidgetItem(username)
            username_item.setFlags(username_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Create a read-only action item
            action_item = QTableWidgetItem(action)
            action_item.setFlags(action_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Create a read-only time item
            time_item = QTableWidgetItem(time)
            time_item.setFlags(time_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
            
            # Set the items in the table
            self.logs_table.setItem(row, 0, log_no_item)
            self.logs_table.setItem(row, 1, username_item)
            self.logs_table.setItem(row, 2, action_item)
            self.logs_table.setItem(row, 3, time_item)
            self.logs_table.setColumnWidth(1, 200)
            self.logs_table.setColumnWidth(2, 250)
            self.logs_table.setColumnWidth(3, 200)
            self.logs_table.scrollToBottom() 
    
    def refresh_logs(self):
        """Refresh Logs."""
        self.load_initial_data()

    def delete_log(self):
        """Delete the selected log."""
        selected_row = self.logs_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Delete Log", "Please select a log to delete.")
            return
        # Confirmation dialog
        reply = QMessageBox.question(self, "Confirm Deletion",
                                    "Are you sure you want to delete this log?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db = DatabaseManager()
            res = db.remove_log(self.logs_data[selected_row][0])
            db.close()
            if res:
                self.load_initial_data()
    
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, user_id, user_name, role):
        super(MainWindow, self).__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.role = role
        self.users_data = []  # List to hold user data
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"{app_title} Application")
        self.setGeometry(300, 300, 800, 600)
        self.setWindowIcon(QIcon(os.path.join(res_path, 'logo1.png')))
        #self.setStyleSheet("background-color: white;") 

        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Main layout with sidebar and content area
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar with QVBoxLayout
        self.sidebar = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar.setStyleSheet("background-color: #57a8f2;")  # Set the background color of the sidebar

        # Create checkable buttons for the sidebar
        self.images_button = QPushButton("  Images ", self)
        self.convert_button = QPushButton("  Convert", self)
        self.read_button = QPushButton("  Read     ", self)
        self.users_button = QPushButton("  Users   ", self)
        self.logs_button = QPushButton("  Logs    ", self)
        self.info_button = QPushButton("  Info     ", self)

        self.set_icon(self.images_button, os.path.join(res_path, 'images.png'))
        self.set_icon(self.convert_button, os.path.join(res_path, 'convert_icon.png'))
        self.set_icon(self.read_button, os.path.join(res_path, 'read_icon.png'))
        self.set_icon(self.users_button, os.path.join(res_path, 'users_icon.png'))
        self.set_icon(self.logs_button, os.path.join(res_path, 'logs_icon.png'))
        self.set_icon(self.info_button, os.path.join(res_path, 'info_icon.png'))

        # Set buttons to be checkable
        self.images_button.setCheckable(True)
        self.convert_button.setCheckable(True)
        self.read_button.setCheckable(True)
        self.users_button.setCheckable(True)
        self.logs_button.setCheckable(True)
        self.info_button.setCheckable(True)

        # Set initial button styles
        self.set_button_style(self.images_button, True)
        self.set_button_style(self.convert_button, False)
        self.set_button_style(self.read_button, False)
        self.set_button_style(self.users_button, False)
        self.set_button_style(self.logs_button, False)
        self.set_button_style(self.info_button, False)

        # Add buttons to the sidebar layout
        self.sidebar_layout.addWidget(self.images_button)
        self.sidebar_layout.addWidget(self.convert_button)
        self.sidebar_layout.addWidget(self.read_button)
        self.sidebar_layout.addWidget(self.users_button)
        self.sidebar_layout.addWidget(self.logs_button)
        self.sidebar_layout.addWidget(self.info_button)
        self.sidebar_layout.addStretch(1)  # Add stretch to push buttons to the top

        # Add stretch to push buttons to the top
        self.sidebar_layout.addStretch(1)

        # Logo at the bottom of the sidebar
        self.logo_label = QLabel(self.sidebar)
        #pixmap = QPixmap(os.path.join(res_path, 'logo.png'))  # Path to your logo image
        #scaled_pixmap = pixmap.scaled(100, 130, QtCore.Qt.AspectRatioMode.KeepAspectRatio)  # Scale the logo if necessary
        pixmap = QPixmap(os.path.join(res_path, 'logo1.png'))  # Path to your logo image
        scaled_pixmap = pixmap.scaled(100, 120, QtCore.Qt.AspectRatioMode.KeepAspectRatio)  # Scale the logo if necessary
        self.logo_label.setPixmap(scaled_pixmap)
        self.logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)  # Center the logo

        # Add the logo to the sidebar layout
        self.sidebar_layout.addWidget(self.logo_label)

        # Stack widget for content area
        self.stack = QStackedWidget()

        # Create pages for each section
        self.images_widget = ImagesPage(self.user_id, self.user_name)
        self.convert_widget = ConvertPage(self.user_id, self.user_name)
        self.read_widget = ReadPage(self.user_id, self.user_name)
        self.users_widget = UsersPage()
        self.logs_widget = LogsPage()
        self.info_widget = InfoPage() #self.create_page("Info Section")

        # Add pages to the stack
        self.stack.addWidget(self.images_widget)
        self.stack.addWidget(self.convert_widget)
        self.stack.addWidget(self.read_widget)
        self.stack.addWidget(self.users_widget)
        self.stack.addWidget(self.logs_widget)
        self.stack.addWidget(self.info_widget)

        # Add sidebar and content area to the main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        # Connect buttons to switch between pages and toggle styles
        self.images_button.clicked.connect(lambda: self.toggle_button(self.images_button, 0))
        self.convert_button.clicked.connect(lambda: self.toggle_button(self.convert_button, 1))
        self.read_button.clicked.connect(lambda: self.toggle_button(self.read_button, 2))
        self.users_button.clicked.connect(lambda: self.toggle_button(self.users_button, 3))
        self.logs_button.clicked.connect(lambda: self.toggle_button(self.logs_button, 4))
        self.info_button.clicked.connect(lambda: self.toggle_button(self.info_button, 5))

        # Role-based access control
        if self.role != "admin":
            self.users_button.setVisible(False)  # Hide "Users" button for non-admins

    def create_page(self, title):
        """Helper function to create a page with a label."""
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(title, page)
        layout.addWidget(label)
        return page    

    def set_icon(self, button, icon_path):
        button.setFixedWidth(130)
        icon = QIcon(icon_path)
        button.setIcon(icon)
        button.setIconSize(button.sizeHint())
        button.setStyleSheet("text-align: right; padding-left: -10px; padding-right: 1px;")


    def set_button_style(self, button, is_toggled):
        """Set button style based on its toggled state."""
        if is_toggled:
            button.setStyleSheet("background-color: white; color: black;")  # Toggled state
        else:
            button.setStyleSheet("background-color: #3d9df4; color: white;")  # Default state

    def toggle_button(self, button, index):
        """Handle the toggle behavior for buttons."""
        # Reset all buttons' states and styles
        self.images_button.setChecked(False)
        self.convert_button.setChecked(False)
        self.read_button.setChecked(False)
        self.users_button.setChecked(False)
        self.logs_button.setChecked(False)
        self.info_button.setChecked(False)

        # Set the clicked button to be checked
        button.setChecked(True)

        # Change styles for all buttons based on their new states
        self.set_button_style(self.images_button, self.images_button.isChecked())
        self.set_button_style(self.convert_button, self.convert_button.isChecked())
        self.set_button_style(self.read_button, self.read_button.isChecked())
        self.set_button_style(self.users_button, self.users_button.isChecked())
        self.set_button_style(self.logs_button, self.logs_button.isChecked())
        self.set_button_style(self.info_button, self.info_button.isChecked())

        # Switch to the corresponding page in the stack
        self.stack.setCurrentIndex(index)
    
    def closeEvent(self, event):
        db = DatabaseManager()
        db.add_log(self.user_id, self.user_name, "Logged out")
        db.close()
        diskManager = DiskManager()
        diskManager.umount_point("/media/images2")

class LoginWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(LoginWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Login Windows")
        self.setFixedSize(300, 150)
        self.setWindowIcon(QIcon(os.path.join(res_path, 'pass.png')))
        self.setStyleSheet("background-color: white;") 
        
        # Central widget
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        # Create layout for the form
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Username layout
        username_layout = QtWidgets.QHBoxLayout()
        self.label_username = QtWidgets.QLabel("Username:")
        self.username_input = QtWidgets.QLineEdit()
        username_layout.addWidget(self.label_username)
        username_layout.addWidget(self.username_input)

        layout.addSpacing(10)

        # Password layout
        password_layout = QtWidgets.QHBoxLayout()
        self.label_password = QtWidgets.QLabel("Password: ")
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.label_password)
        password_layout.addWidget(self.password_input)

        layout.addSpacing(10)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()
        self.login_button = QtWidgets.QPushButton("Login")
        self.login_button.setStyleSheet("background-color: #8acd5e; color: white; margin-top 10")
        button_layout.addStretch(1)  # Add stretch to center the button
        button_layout.addWidget(self.login_button)
        button_layout.addStretch(1)  # Add stretch to center the button

        # Add the layouts to the main vertical layout
        layout.addStretch(1)  # Stretch at the top to center the form vertically
        layout.addLayout(username_layout)
        layout.addLayout(password_layout)
        layout.addLayout(button_layout)
        layout.addStretch(1)  # Stretch at the bottom to center the form vertically

        # Connect the login button
        self.login_button.clicked.connect(self.login)    

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        db = DatabaseManager()
        # Authenticate a user
        user = db.authenticate_user(username, password)        
        if user:
            self.accept(user[0], user[1], user[3])
            # Add a log entry for the user
            db.add_log(user[0], user[1], "Logged in")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Authentication failed!")
        db.close()

    def accept(self, id, name, role):
        self.hide()
        self.mainWindow = MainWindow(id, name, role)
        self.mainWindow.show()

class DatabaseManager:
    def __init__(self, db_name='Data'):
        """Initialize the database manager and ensure tables are created."""
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        #self.create_tables()

    def create_tables(self):
        """Create the necessary tables for users and logs if they don't exist."""
        # Create users table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'user')) NOT NULL
        );
        """
        self.cursor.execute(create_table_query)      
        # Create logs table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.cursor.execute(create_table_query)
        self.conn.commit()

    def add_user(self, username, password, role='admin'):
        """Add a new user to the users table."""
        # Hash the password before storing it
        password_hash = self.getHashString(password)        
        try:
            self.cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                            (username, password_hash, role))
            self.conn.commit()
            return True
        except Exception as e:
            return False

    def authenticate_user(self, username, password):
        """Authenticate a user based on username and password."""
        password_hash = self.getHashString(password)
        self.cursor.execute('SELECT * FROM users WHERE username=? AND password=?', 
                            (username, password_hash))
        return self.cursor.fetchone()  # None if no match
    
    def get_user(self, user_id):
        """Authenticate a user based on user_id."""
        query = "SELECT * FROM users WHERE id=?"
        self.cursor.execute(query, (user_id,))
        return self.cursor.fetchone()  # None if no match

    def authenticate_user_byID(self, user_id, password):
        """Authenticate a user based on user_id and password."""
        password_hash = self.getHashString(password)
        self.cursor.execute('SELECT * FROM users WHERE id=? AND password=?', 
                            (user_id, password_hash))
        return self.cursor.fetchone()  # None if no match

    def get_allusers(self):
        query = "SELECT id, username, role FROM users"
        try:
            self.cursor.execute(query)
            return  self.cursor.fetchall()  # Fetch all rows
        except sqlite3.Error as e:
            #QMessageBox.critical(self, 'Database Error', f"Failed to load data: {e}")
            return None
    
    def update_user(self, user_id, username, password, role):
        """Update the user details in the database."""
        # Hash the password
        password_hash = self.getHashString(password)        
        # Parameterized query to prevent SQL injection
        query = "UPDATE users SET username=?, password=?, role=? WHERE id=?"        
        try:
            # Execute the query with parameters
            self.cursor.execute(query, (username, password_hash, role, user_id))
            self.conn.commit()  # Commit the changes to the database
            return True
        except sqlite3.Error as e:
            return False
    
    def remove_user(self, user_id):
        try:
            self.cursor.execute("DELETE FROM users WHERE id=?",(user_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            return False

    def add_log(self, user_id, username, action):
        """Add a log entry for a specific user and action."""
        self.cursor.execute('INSERT INTO logs (user_id, username, action) VALUES (?, ?, ?)', 
                            (user_id, username, action))
        self.conn.commit()

    def get_user_logs(self, user_id):
        """Retrieve all logs for a specific user."""
        self.cursor.execute('SELECT * FROM logs WHERE user_id=?', (user_id,))
        return self.cursor.fetchall()

    def get_alllogs(self):
        query = "SELECT id, username, action, timestamp, user_id FROM logs"
        try:
            self.cursor.execute(query)
            return  self.cursor.fetchall()  # Fetch all rows
        except sqlite3.Error as e:
            return None

    def remove_log(self, log_id):
        try:
            self.cursor.execute("DELETE FROM logs WHERE id=?",(log_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            return False

    def close(self):
        """Close the database connection."""
        self.conn.close()
    # Function to hash a password using SHA-256
    def getHashString(self, str):
        hash_object = SHA256.new()
        hash_object.update(str.encode('utf-8'))
        return hash_object.hexdigest()

class InfoPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        border_widget = QWidget(self)
        border_widget.setObjectName("borderWidget")  # Set an object name for this widget

        stats_layout = QVBoxLayout(border_widget)
        border_widget.setMinimumWidth(500)  # Set your desired minimum width
        border_widget.setMinimumHeight(300)  # Set your desired minimum height

        border_widget.setStyleSheet("""
            QWidget#borderWidget { 
                border: 1px solid #d3d3d3;
                border-radius: 10px;
                padding: 10px;
                background-color: white;
            }
        """)
        
        title_label = QLabel(f"<h1>{app_title}</h1>")
        version_label = QLabel(f"Version: {app_version}")
        copyright_label = QLabel(f"{copyright}")
        build_label = QLabel(f"Build: {app_build}")
        contact_label = QLabel(f"Contact: <span style='color: blue;'>{contact_info}</span>")

        # Customize styles
        title_label.setStyleSheet("font-weight: bold; color: #000064;")
        version_label.setStyleSheet("color: #333333;")
        #copyright_label.setStyleSheet("color: #333333;")
        copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        build_label.setStyleSheet("color: #333333;")

        stats_layout.addWidget(QLabel("  "))
        stats_layout.addWidget(title_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(version_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("  "))
        stats_layout.addWidget(copyright_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(build_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(QLabel("  "))        
        stats_layout.addWidget(contact_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # Center the layout
        #stats_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Add the border widget to the main layout
        layout.addWidget(border_widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

class common_clase:
    def get_center(self):
        screen_geometry = QtWidgets.QApplication.primaryScreen().availableGeometry()
        return screen_geometry.center()
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    default_font = QtGui.QFont()
    default_font.setPointSize(15)
    app.setFont(default_font)
    db = DatabaseManager()
    db.create_tables()
    db.close()
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())