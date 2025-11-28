import time
import json
import struct
import psutil
import ctypes
import win32gui
import win32con
import traceback
import win32process
import requests
from ctypes import wintypes
import sys
import threading
import win32api
import tkinter as tk
from tkinter import colorchooser

OFFSETS_URL = "https://robloxoffsets.com/offsets.json"
try:
    resp = requests.get(OFFSETS_URL, timeout=5)
    OFFSETS = resp.json()
except Exception as e:
    print(f"Ошибка при получении смещений: {e}")
    sys.exit(1)

COLOR_SETTINGS = {
    "box_color": (0, 255, 0),
    "high_health_color": (255, 0, 0),
    "line_color": (255, 255, 0),
    "text_color": (255, 255, 255),
    "health_text_color": (255, 255, 255)
}

class ColorSettingsWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("ESP Color Settings")
        self.window.geometry("300x300")
        
        self.create_widgets()
        
    def create_widgets(self):
        tk.Label(self.window, text="ESP Color Settings", font=("Arial", 14)).pack(pady=10)
        
        self.create_color_button("Box Color", "box_color", (255,255,255))
        self.create_color_button("High Health Color", "high_health_color", (255,255,255))
        self.create_color_button("Line Color", "line_color", (255,255,255))
        self.create_color_button("Text Color", "text_color", (255, 255, 255))
        self.create_color_button("Health Text Color", "health_text_color", (255, 255, 255))
        
        tk.Button(self.window, text="Apply Settings", command=self.apply_settings, 
                 bg="#4CAF50", fg="white", font=("Arial", 10)).pack(pady=10)
        
        self.color_preview = tk.Frame(self.window, width=200, height=20, bg=self.rgb_to_hex(COLOR_SETTINGS["box_color"]))
        self.color_preview.pack(pady=5)
        
    def create_color_button(self, text, setting_key, default_color):
        frame = tk.Frame(self.window)
        frame.pack(pady=5)
        
        tk.Label(frame, text=text, width=15).pack(side=tk.LEFT)
        
        color_btn = tk.Button(frame, text="Choose", command=lambda k=setting_key: self.choose_color(k),
                             bg=self.rgb_to_hex(COLOR_SETTINGS[setting_key]), width=10)
        color_btn.pack(side=tk.LEFT, padx=5)
        
    def choose_color(self, setting_key):
        color_code = colorchooser.askcolor(title=f"Choose {setting_key}", initialcolor=self.rgb_to_hex(COLOR_SETTINGS[setting_key]))
        if color_code[0]:
            COLOR_SETTINGS[setting_key] = tuple(map(int, color_code[0]))
            self.update_preview()
            
    def rgb_to_hex(self, rgb):
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def update_preview(self):
        self.color_preview.configure(bg=self.rgb_to_hex(COLOR_SETTINGS["box_color"]))
        
    def apply_settings(self):
        self.window.destroy()
        
    def run(self):
        self.window.mainloop()

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32Usage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(wintypes.DWORD)),
        ("th32ModuleID", wintypes.DWORD),
        ("th32Threads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260)
    ]

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(wintypes.BYTE)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260)
    ]

class vec2:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

class vec3:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

class robloxmemory:
    
    def __init__(self):
        if not self.find_roblox_process():
            raise Exception("failed to find roblox process.")
        self.initialize_game_data()

    def find_roblox_process(self):
        hwnd, pid = self.find_window_by_exe("RobloxPlayerBeta.exe")
        if pid:
            self.hwnd = hwnd
            self.process_id = pid
        else:
            pid = self.get_process_id_by_psutil("RobloxPlayerBeta.exe")
            if not pid:
                return False
            self.process_id = pid
            hwnd, _ = self.find_window_by_exe("RobloxPlayerBeta.exe")
            self.hwnd = hwnd if hwnd else None
        self.process_handle = ctypes.windll.kernel32.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, self.process_id)
        if not self.process_handle:
            return False
        self.base_address = self.get_module_address("RobloxPlayerBeta.exe")
        if not self.base_address:
            ctypes.windll.kernel32.CloseHandle(self.process_handle)
            return False
        return True

    def find_window_by_exe(self, exe_name):
        matches = []
        def enum_proc(hwnd, _):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    p = psutil.Process(pid)
                    pname = (p.name() or "").lower()
                    target = exe_name.lower()
                    target_noexe = target[:-4] if target.endswith(".exe") else target
                    if pname == target or pname == target_noexe:
                        matches.append((hwnd, pid))
                except Exception:
                    pass
                return True
            except Exception:
                return True
        try:
            win32gui.EnumWindows(enum_proc, None)
        except Exception:
            pass
        if matches:
            for hwnd, pid in matches:
                title = win32gui.GetWindowText(hwnd)
                if title:
                    return hwnd, pid
            return matches[0]
        return None, None

    def get_process_id_by_psutil(self, process_name):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == process_name.lower():
                        return proc.info['pid']
                except Exception:
                    continue
            return None
        except Exception:
            return None

    def get_module_address(self, module_name):
        if not getattr(self, 'process_handle', None):
            return None
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(0x8 | 0x10, self.process_id)
        if snapshot == -1:
            return None
        module_entry = MODULEENTRY32()
        module_entry.dwSize = ctypes.sizeof(MODULEENTRY32)
        if ctypes.windll.kernel32.Module32First(snapshot, ctypes.byref(module_entry)):
            while True:
                try:
                    name = module_entry.szModule.decode().lower()
                except Exception:
                    name = ""
                if module_name.lower() == name:
                    ctypes.windll.kernel32.CloseHandle(snapshot)
                    return ctypes.addressof(module_entry.modBaseAddr.contents)
                if not ctypes.windll.kernel32.Module32Next(snapshot, ctypes.byref(module_entry)):
                    break
        ctypes.windll.kernel32.CloseHandle(snapshot)
        return None

    def read_memory(self, address, size):
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        result = ctypes.windll.kernel32.ReadProcessMemory(self.process_handle, ctypes.c_void_p(address), buffer, size, ctypes.byref(bytes_read))
        if result and bytes_read.value > 0:
            return buffer.raw[:bytes_read.value]
        return None

    def read_ptr(self, address):
        data = self.read_memory(address, 8)
        if data:
            return int.from_bytes(data, byteorder='little')
        return None

    def read_int(self, address):
        data = self.read_memory(address, 4)
        if data:
            return int.from_bytes(data, byteorder='little', signed=True)
        return None

    def read_int64(self, address):
        data = self.read_memory(address, 8)
        if data:
            return struct.unpack('q', data)[0]
        return None

    def read_float(self, address):
        data = self.read_memory(address, 4)
        if data:
            return struct.unpack('f', data)[0]
        return None

    def read_string(self, address):
        if not address:
            return ""
        str_length = self.read_int(address + 0x18)
        if not str_length or str_length <= 0 or str_length > 1000:
            return ""
        if str_length >= 16:
            address = self.read_ptr(address)
            if not address:
                return ""
        result = ""
        offset = 0
        while offset < str_length:
            char_data = self.read_memory(address + offset, 1)
            if not char_data:
                break
            char_val = char_data[0]
            if char_val == 0:
                break
            result += chr(char_val)
            offset += 1
        return result

    def initialize_game_data(self):
        try:
            fake_data_model = self.read_ptr(self.base_address + int(OFFSETS["FakeDataModelPointer"], 16))
            if not fake_data_model or fake_data_model == 0xFFFFFFFF:
                return
            data_model_pointer = self.read_ptr(fake_data_model + int(OFFSETS["FakeDataModelToDataModel"], 16))
            if not data_model_pointer or data_model_pointer == 0xFFFFFFFF:
                return
            retry_count = 0
            data_model_name = ""
            while retry_count < 30:
                name_ptr = self.read_ptr(data_model_pointer + int(OFFSETS["Name"], 16)) if data_model_pointer else None
                data_model_name = self.read_string(name_ptr) if name_ptr else ""
                if data_model_name == "Ugc":
                    break
                time.sleep(1)
                retry_count += 1
                fake_data_model = self.read_ptr(self.base_address + int(OFFSETS["FakeDataModelPointer"], 16))
                if fake_data_model:
                    data_model_pointer = self.read_ptr(fake_data_model + int(OFFSETS["FakeDataModelToDataModel"], 16))
            if data_model_name != "Ugc":
                return
            self.data_model = data_model_pointer
            self.visual_engine = self.read_ptr(self.base_address + int(OFFSETS["VisualEnginePointer"], 16))
            if not self.visual_engine or self.visual_engine == 0xFFFFFFFF:
                self.visual_engine = None
                return
            self.workspace = self.find_first_child_which_is_a(self.data_model, "Workspace") if self.data_model else None
            self.players = self.find_first_child_which_is_a(self.data_model, "Players") if self.data_model else None
            if self.workspace:
                self.camera = self.find_first_child_which_is_a(self.workspace, "Camera")
            else:
                self.camera = None
            if self.players:
                local_player_ptr = self.read_ptr(self.players + int(OFFSETS["LocalPlayer"], 16)) if self.players else None
                if local_player_ptr:
                    self.local_player = local_player_ptr
                else:
                    self.local_player = None
            else:
                self.local_player = None
        except Exception:
            pass

    def get_children(self, parent_address):
        children = []
        if not parent_address:
            return children
        children_ptr = self.read_ptr(parent_address + int(OFFSETS["Children"], 16))
        if not children_ptr:
            return children
        children_end = self.read_ptr(children_ptr + int(OFFSETS["ChildrenEnd"], 16))
        current_child = self.read_ptr(children_ptr)
        while current_child < children_end:
            child_ptr = self.read_ptr(current_child)
            if child_ptr:
                children.append(child_ptr)
            current_child += 0x10
        return children

    def get_instance_name(self, address):
        if not address:
            return ""
        name_ptr = self.read_ptr(address + int(OFFSETS["Name"], 16))
        return self.read_string(name_ptr) if name_ptr else ""

    def get_instance_class(self, address):
        if not address:
            return ""
        class_descriptor = self.read_ptr(address + int(OFFSETS["ClassDescriptor"], 16))
        if class_descriptor:
            class_name_ptr = self.read_ptr(class_descriptor + int(OFFSETS["ClassDescriptorToClassName"], 16))
            return self.read_string(class_name_ptr) if class_name_ptr else ""
        return ""

    def find_first_child_which_is_a(self, parent_address, class_name):
        children = self.get_children(parent_address)
        for child in children:
            if self.get_instance_class(child) == class_name:
                return child
        return None

    def find_first_child_by_name(self, parent_address, name):
        children = self.get_children(parent_address)
        for child in children:
            if self.get_instance_name(child) == name:
                return child
        return None

    def read_matrix4(self, address):
        data = self.read_memory(address, 64)
        if data:
            matrix = []
            for i in range(16):
                matrix.append(struct.unpack('f', data[i*4:(i+1)*4])[0])
            return matrix
        return None

    def get_team(self, player_ptr):
        if not player_ptr:
            return None
        team_ptr = self.read_ptr(player_ptr + int(OFFSETS.get("Team", "0x0"), 16))
        if not team_ptr:
            return None
        return team_ptr

    def get_player_coordinates(self):
        if not getattr(self, 'players', None) or not getattr(self, 'local_player', None):
            return []
        coordinates = []
        player_instances = self.get_children(self.players)
        for player_ptr in player_instances:
            if not player_ptr:
                continue
            if player_ptr == self.local_player:
                continue
            player_name = self.get_instance_name(player_ptr)
            if not player_name:
                continue
            character_ptr = self.read_ptr(player_ptr + int(OFFSETS["ModelInstance"], 16))
            if not character_ptr:
                continue
            if self.get_instance_class(character_ptr) != "Model":
                continue
            humanoid_root_part = self.find_first_child_by_name(character_ptr, "HumanoidRootPart")
            if not humanoid_root_part:
                continue
            if self.get_instance_class(humanoid_root_part) != "Part":
                continue
            primitive = self.read_ptr(humanoid_root_part + int(OFFSETS["Primitive"], 16))
            if not primitive:
                continue
            position_data = self.read_memory(primitive + int(OFFSETS["Position"], 16), 12)
            if not position_data:
                continue
            x, y, z = struct.unpack('fff', position_data)
            position = vec3(x, y, z)
            size_data = self.read_memory(primitive + int(OFFSETS["PartSize"], 16), 12)
            if size_data:
                sx, sy, sz = struct.unpack('fff', size_data)
                player_size = vec3(sx, sy, sz)
            else:
                player_size = vec3(2.0, 5.0, 1.0)
            head_part = self.find_first_child_by_name(character_ptr, "Head")
            head_pos = None
            if head_part:
                head_primitive = self.read_ptr(head_part + int(OFFSETS["Primitive"], 16))
                if head_primitive:
                    head_position_data = self.read_memory(head_primitive + int(OFFSETS["Position"], 16), 12)
                    if head_position_data:
                        hx, hy, hz = struct.unpack('fff', head_position_data)
                        head_pos = vec3(hx, hy, hz)
            if not head_pos:
                head_pos = vec3(position.x, position.y + player_size.y / 2 + 1.0, position.z)
                
            feet_pos = vec3(position.x, position.y - player_size.y / 2, position.z)
            
            humanoid = self.find_first_child_which_is_a(character_ptr, "Humanoid")
            health = None
            max_health = None
            if humanoid:
                health_addr = humanoid + int(OFFSETS["Health"], 16)
                max_health_addr = humanoid + int(OFFSETS["MaxHealth"], 16)
                health = self.read_float(health_addr)
                max_health = self.read_float(max_health_addr)
            coordinates.append({
                "player_name": player_name,
                "root_pos": position,
                "head_pos": head_pos,
                "feet_pos": feet_pos,
                "player_size": player_size,
                "player_ptr": player_ptr,
                "character_ptr": character_ptr,
                "humanoid_root_part_ptr": humanoid_root_part,
                "health": health,
                "max_health": max_health
            })
        return coordinates

    def get_window_viewport(self):
        if not getattr(self, 'hwnd', None):
            return {"width": 1920, "height": 1080, "x": 0, "y": 0, "border_x": 0, "border_y": 0}
        try:
            left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
            width = float(right - left)
            height = float(bottom - top)

            if width <= 0 or height <= 0:
                rect = win32gui.GetWindowRect(self.hwnd)
                width = float(rect[2] - rect[0])
                height = float(rect[3] - rect[1])
                
            win_rect = win32gui.GetWindowRect(self.hwnd)
            client_rect = win32gui.GetClientRect(self.hwnd)
            
            pos_x = win_rect[0] + client_rect[0]
            pos_y = win_rect[1] + client_rect[1]

            return {
                "width": width, 
                "height": height,
                "x": pos_x, 
                "y": pos_y,
                "border_x": client_rect[0],
                "border_y": client_rect[1]
            }
        except Exception:
            return {"width": 1920, "height": 1080, "x": 0, "y": 0, "border_x": 0, "border_y": 0}

    def world_to_screen(self, pos):
        if not getattr(self, 'visual_engine', None):
            return vec2(-1, -1)
        try:
            view_matrix = self.read_matrix4(self.visual_engine + int(OFFSETS["viewmatrix"], 16))
            if not view_matrix:
                return vec2(-1, -1)
            qx = (pos.x * view_matrix[0]) + (pos.y * view_matrix[1]) + (pos.z * view_matrix[2]) + view_matrix[3]
            qy = (pos.x * view_matrix[4]) + (pos.y * view_matrix[5]) + (pos.z * view_matrix[6]) + view_matrix[7]
            qz = (pos.x * view_matrix[8]) + (pos.y * view_matrix[9]) + (pos.z * view_matrix[10]) + view_matrix[11]
            qw = (pos.x * view_matrix[12]) + (pos.y * view_matrix[13]) + (pos.z * view_matrix[14]) + view_matrix[15]
            if qw < 0.1: 
                return vec2(-1, -1)
            ndc_x = qx / qw
            ndc_y = qy / qw
            viewport = self.get_window_viewport()
            width = viewport["width"]
            height = viewport["height"]
            x = (width / 2.0) * (1.0 + ndc_x)
            y = (height / 2.0) * (1.0 - ndc_y) 
            if x < 0 or x > width or y < 0 or y > height:
                return vec2(-1, -1)
            return vec2(x, y)
        except Exception:
            return vec2(-1, -1)

class Overlay:
    def __init__(self, target_hwnd):
        self.target_hwnd = target_hwnd
        self.hwnd = None
        self.hbr_transparent = win32gui.CreateSolidBrush(win32api.RGB(0, 0, 0))
        self.wnd_class = "PythonOverlayClass"
        self.create_window()
        self.dc = win32gui.GetDC(self.hwnd)
        

        import win32ui
        self.font = win32ui.CreateFont({
            'name': 'Arial',
            'height': -12,
            'weight': win32con.FW_NORMAL,
        })
        win32gui.SelectObject(self.dc, self.font.GetSafeHandle())

    def create_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc
        wc.lpszClassName = self.wnd_class
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hbrBackground = self.hbr_transparent

        try:
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass 

        ex_style = win32con.WS_EX_TOPMOST | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED

        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            self.wnd_class,
            "Python Overlay",
            win32con.WS_POPUP,
            0, 0, 800, 600, 
            None, None, wc.hInstance, None
        )

        win32gui.SetLayeredWindowAttributes(self.hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

    def update_position(self, rect):
        try:
            win32gui.MoveWindow(self.hwnd, int(rect["x"]), int(rect["y"]), int(rect["width"]), int(rect["height"]), True)
        except Exception:
            pass

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def clear(self):
        try:
            rect = win32gui.GetClientRect(self.hwnd)
            win32gui.PatBlt(self.dc, 0, 0, rect[2], rect[3], win32con.BLACKNESS)
        except Exception:
            pass

    def draw_text(self, x, y, text, color=(255, 255, 255)):
        try:
            win32gui.SetTextColor(self.dc, win32api.RGB(*color))
            win32gui.SetBkMode(self.dc, win32con.TRANSPARENT)
            win32gui.ExtTextOut(self.dc, int(x), int(y), 0, None, text)
        except Exception:
            pass

    def draw_box(self, x, y, w, h, color=(255, 0, 0), thickness=1):
        try:
            pen = win32gui.CreatePen(win32con.PS_SOLID, thickness, win32api.RGB(*color))
            old_pen = win32gui.SelectObject(self.dc, pen)
            win32gui.SelectObject(self.dc, win32gui.GetStockObject(win32con.NULL_BRUSH))
            win32gui.Rectangle(self.dc, int(x), int(y), int(x + w), int(y + h))
            win32gui.SelectObject(self.dc, old_pen)
            win32gui.DeleteObject(pen)
        except Exception:
            pass

    def draw_line(self, x1, y1, x2, y2, color=(255, 0, 0), thickness=1):
        try:
            pen = win32gui.CreatePen(win32con.PS_SOLID, thickness, win32api.RGB(*color))
            old_pen = win32gui.SelectObject(self.dc, pen)
            win32gui.MoveToEx(self.dc, int(x1), int(y1))
            win32gui.LineTo(self.dc, int(x2), int(y2))
            win32gui.SelectObject(self.dc, old_pen)
            win32gui.DeleteObject(pen)
        except Exception:
            pass

shared_data_lock = threading.Lock()
cached_player_data = []
is_running = True

def data_update_thread(external):
    global cached_player_data, is_running
    
    DATA_UPDATE_INTERVAL = 0.1 
    error_count = 0
    
    while is_running and error_count < 5:
        try:
            raw_player_data = external.get_player_coordinates()
            player_data_for_render = []
            
            for p in raw_player_data:
                head_screen = external.world_to_screen(p["head_pos"])
                root_screen = external.world_to_screen(p["root_pos"])
                feet_screen = external.world_to_screen(p["feet_pos"])
                
                if head_screen.x != -1 and root_screen.x != -1 and feet_screen.x != -1:
                    p["head_screen"] = head_screen
                    p["root_screen"] = root_screen
                    p["feet_screen"] = feet_screen
                    player_data_for_render.append(p)

            with shared_data_lock:
                cached_player_data = player_data_for_render
            
            error_count = 0
            
        except Exception as e:
            error_count += 1
            if error_count >= 5:
                is_running = False
                break
        
        time.sleep(DATA_UPDATE_INTERVAL)

def main():
    global is_running
    
    color_window = ColorSettingsWindow()
    color_window.run()
    
    try:
        print("Инициализация robloxmemory...")
        external = robloxmemory()
        print(f"Процесс Roblox найден. PID: {external.process_id}")
    except Exception as e:
        print(f"Ошибка: {e}")
        traceback.print_exc()
        time.sleep(5)
        return

    data_thread = threading.Thread(target=data_update_thread, args=(external,), daemon=True)
    data_thread.start()

    viewport = external.get_window_viewport()
    
    try:
        overlay = Overlay(external.hwnd)
        overlay.update_position(viewport)
        print("Оверлей создан успешно")
    except Exception as e:
        print(f"Ошибка при создании оверлея: {e}")
        traceback.print_exc()
        return

    FPS_DELAY = 1/15
    position_update_counter = 0
    frame_count = 0
    
    print("Запуск цикла рендеринга...")
    
    try:
        while is_running:
            start_time = time.time()
            
            try:
                position_update_counter += 1
                if position_update_counter >= 15:
                    viewport = external.get_window_viewport()
                    overlay.update_position(viewport)
                    position_update_counter = 0
                
                overlay.clear()

                current_players = []
                with shared_data_lock:
                    current_players = list(cached_player_data)

                for p in current_players:
                    head_screen = p.get("head_screen")
                    feet_screen = p.get("feet_screen")
                    
                    if not head_screen or not feet_screen or head_screen.x == -1 or feet_screen.x == -1:
                        continue
                    
                    height = feet_screen.y - head_screen.y
                    if height <= 0:
                        continue
                        
                    width = height / 2.0
                    box_x = head_screen.x - width / 2
                    box_y = head_screen.y
                    
                    health = p.get("health")
                    box_color = COLOR_SETTINGS["box_color"]
                    
                    if health is not None and health > 500:
                        box_color = COLOR_SETTINGS["high_health_color"]
                    
                    overlay.draw_box(box_x, box_y, width, height, color=box_color, thickness=2)
                    
                    center_x = box_x + width / 2
                    bottom_y = box_y + height
                    overlay.draw_line(center_x, bottom_y, center_x, bottom_y + 10, color=COLOR_SETTINGS["line_color"], thickness=1)
                    
                    player_name = p.get("player_name", "Unknown")
                    max_health = p.get("max_health")
                    
                    overlay.draw_text(box_x, box_y - 15, player_name, color=COLOR_SETTINGS["text_color"])
                    
                    if health is not None and max_health is not None:
                        health_text = f"HP: {int(health)}/{int(max_health)}"
                        overlay.draw_text(box_x, box_y - 30, health_text, color=COLOR_SETTINGS["health_text_color"])

                frame_count += 1
                
                if frame_count >= 60:
                    frame_count = 0

            except Exception as e:
                break
            
            elapsed = time.time() - start_time
            sleep_time = FPS_DELAY - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except KeyboardInterrupt:
        print("Остановка по запросу пользователя...")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        is_running = False
        try:
            win32gui.ReleaseDC(overlay.hwnd, overlay.dc)
            win32gui.DestroyWindow(overlay.hwnd)
            if hasattr(overlay, 'font'):
                overlay.font.DeleteObject()
        except:
            pass
        print("Оверлей остановлен.")

if __name__ == "__main__":
    main()