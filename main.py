import sys
import os
import json
import telebot
import shutil
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea,
    QListWidget, QListWidgetItem, QMessageBox, QFrame, QStackedWidget, 
    QFileDialog, QMenu, QInputDialog, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QUrl, QSize
from PyQt5.QtGui import QFont, QFontMetrics, QPixmap, QMovie

CONFIG_FILE = "config.json"
DOWNLOADS_DIR = os.path.abspath("downloads")

if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

QSS = """
QMainWindow { background-color: #0e1621; }
QWidget { background-color: #0e1621; color: #ffffff; font-family: 'Segoe UI', sans-serif; }

QScrollBar:vertical { border: none; background: #0e1621; width: 6px; margin: 0px; }
QScrollBar::handle:vertical { background: #2c3b4a; min-height: 20px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }

QFrame#login_frame { background-color: #17212b; border-radius: 12px; }
QLabel#login_title { background-color: transparent; color: #3390ec; font-size: 24px; font-weight: bold; border: none; }

QFrame#sidebar_frame { background-color: #17212b; border: none; }
QLabel#sidebar_label { background-color: transparent; color: #3390ec; font-weight: bold; font-size: 11px; text-transform: uppercase; margin-bottom: 5px; }

QListWidget { background-color: #17212b; border: none; outline: none; }
QListWidget::item { padding: 15px; border-bottom: 1px solid #1c2733; }
QListWidget::item:hover { background-color: #202b36; }
QListWidget::item:selected { background-color: #2b5278; color: white; }

QLineEdit { background-color: #242f3d; border: 1px solid #242f3d; border-radius: 6px; padding: 10px; color: white; }
QLineEdit:focus { border: 1px solid #3390ec; }

QPushButton#start_btn { background-color: #3390ec; border-radius: 6px; font-weight: bold; padding: 12px; color: white; border: none; }
QPushButton#action_btn { background-color: #3390ec; border-radius: 4px; font-weight: bold; border: none; color: white; }
QPushButton#del_btn { background-color: #d32f2f; border-radius: 4px; font-weight: bold; border: none; color: white; }
QPushButton#send_btn { background: transparent; color: #3390ec; font-size: 38px; border: none; padding-bottom: 8px; }
QPushButton#attach_btn { background: transparent; color: #7f91a4; font-size: 24px; border: none; padding-bottom: 5px;}

QFrame#loading_overlay { background-color: rgba(14, 22, 33, 220); }
QFrame#loading_box { background-color: #17212b; border-radius: 15px; border: 1px solid #242f3d; }
QProgressBar { border: 1px solid #242f3d; border-radius: 5px; text-align: center; background-color: #0e1621; height: 12px; }
QProgressBar::chunk { background-color: #3390ec; }
QPushButton#cancel_btn { background-color: #d32f2f; border-radius: 5px; font-weight: bold; color: white; border: none; padding: 8px; }

QMenu { background-color: #17212b; border: 1px solid #242f3d; color: white; }
QMenu::item:selected { background-color: #2b5278; }
"""

def reveal_in_explorer(path):
    if not path or not os.path.exists(path): return
    path = os.path.normpath(path)
    if sys.platform == 'win32': subprocess.run(['explorer', '/select,', path])
    else: subprocess.run(['open', os.path.dirname(path)])

def format_filename(name):
    if len(name) <= 15: return name
    parts = name.rsplit('.', 1)
    ext = parts[1] if len(parts) > 1 else ""
    return f"{parts[0][:10]}...{ext}"

def get_media_file_id(m):
    for attr in ['video', 'audio', 'document', 'voice', 'animation', 'sticker']:
        obj = getattr(m, attr, None)
        if obj: return obj.file_id
    if m.photo: return m.photo[-1].file_id
    return None

class TaskWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, task_type, bot, **kwargs):
        super().__init__()
        self.task_type, self.bot, self.kwargs = task_type, bot, kwargs
        self.is_cancelled = False

    def run(self):
        try:
            if self.task_type == "download":
                fid, ext = self.kwargs['file_id'], self.kwargs['ext']
                f_info = self.bot.get_file(fid)
                down = self.bot.download_file(f_info.file_path)
                p = os.path.join(DOWNLOADS_DIR, f"{fid}.{ext}")
                with open(p, 'wb') as f: f.write(down)
                self.finished.emit(p)
            elif self.task_type == "send_file":
                cid, path, f_type = self.kwargs['cid'], self.kwargs['path'], self.kwargs['f_type']
                with open(path, 'rb') as f:
                    if f_type == 'photo': res = self.bot.send_photo(cid, f)
                    elif f_type == 'sticker': res = self.bot.send_sticker(cid, f)
                    elif f_type == 'video': res = self.bot.send_video(cid, f)
                    else: res = self.bot.send_document(cid, f)
                self.finished.emit(res)
        except Exception as e:
            if not self.is_cancelled: self.error.emit(str(e))

class BotWorker(QObject):
    msg_signal = pyqtSignal(object, str, dict)
    err_signal = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, token):
        super().__init__()
        self.bot = telebot.TeleBot(token); self.is_running = True

    def run(self):
        @self.bot.message_handler(content_types=['text', 'photo', 'sticker', 'video', 'document', 'audio', 'voice', 'animation'])
        def handle_all(m):
            if not self.is_running: return
            cid, user = m.chat.id, (m.from_user.username or m.from_user.first_name)
            data = {"side": "in", "type": "text", "content": "", "message_id": m.message_id}
            
            if m.content_type == 'text': data.update({"type": "text", "content": m.text})
            elif m.content_type == 'photo':
                fid = m.photo[-1].file_id
                data.update({"type": "photo", "content": "", "file_id": fid, "ext": "jpg"})
            elif m.content_type == 'sticker':
                fid = m.sticker.file_id
                data.update({"type": "sticker", "content": "", "file_id": fid, "ext": "webp"})
            else:
                attr = m.content_type
                obj = getattr(m, attr)
                fid = obj.file_id
                ext = "mp4" if attr in ['video', 'animation'] else "ogg" if attr == 'voice' else "mp3" if attr == 'audio' else obj.file_name.split('.')[-1]
                name = getattr(obj, 'file_name', None) or f"{attr}.{ext}"
                data.update({"type": "file", "content": f"{name}|", "file_id": fid, "ext": ext})
            self.msg_signal.emit(cid, f"@{user}", data)
        try:
            self.bot.remove_webhook(); self.bot.infinity_polling(timeout=5)
        except Exception as e:
            if self.is_running: self.err_signal.emit(str(e))
        finally: self.finished.emit()

    def stop(self):
        self.is_running = False; self.bot.stop_polling()

class MessageBubble(QFrame):
    edit_signal = pyqtSignal(int, str)
    delete_signal = pyqtSignal(int)
    download_request = pyqtSignal(int)

    def __init__(self, msg, index):
        super().__init__()
        self.msg, self.index = msg, index
        content = msg.get('content', '')
        self.file_path = content.split('|')[1] if '|' in content else content
        
        main_layout = QHBoxLayout(self); main_layout.setContentsMargins(15, 2, 15, 2)
        m_type, side = msg.get('type', 'text'), msg.get('side', 'in')
        color = "#2b5278" if side == "out" else "#182533"

        self.bubble = QFrame()
        self.b_lay = QVBoxLayout(self.bubble); self.b_lay.setContentsMargins(0,0,0,0)

        if m_type == 'text':
            lbl = QLabel(msg['content']); lbl.setWordWrap(True)
            font = QFont('Segoe UI', 15); lbl.setFont(font)
            lbl.setFixedWidth(min(QFontMetrics(font).horizontalAdvance(msg['content']) + 40, 550))
            lbl.setStyleSheet(f"background-color: {color}; color: white; padding: 7px 15px; border-radius: 12px;")
            self.bubble.setFixedWidth(lbl.width()); self.b_lay.addWidget(lbl)
        
        elif m_type == 'photo':
            self.file_path = content
            lbl = QLabel()
            if os.path.exists(self.file_path):
                pix = QPixmap(self.file_path)
                scaled = pix.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lbl.setPixmap(scaled)
                self.bubble.setFixedWidth(scaled.width() + 10)
            else:
                lbl.setText("⬇️"); lbl.setFixedSize(100, 100); lbl.setAlignment(Qt.AlignCenter)
                self.bubble.setFixedWidth(100)
            lbl.setStyleSheet(f"background-color: {color}; padding: 5px; border-radius: 12px; font-size: 30px;")
            self.b_lay.addWidget(lbl)

        elif m_type == 'sticker':
            self.file_path = content
            lbl = QLabel()
            if os.path.exists(self.file_path):
                pix = QPixmap(self.file_path)
                scaled = pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lbl.setPixmap(scaled)
                self.bubble.setFixedWidth(scaled.width())
            else:
                lbl.setText("⬇️"); lbl.setFixedSize(100, 100); lbl.setAlignment(Qt.AlignCenter)
                self.bubble.setFixedWidth(100)
            lbl.setStyleSheet("background: transparent; font-size: 30px;")
            self.b_lay.addWidget(lbl)

        elif m_type == 'file':
            try: name = msg['content'].split('|')[0]
            except: name = "File"
            f_frame = QFrame(); f_frame.setFixedSize(230, 65)
            f_frame.setStyleSheet(f"background-color: {color}; border-radius: 12px;")
            f_lay = QHBoxLayout(f_frame); f_lay.setContentsMargins(10, 0, 10, 0)
            icon = "📁" if (self.file_path and os.path.exists(self.file_path)) else "⬇️"
            icon_lab = QLabel(icon); icon_lab.setFixedSize(42, 42); icon_lab.setAlignment(Qt.AlignCenter)
            icon_lab.setStyleSheet("background-color: #3390ec; border-radius: 21px; font-size: 18px; padding-left: 0px;")
            name_lab = QLabel(format_filename(name)); name_lab.setStyleSheet("background: transparent; font-weight: bold; font-size: 13px;")
            f_lay.addWidget(icon_lab); f_lay.addWidget(name_lab); f_lay.addStretch()
            self.bubble.setFixedWidth(230); self.b_lay.addWidget(f_frame)

        if side == "out":
            main_layout.addStretch(); main_layout.addWidget(self.bubble)
            self.bubble.setContextMenuPolicy(Qt.CustomContextMenu)
            self.bubble.customContextMenuRequested.connect(self.show_menu)
        else:
            main_layout.addWidget(self.bubble); main_layout.addStretch()
        self.bubble.mousePressEvent = self.on_bubble_click

    def show_menu(self, pos):
        menu = QMenu(); menu.setStyleSheet(QSS)
        if self.msg.get('type') == 'text':
            menu.addAction("Edit").triggered.connect(lambda: self.edit_signal.emit(self.index, self.msg['content']))
        menu.addAction("Delete").triggered.connect(lambda: self.delete_signal.emit(self.index))
        menu.exec_(self.bubble.mapToGlobal(pos))

    def on_bubble_click(self, event):
        if event.button() == Qt.LeftButton:
            if self.msg.get('type') == 'text': return # Игнорим клик по тексту
            if self.file_path and os.path.exists(self.file_path): reveal_in_explorer(self.file_path)
            elif self.msg.get('file_id'): self.download_request.emit(self.index)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Dispatcher [github.com/radmin1337]")
        self.setFixedSize(1150, 800); self.setStyleSheet(QSS)
        self.full_config, self.chats, self.current_token, self.current_id, self.worker, self.current_task = {}, {}, "", None, None, None
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.load_all_configs(); self.init_login_ui(); self.init_main_ui(); self.init_overlay()

    def init_overlay(self):
        self.overlay = QFrame(self); self.overlay.setObjectName("loading_overlay"); self.overlay.setGeometry(0, 0, 1150, 800); self.overlay.hide()
        vbox = QVBoxLayout(self.overlay); self.loading_box = QFrame(); self.loading_box.setObjectName("loading_box")
        self.loading_box.setFixedSize(300, 180); box_lay = QVBoxLayout(self.loading_box); box_lay.setContentsMargins(20, 20, 20, 20)
        self.overlay_label = QLabel("Loading..."); self.overlay_label.setAlignment(Qt.AlignCenter)
        self.overlay_pbar = QProgressBar(); self.overlay_pbar.setRange(0, 0)
        btn_c = QPushButton("Cancel"); btn_c.setObjectName("cancel_btn"); btn_c.clicked.connect(self.cancel_task)
        box_lay.addWidget(self.overlay_label); box_lay.addWidget(self.overlay_pbar); box_lay.addSpacing(10); box_lay.addWidget(btn_c)
        vbox.addWidget(self.loading_box, alignment=Qt.AlignCenter)

    def show_loading(self, text): self.overlay_label.setText(text); self.overlay.show(); self.overlay.raise_()

    def cancel_task(self):
        if self.current_task: self.current_task.is_cancelled = True; self.current_task.terminate()
        self.overlay.hide()

    def load_all_configs(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: self.full_config = json.load(f)
            except: pass

    def save_all_configs(self):
        if self.current_token: self.full_config[self.current_token] = {"chats": self.chats}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(self.full_config, f, ensure_ascii=False, indent=4)

    def authorize(self):
        t = self.token_input.text().strip()
        if not t: return
        self.current_token = t
        d = self.full_config.get(t, {})
        self.chats = {int(k): v for k, v in d.get("chats", {}).items()}
        self.stack.setCurrentIndex(1); self.populate_chats(); self.start_bot_thread()

    def init_login_ui(self):
        p = QWidget(); l = QVBoxLayout(p); l.setAlignment(Qt.AlignCenter); f = QFrame(objectName="login_frame"); f.setFixedSize(450, 280)
        fl = QVBoxLayout(f); fl.setContentsMargins(40,40,40,40); fl.setSpacing(20); t = QLabel("Telegram Dispatcher"); t.setObjectName("login_title")
        self.token_input = QLineEdit(placeholderText="Paste Bot Token here...")
        if self.full_config: 
            try: self.token_input.setText(list(self.full_config.keys())[-1])
            except: pass
        b = QPushButton("CONNECT", objectName="start_btn"); b.clicked.connect(self.authorize)
        fl.addWidget(t, alignment=Qt.AlignCenter); fl.addWidget(self.token_input); fl.addWidget(b); l.addWidget(f); self.stack.addWidget(p)

    def init_main_ui(self):
        self.main_page = QWidget(); ml = QHBoxLayout(self.main_page); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        s = QFrame(objectName="sidebar_frame"); s.setFixedWidth(320); sl = QVBoxLayout(s); sl.setContentsMargins(15,15,15,15)
        mb = QVBoxLayout(); sl.addLayout(mb); mb.addWidget(QLabel("CHATS", objectName="sidebar_label"))
        self.id_manage_input = QLineEdit(placeholderText="ID..."); mb.addWidget(self.id_manage_input)
        br = QHBoxLayout(); mb.addLayout(br); a = QPushButton("Add", objectName="action_btn"); a.setFixedHeight(30); a.clicked.connect(self.manual_add)
        d = QPushButton("Delete", objectName="del_btn"); d.setFixedHeight(30); d.clicked.connect(self.manual_rem)
        br.addWidget(a); br.addWidget(d); self.chat_list = QListWidget(); self.chat_list.itemClicked.connect(self.switch_chat); sl.addWidget(self.chat_list)
        v = QFrame(styleSheet="background-color: #242f3d;"); v.setFixedWidth(1); cc = QWidget(); cl = QVBoxLayout(cc); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)
        h = QFrame(styleSheet="background-color: #17212b;"); h.setFixedHeight(60); hl = QVBoxLayout(h); hl.setContentsMargins(25,0,25,0)
        self.title_lab = QLabel("Select a chat"); self.title_lab.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        hl.addWidget(self.title_lab, alignment=Qt.AlignVCenter); self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setStyleSheet("border: none; background-color: #0e1621;")
        self.sc = QWidget(); self.msg_layout = QVBoxLayout(self.sc); self.msg_layout.addStretch(); self.scroll.setWidget(self.sc)
        ifm = QFrame(styleSheet="background-color: #17212b;"); ifm.setFixedHeight(85); il = QHBoxLayout(ifm); il.setContentsMargins(20,10,20,10)
        at = QPushButton("📎", objectName="attach_btn"); at.clicked.connect(self.attach_file); self.msg_input = QLineEdit(placeholderText="Write a message...", styleSheet="background: #0e1621; border: none; border-radius: 22px; padding: 12px 18px; font-size: 15px;")
        self.msg_input.returnPressed.connect(self.send_message); sb = QPushButton("➤", objectName="send_btn"); sb.setFixedSize(55,55); sb.clicked.connect(self.send_message)
        il.addWidget(at); il.addWidget(self.msg_input); il.addWidget(sb); cl.addWidget(h); cl.addWidget(self.scroll); cl.addWidget(ifm)
        ml.addWidget(s); ml.addWidget(v); ml.addWidget(cc); self.stack.addWidget(self.main_page)

    def start_bot_thread(self):
        self.thread = QThread(); self.worker = BotWorker(self.current_token); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.msg_signal.connect(self.handle_incoming)
        self.worker.err_signal.connect(lambda e: QMessageBox.critical(self, "API Error", e))
        self.worker.finished.connect(self.thread.quit); self.thread.start()

    def request_download(self, idx):
        msg = self.chats[self.current_id]["messages"][idx]
        ext = msg.get('ext', 'dat')
        self.show_loading("Downloading file...")
        self.current_task = TaskWorker("download", self.worker.bot, file_id=msg['file_id'], ext=ext)
        self.current_task.finished.connect(lambda p: self.on_task_finished(idx, p))
        self.current_task.error.connect(lambda e: [self.overlay.hide(), QMessageBox.warning(self, "Error", e)])
        self.current_task.start()

    def on_task_finished(self, idx, res):
        self.overlay.hide(); m = self.chats[self.current_id]["messages"][idx]
        if m['type'] == 'file': m['content'] = f"{m['content'].split('|')[0]}|{res}"
        else: m['content'] = res
        self.save_all_configs(); self.update_view(); reveal_in_explorer(res)

    def attach_file(self):
        if not self.current_id: return
        p, _ = QFileDialog.getOpenFileName(self, "Select File")
        if not p: return
        ext = p.split('.')[-1].lower()
        f_type = 'photo' if ext in ['jpg', 'jpeg', 'png'] else 'sticker' if ext == 'webp' else 'video' if ext == 'mp4' else 'file'
        self.show_loading("Sending file...")
        self.current_task = TaskWorker("send_file", self.worker.bot, cid=self.current_id, path=p, f_type=f_type)
        self.current_task.finished.connect(lambda m: self.on_send_finished(m, p, f_type)); self.current_task.start()

    def on_send_finished(self, m, p, f_type):
        self.overlay.hide(); fid = get_media_file_id(m)
        content = p if f_type != 'file' else f"{os.path.basename(p)}|{p}"
        self.add_msg(f_type, content, 'out', fid, m.message_id)

    def manual_add(self):
        try:
            cid = int(self.id_manage_input.text().strip())
            if cid not in self.chats:
                c = self.worker.bot.get_chat(cid); name = f"@{c.username}" if c.username else c.first_name
                self.chats[cid] = {"name": name, "messages": []}; self.populate_chats(); self.save_all_configs()
        except: pass

    def manual_rem(self):
        try:
            cid = int(self.id_manage_input.text().strip())
            if cid in self.chats:
                self.chats.pop(cid); self.populate_chats(); self.save_all_configs()
                if self.current_id == cid: self.current_id = None; self.update_view()
        except: pass

    def populate_chats(self):
        self.chat_list.clear()
        for cid, info in self.chats.items():
            i = QListWidgetItem(f"{info['name']}\n{cid}"); i.setData(Qt.UserRole, cid); self.chat_list.addItem(i)

    def handle_incoming(self, cid, name, msg):
        if cid not in self.chats: self.chats[cid] = {"name": name, "messages": []}; self.populate_chats()
        self.chats[cid]["messages"].append(msg); self.save_all_configs()
        if self.current_id == cid: self.update_view()

    def send_message(self):
        t = self.msg_input.text().strip()
        if not t or not self.current_id: return
        try:
            m = self.worker.bot.send_message(self.current_id, t)
            self.add_msg('text', t, 'out', None, m.message_id); self.msg_input.clear()
        except Exception as e: QMessageBox.warning(self, "Error", str(e))

    def add_msg(self, t, c, s, fid=None, mid=None):
        ext = c.split('.')[-1] if '.' in c else "dat"
        d = {"type": t, "content": c, "side": s, "file_id": fid, "message_id": mid, "ext": ext}
        self.chats[self.current_id]["messages"].append(d); self.save_all_configs(); self.update_view()

    def delete_message(self, idx):
        m = self.chats[self.current_id]["messages"][idx]
        try: self.worker.bot.delete_message(self.current_id, m['message_id'])
        except: pass
        self.chats[self.current_id]["messages"].pop(idx); self.save_all_configs(); self.update_view()

    def edit_message(self, idx, old):
        dialog = QInputDialog(self); dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("Edit Message"); dialog.setLabelText("New text:"); dialog.setTextValue(old)
        if dialog.exec_() == QInputDialog.Accepted:
            new_t = dialog.textValue()
            if new_t and new_t != old:
                m = self.chats[self.current_id]["messages"][idx]
                try:
                    self.worker.bot.edit_message_text(new_t, self.current_id, m['message_id'])
                    self.chats[self.current_id]["messages"][idx]['content'] = new_t
                    self.save_all_configs(); self.update_view()
                except Exception as e: QMessageBox.warning(self, "Error", str(e))

    def switch_chat(self, item):
        self.current_id = item.data(Qt.UserRole); self.title_lab.setText(f"{self.chats[self.current_id]['name']}  |  {self.current_id}"); self.update_view()

    def update_view(self):
        while self.msg_layout.count() > 1:
            c = self.msg_layout.takeAt(0)
            if c.widget(): c.widget().deleteLater()
        if not self.current_id: return
        for i, m in enumerate(self.chats[self.current_id].get("messages", [])):
            b = MessageBubble(m, i); b.edit_signal.connect(self.edit_message); b.delete_signal.connect(self.delete_message)
            b.download_request.connect(self.request_download); self.msg_layout.insertWidget(self.msg_layout.count()-1, b)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum() + 1000)

    def closeEvent(self, event):
        if self.worker: self.worker.stop()
        self.save_all_configs()
        if os.path.exists(DOWNLOADS_DIR): shutil.rmtree(DOWNLOADS_DIR); os.makedirs(DOWNLOADS_DIR)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    w = MainWindow(); w.show(); sys.exit(app.exec_())
