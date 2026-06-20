import tkinter as tk
import random
import time
import math
import os
import ctypes
import keyboard
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item
import threading
from tkinter import ttk
import sqlite3
import json
import urllib.request
import subprocess
class DesktopPet:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Succubus Pet")
        self.root.withdraw()
        
        # Make the window borderless and transparent
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Use magenta as the transparent color
        self.transparent_color = '#ff00ff'
        self.root.config(bg=self.transparent_color)
        self.root.wm_attributes("-transparentcolor", self.transparent_color)

        # Frame states
        self.frames_idle_left = []
        self.frames_idle_right = []
        self.frames_walk_left = []
        self.frames_walk_right = []
        self.frames_grab_left = []
        self.frames_grab_right = []
        self.frames_talk_left = []
        self.frames_talk_right = []
        self.frames_click_left = []
        self.frames_click_right = []
        self.frames_bored_left = []
        self.frames_bored_right = []
        self.current_frame = 0
        
        self.width, self.height = 100, 100
        self.load_images()

        self.image_offset_x = 160
        self.window_width = self.width + 320
        self.window_height = self.height

        # Canvas to show the image
        self.canvas = tk.Canvas(self.root, bg=self.transparent_color, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.image_item = None
        if self.frames_idle_left:
            self.canvas.config(width=self.window_width, height=self.window_height)
            self.image_item = self.canvas.create_image(self.image_offset_x, 0, image=self.frames_idle_left[0], anchor='nw')
        else:
            self.canvas.config(width=self.window_width, height=self.window_height)

        self.text_bg_item = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#cccccc", outline="#888888", width=1
        )
        self.text_item = self.canvas.create_text(0, 0, text="", font=("Arial", 8), fill="black", anchor="w", width=140)
        
        self.canvas.itemconfig(self.text_bg_item, state='hidden')
        self.canvas.itemconfig(self.text_item, state='hidden')

        # Position and state
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.x = self.screen_width // 2
        self.y = self.screen_height // 2
        
        # State machine: 'idle', 'wander', 'grab_mouse', 'bored'
        self.state = 'idle'
        self.state_timer = 0
        self.target_x = self.x
        self.target_y = self.y
        self.speed = 2.0
        self.facing_right = True

        # Typing detection
        self.last_key_time = 0
        self.typing_start_time = 0
        self.is_typing = False
        try:
            keyboard.on_press(self.on_key_press)
        except Exception as e:
            print(f"Keyboard hook failed: {e}")

        self.update_geometry()
        
        self.reminders = []
        self.regular_reminders = []
        self.is_running = False
        
        self.cursor_auto_remaining = 100.0
        self.cursor_api_remaining = 100.0
        self.last_cursor_check_time = time.time()
        self.cursor_check_interval = 300 # 5 minutes
        self.last_click_time = 0.0
        
        self.setup_tray()
        self.create_settings_window()
        
        # Start loops
        self.root.after(50, self.update)
        self.root.after(100, self.animate)

    def is_cursor_running(self):
        try:
            output = subprocess.check_output('tasklist /fi "imagename eq Cursor.exe"', shell=True).decode('cp866', errors='ignore')
            return "Cursor.exe" in output
        except Exception:
            return False

    def check_cursor_usage(self, manual=False):
        def _fetch_and_process():
            if not manual and not self.is_cursor_running():
                return
                
            db_path = os.path.expanduser(r"~\AppData\Roaming\Cursor\User\globalStorage\state.vscdb")
            if not os.path.exists(db_path):
                return
                
            try:
                conn = sqlite3.connect(db_path)
                val = conn.execute("SELECT value FROM ItemTable WHERE key='cursorAuth/accessToken'").fetchone()
                conn.close()
                
                if not val:
                    return
                    
                token = val[0]
                if token.startswith('"'): 
                    token = json.loads(token)
                    
                url = "https://api2.cursor.sh/aiserver.v1.DashboardService/GetCurrentPeriodUsage"
                req = urllib.request.Request(url, data=b"{}", headers={
                    "Authorization": f"Bearer {token}", 
                    "User-Agent": "Cursor", 
                    "Content-Type": "application/json"
                })
                res = urllib.request.urlopen(req).read().decode()
                data = json.loads(res)
                
                plan = data.get("planUsage", {})
                auto_used = plan.get("autoPercentUsed", 0)
                api_used = plan.get("apiPercentUsed", 0)
                
                new_auto = max(0.0, 100.0 - auto_used)
                new_api = max(0.0, 100.0 - api_used)
                
                if manual:
                    self.root.after(0, lambda: self.trigger_manual_cursor_notification(new_auto, new_api))
                else:
                    self.root.after(0, lambda: self.evaluate_cursor_thresholds("Composer", self.cursor_auto_remaining, new_auto))
                    self.root.after(0, lambda: self.evaluate_cursor_thresholds("API", self.cursor_api_remaining, new_api))
                    
                self.cursor_auto_remaining = new_auto
                self.cursor_api_remaining = new_api
                
            except Exception as e:
                print("Cursor fetch error:", e)
        
        threading.Thread(target=_fetch_and_process, daemon=True).start()

    def trigger_manual_cursor_notification(self, auto_rem, api_rem):
        self.state = 'talk'
        self.state_timer = 150 # 4.5 seconds
        self.show_text_bubble(f"У нас осталось {int(auto_rem)}% Composer и {int(api_rem)}% API в Cursor")
        
    def evaluate_cursor_thresholds(self, name, old_val, new_val):
        old_step = int(old_val / 5) * 5
        new_step = int(new_val / 5) * 5
        
        if new_step < old_step:
            if new_step <= 10:
                if name == "Composer":
                    msg = f"Эй, полегче с Composer'ом, у нас осталось всего {new_step}% запросов!"
                else:
                    msg = f"Эй, полегче с API Cursor, у нас осталось всего {new_step}% запросов ко внешним моделям!"
            else:
                if name == "Composer":
                    msg = f"Ты потратил 5% запросов к Composer! Осталось {new_step}%"
                else:
                    msg = f"Ты потратил 5% запросов к API внешних Cursor моделей! Осталось {new_step}%"
            
            if hasattr(self, 'current_reminder_text') and self.state == 'fly_to_center':
                self.current_reminder_text += "\n" + msg
            else:
                self.current_reminder_text = "Уведомление: " + msg
                self.target_x = self.screen_width // 2
                self.target_y = self.screen_height // 2
                self.state = 'fly_to_center'
                self.state_timer = 0

    def setup_tray(self):
        try:
            image = Image.open(os.path.join(os.path.dirname(__file__), 'assets', 'logo.png'))
        except:
            image = Image.new('RGB', (64, 64), color=(255, 192, 203))
        
        menu = pystray.Menu(
            item('Развернуть окно', self.on_tray_open),
            item('Закрыть', self.on_tray_exit)
        )
        self.tray_icon = pystray.Icon("SuccubusPet", image, "Succubus Pet", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def on_tray_open(self, icon, item):
        self.root.after(0, self.show_settings)

    def on_tray_exit(self, icon, item):
        self.tray_icon.stop()
        os._exit(0)

    def create_settings_window(self):
        self.settings = tk.Toplevel(self.root)
        self.settings.title("Succubus Pet - Настройки")
        
        width = 500
        height = 550
        x = (self.settings.winfo_screenwidth() // 2) - (width // 2)
        y = (self.settings.winfo_screenheight() // 2) - (height // 2)
        self.settings.geometry(f"{width}x{height}+{x}+{y}")
        self.settings.resizable(False, False)
        
        try:
            icon_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), 'assets', 'logo.png'))
            self.settings.iconphoto(False, icon_img)
        except:
            pass
            
        tk.Label(self.settings, text="Привет! Я суккуб, который живет на твоем рабочем столе 💖\n\nНапомнить тебе о чем-то важном?", font=("Arial", 11)).pack(pady=15)
        
        self.reminder_rows = []
        frame = tk.Frame(self.settings)
        frame.pack(pady=5)
        
        for i in range(5):
            row_frame = tk.Frame(frame)
            row_frame.pack(fill='x', pady=3)
            
            hours = [f"{h:02d}" for h in range(24)]
            mins = [f"{m:02d}" for m in range(0, 60, 5)]
            
            cb_h = ttk.Combobox(row_frame, values=hours, width=3, state="readonly")
            cb_h.set("12")
            cb_h.pack(side='left', padx=2)
            
            tk.Label(row_frame, text=":").pack(side='left')
            
            cb_m = ttk.Combobox(row_frame, values=mins, width=3, state="readonly")
            cb_m.set("00")
            cb_m.pack(side='left', padx=2)
            
            entry = tk.Entry(row_frame, width=45)
            entry.pack(side='left', padx=10)
            
            self.reminder_rows.append((cb_h, cb_m, entry))
            
        ttk.Separator(self.settings, orient='horizontal').pack(fill='x', padx=20, pady=10)
        tk.Label(self.settings, text="Регулярные уведомления (интервалы)", font=("Arial", 10, "bold")).pack(pady=5)
        
        self.regular_reminder_rows = []
        reg_frame = tk.Frame(self.settings)
        reg_frame.pack(pady=5)
        
        reg_hours = [str(h) for h in range(13)]
        reg_mins = [f"{m:02d}" for m in range(0, 60, 5)]
        
        for i in range(3):
            row_frame = tk.Frame(reg_frame)
            row_frame.pack(fill='x', pady=3)
            
            cb_h = ttk.Combobox(row_frame, values=reg_hours, width=3, state="readonly")
            cb_h.set("0")
            cb_h.pack(side='left', padx=2)
            tk.Label(row_frame, text="ч").pack(side='left')
            
            cb_m = ttk.Combobox(row_frame, values=reg_mins, width=3, state="readonly")
            cb_m.set("00")
            cb_m.pack(side='left', padx=2)
            tk.Label(row_frame, text="м").pack(side='left')
            
            entry = tk.Entry(row_frame, width=38)
            entry.pack(side='left', padx=10)
            
            self.regular_reminder_rows.append((cb_h, cb_m, entry))
            
        btn_frame = tk.Frame(self.settings)
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="Закрыть", command=lambda: os._exit(0), width=15).pack(side='left', padx=10)
        
        self.save_btn = tk.Button(btn_frame, text="Запустить", command=self.save_and_start, width=15)
        self.save_btn.pack(side='left', padx=10)

        tk.Label(self.settings, text="Succubus Pet © Yury Mikhno, 2026", font=("Arial", 8), fg="gray").pack(side='bottom', pady=5)

        self.settings.protocol("WM_DELETE_WINDOW", self.hide_settings)
        
        self.settings.deiconify()
        self.settings.lift()
        self.settings.attributes('-topmost', True)
        self.settings.after(100, lambda: self.settings.attributes('-topmost', False))
        self.settings.focus_force()

    def show_settings(self):
        self.settings.deiconify()
        self.settings.lift()
        self.save_btn.config(text="Сохранить")

    def hide_settings(self):
        self.settings.withdraw()

    def save_and_start(self):
        self.reminders = []
        for h_cb, m_cb, entry in self.reminder_rows:
            text = entry.get().strip()
            if text:
                self.reminders.append({
                    'hour': int(h_cb.get()),
                    'minute': int(m_cb.get()),
                    'text': text,
                    'triggered_today': False
                })
                
        new_regular_reminders = []
        for h_cb, m_cb, entry in self.regular_reminder_rows:
            text = entry.get().strip()
            h = int(h_cb.get())
            m = int(m_cb.get())
            interval_seconds = h * 3600 + m * 60
            if text and interval_seconds > 0:
                last_triggered = time.time()
                for old_rem in getattr(self, 'regular_reminders', []):
                    if old_rem['interval'] == interval_seconds and old_rem['text'] == text:
                        last_triggered = old_rem['last_triggered']
                        break
                new_regular_reminders.append({
                    'interval': interval_seconds,
                    'last_triggered': last_triggered,
                    'text': text
                })
        self.regular_reminders = new_regular_reminders
        
        self.hide_settings()
        self.root.deiconify()
        self.is_running = True

    def show_text_bubble(self, text):
        self.canvas.itemconfig(self.text_bg_item, state='normal')
        self.canvas.itemconfig(self.text_item, state='normal')
        self.canvas.itemconfig(self.text_item, text=text)
        
        if self.x + self.width + 120 > self.screen_width:
            self.canvas.itemconfig(self.text_item, anchor="e")
            self.canvas.coords(self.text_item, self.image_offset_x - 10, self.height // 2)
        else:
            self.canvas.itemconfig(self.text_item, anchor="w")
            self.canvas.coords(self.text_item, self.image_offset_x + self.width + 10, self.height // 2)
        
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox(self.text_item)
        if bbox:
            self.canvas.coords(self.text_bg_item, bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5)

    def load_images(self):
        anim_dir = os.path.join(os.path.dirname(__file__), 'assets', 'animations')
        if not os.path.exists(anim_dir):
            print(f"Animation directory not found at {anim_dir}.")
            self.load_fallback_gif()
            return
            
        def process_frame(img_path, flip=False):
            img = Image.open(img_path).convert("RGBA")
            if flip:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                
            w, h = img.size
            if w > 100:
                scale = 100.0 / w
                new_w = 100
                new_h = int(h * scale)
                img = img.resize((new_w, new_h), Image.NEAREST)
            else:
                new_w = w
                new_h = h
                
            datas = img.getdata()
            new_data = []
            for item in datas:
                if item[3] < 128:
                    new_data.append((255, 0, 255, 255))
                else:
                    new_data.append((item[0], item[1], item[2], 255))
            img.putdata(new_data)
            
            return ImageTk.PhotoImage(img), new_w, new_h

        def load_sequence(subfolder, flip=False):
            seq_dir = os.path.join(anim_dir, subfolder)
            frames = []
            if os.path.exists(seq_dir):
                files = sorted([f for f in os.listdir(seq_dir) if f.endswith('.png')])
                for f in files:
                    photo, w, h = process_frame(os.path.join(seq_dir, f), flip=flip)
                    frames.append(photo)
                    # Update global width/height based on frames
                    self.width, self.height = w, h
            return frames

        try:
            self.frames_idle_left = load_sequence('idle')
            self.frames_walk_left = load_sequence('walk')
            self.frames_grab_left = load_sequence('grab')
            self.frames_talk_left = load_sequence('talk')
            self.frames_click_left = load_sequence('click')
            
            self.frames_idle_right = load_sequence('idle', flip=True)
            self.frames_walk_right = load_sequence('walk', flip=True)
            self.frames_grab_right = load_sequence('grab', flip=True)
            self.frames_talk_right = load_sequence('talk', flip=True)
            self.frames_click_right = load_sequence('click', flip=True)
            
            print(f"Loaded animations.")
        except Exception as e:
            print(f"Error loading animations: {e}")
            self.load_fallback_gif()

    def load_fallback_gif(self):
        gif_path = os.path.join(os.path.dirname(__file__), 'assets', '4.gif')
        try:
            frames = []
            idx = 0
            temp_frame = tk.PhotoImage(file=gif_path, format="gif -index 0")
            orig_w = temp_frame.width()
            factor = 1
            if orig_w > 100:
                factor = math.ceil(orig_w / 100.0)

            while True:
                try:
                    frame = tk.PhotoImage(file=gif_path, format=f"gif -index {idx}")
                    if factor > 1:
                        frame = frame.subsample(int(factor), int(factor))
                    frames.append(frame)
                    idx += 1
                except tk.TclError:
                    break
            
            if len(frames) > 0:
                self.frames_idle_left = self.frames_idle_right = frames
                self.frames_walk_left = self.frames_walk_right = frames
                self.frames_grab_left = self.frames_grab_right = frames
                self.frames_talk_left = self.frames_talk_right = frames
                self.frames_click_left = self.frames_click_right = frames
                self.frames_bored_left = self.frames_bored_right = frames
                self.width = frames[0].width()
                self.height = frames[0].height()
        except Exception as e:
            print(f"Error loading fallback: {e}")

    def on_key_press(self, event):
        self.last_key_time = time.time()

    def on_click(self, event):
        now = time.time()
        diff = now - self.last_click_time
        
        # Ignore event bubbling (multiple events for a single click)
        if diff < 0.05:
            return "break"
            
        if diff <= 0.4:
            self.check_cursor_usage(manual=True)
            self.last_click_time = 0.0
        else:
            self.last_click_time = now
            if self.state not in ['click', 'talk', 'grab', 'fly_to_center']:
                self.state = 'click'
                self.state_timer = 50 
                self.current_frame = 0 # reset animation to start
                self.canvas.itemconfig(self.text_item, state='hidden')
                self.canvas.itemconfig(self.text_bg_item, state='hidden')
        return "break"

    def update_geometry(self):
        win_x = int(self.x) - self.image_offset_x
        win_y = int(self.y)
        self.root.geometry(f"{self.window_width}x{self.window_height}+{win_x}+{win_y}")

    def update(self):
        if not self.is_running:
            self.root.after(30, self.update)
            return

        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        dist_to_mouse = math.hypot(mx - cx, my - cy)
        
        now = time.time()
        
        # Check cursor api every 5 minutes
        if now - self.last_cursor_check_time > self.cursor_check_interval:
            self.last_cursor_check_time = now
            self.check_cursor_usage()
        
        current_time = time.strftime("%H:%M")
        local_time = time.localtime(now)
        
        reminder_active = False
        for r in self.reminders:
            if local_time.tm_hour == r['hour'] and local_time.tm_min == r['minute']:
                if not r['triggered_today']:
                    r['triggered_today'] = True
                    self.state = 'fly_to_center'
                    self.target_x = self.screen_width // 2 - self.width // 2
                    self.target_y = self.screen_height // 2 - self.height // 2
                    self.current_reminder_text = "Уведомление: " + r['text']
                    reminder_active = True
            elif r['triggered_today'] and local_time.tm_min != r['minute']:
                r['triggered_today'] = False
                
        for r in self.regular_reminders:
            if now - r['last_triggered'] >= r['interval']:
                with open("debug_log.txt", "a") as f:
                    f.write(f"Triggered regular reminder: {r['text']}, interval: {r['interval']}, last: {r['last_triggered']}, now: {now}\n")
                r['last_triggered'] = now
                
                was_flying = (self.state == 'fly_to_center')
                self.state = 'fly_to_center'
                self.target_x = self.screen_width // 2 - self.width // 2
                self.target_y = self.screen_height // 2 - self.height // 2
                
                if hasattr(self, 'current_reminder_text') and getattr(self, 'current_reminder_text', '') and was_flying:
                    self.current_reminder_text += "\n" + r['text']
                else:
                    self.current_reminder_text = "Регулярное уведомление: " + r['text']
                reminder_active = True
                
        if reminder_active:
            pass
        else:
            # Check typing
            if now - self.last_key_time < 0.6:
                if not self.is_typing:
                    self.is_typing = True
                    self.typing_start_time = now
                elif now - self.typing_start_time > 8.0 and self.state not in ['talk', 'click']:
                    self.state = 'talk'
                    self.state_timer = 100 # 3 seconds
                    self.show_text_bubble("Хороший мальчик... Продолжай печатать")
            else:
                self.is_typing = False
        
        # State transitions
        if self.state not in ['grab_mouse', 'talk', 'click', 'fly_to_center']:
            if dist_to_mouse < 100 and random.random() < 0.02:
                self.state = 'grab_mouse'
                self.state_timer = 60 # hold for ~2 seconds
                self.target_x = random.randint(50, self.screen_width - 50)
                self.target_y = random.randint(50, self.screen_height - 50)
        
        self.state_timer -= 1
        
        # Behavior based on state
        if self.state == 'talk':
            if self.state_timer <= 0:
                self.canvas.itemconfig(self.text_item, state='hidden')
                self.canvas.itemconfig(self.text_bg_item, state='hidden')
                self.state = 'idle'
                self.typing_start_time = now # reset typing timer so she doesn't immediately talk again
                self.state_timer = random.randint(30, 80)
                
        elif self.state == 'click':
            if self.state_timer <= 0:
                self.state = 'idle'
                self.state_timer = random.randint(30, 80)
                
        elif self.state == 'idle':
            if self.state_timer <= 0:
                self.state = 'wander'
                self.state_timer = random.randint(50, 150)
                self.target_x = self.x + random.randint(-300, 300)
                self.target_y = self.y + random.randint(-150, 150)
        
        elif self.state == 'wander':
            if self.state_timer <= 0:
                self.state = 'idle'
                self.state_timer = random.randint(30, 80)
            else:
                self.move_towards(self.target_x, self.target_y, speed=1.5)
                
        elif self.state == 'fly_to_center':
            self.move_towards(self.target_x, self.target_y, speed=10.0)
            dist = math.hypot(self.target_x - self.x, self.target_y - self.y)
            if dist < 10.0:
                self.x = self.target_x
                self.y = self.target_y
                self.state = 'talk'
                self.state_timer = 333
                self.show_text_bubble(self.current_reminder_text)
                
        elif self.state == 'grab_mouse':
            cursor_x = cx + (35 if self.facing_right else -35)
            cursor_y = cy + 40
            ctypes.windll.user32.SetCursorPos(int(cursor_x), int(cursor_y))
            self.move_towards(self.target_x, self.target_y, speed=8.0)
            if self.state_timer <= 0:
                self.state = 'idle'
                self.state_timer = random.randint(30, 80)

        self.x = max(0, min(self.screen_width - self.width, self.x))
        self.y = max(0, min(self.screen_height - self.height, self.y))
        self.update_geometry()
        self.root.after(30, self.update)

    def move_towards(self, tx, ty, speed):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        
        if dist > speed:
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed
            
        self.facing_right = dx > 0

    def animate(self):
        # Choose frames based on state
        if self.state in ['wander', 'fly_to_center']:
            frames = self.frames_walk_right if self.facing_right else self.frames_walk_left
        elif self.state == 'grab_mouse':
            frames = self.frames_grab_right if self.facing_right else self.frames_grab_left
        elif self.state == 'talk':
            frames = self.frames_talk_right if self.facing_right else self.frames_talk_left
        elif self.state == 'click':
            frames = self.frames_click_right if self.facing_right else self.frames_click_left
        elif self.state == 'bored':
            frames = self.frames_bored_right if self.facing_right else self.frames_bored_left
        else:
            frames = self.frames_idle_right if self.facing_right else self.frames_idle_left

        if not frames:
            frames = self.frames_idle_right if self.facing_right else self.frames_idle_left

        if frames:
            delay = 100
            if self.state in ['grab_mouse', 'wander']:
                delay = 50
                
            self.current_frame = (self.current_frame + 1) % len(frames)
            self.canvas.itemconfig(self.image_item, image=frames[self.current_frame])
        
        self.root.after(delay if frames else 100, self.animate)

    def run(self):
        self.root.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-1>", self.on_click)
        if self.image_item is not None:
            self.canvas.tag_bind(self.image_item, "<Button-1>", self.on_click)
        self.root.bind("<Button-3>", lambda e: os._exit(0))
        self.root.mainloop()

if __name__ == '__main__':
    pet = DesktopPet()
    pet.run()
