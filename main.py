import sys
import os
import json
import telebot
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea,
    QListWidget, QListWidgetItem, QMessageBox, QFrame, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QFontMetrics

CONFIG_FILE = "config.json"

QSS = """
QMainWindow { background-color: #0e1621; }
QWidget { background-color: #0e1621; color: #ffffff; font-family: 'Segoe UI', sans-serif; }

QScrollBar:vertical {
    border: none;
    background: #0e1621;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2c3b4a;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none; background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QFrame#login_frame { background-color: #17212b; border-radius: 12px; }
QPushButton#start_btn { 
    background-color: #3390ec; border-radius: 6px; font-weight: bold; padding: 12px; color: white; border: none; 
}
QPushButton#start_btn:hover { background-color: #40a7e3; }

QFrame#sidebar_frame { background-color: #17212b; border: none; }
QLabel#sidebar_label {
    background-color: transparent;
    color: #3390ec;
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    margin-bottom: 5px;
}

QListWidget { background-color: #17212b; border: none; outline: none; }
QListWidget::item { padding: 15px; border-bottom: 1px solid #1c2733; }
QListWidget::item:hover { background-color: #202b36; }
QListWidget::item:selected { background-color: #2b5278; color: white; }

QLineEdit { 
    background-color: #242f3d; border: 1px solid #242f3d; border-radius: 6px; padding: 10px; color: white;
}
QLineEdit:focus { border: 1px solid #3390ec; }

QPushButton#action_btn { background-color: #3390ec; border-radius: 4px; font-weight: bold; border: none; color: white; }
QPushButton#del_btn { background-color: #d32f2f; border-radius: 4px; font-weight: bold; border: none; color: white; }

QPushButton#send_btn { 
    background: transparent; 
    color: #3390ec; 
    font-size: 38px; 
    border: none; 
    padding-bottom: 8px; 
}
QPushButton#send_btn:hover { color: #40a7e3; }
"""

class BotWorker(QObject):
    msg_signal = pyqtSignal(object, str, str)
    err_signal = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, token):
        super().__init__()
        self.token = token
        self.bot = telebot.TeleBot(token)
        self.is_running = True

    def run(self):
        @self.bot.message_handler(func=lambda message: True)
        def handle(m):
            if not self.is_running: return
            cid = m.chat.id
            user = m.from_user.username or m.from_user.first_name or "Unknown"
            self.msg_signal.emit(cid, f"@{user}", m.text)
        try:
            self.bot.remove_webhook()
            self.bot.infinity_polling(timeout=5)
        except Exception as e:
            if self.is_running: self.err_signal.emit(str(e))
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        self.bot.stop_polling()

class MessageBubble(QFrame):
    def __init__(self, text, side):
        super().__init__()
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 2, 15, 2)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        
        font = QFont('Segoe UI', 15)
        self.label.setFont(font)
        metrics = QFontMetrics(font)

        text_width = metrics.horizontalAdvance(text) + 40
        max_bubble_width = 550

        if text_width < max_bubble_width:
            self.label.setFixedWidth(text_width)
        else:
            self.label.setFixedWidth(max_bubble_width)

        radius_css = "border-radius: 15px; border-bottom-left-radius: 2px;" if side == "in" else "border-radius: 15px; border-bottom-right-radius: 2px;"

        self.label.setStyleSheet(f"""
            background-color: {"#2b5278" if side == "out" else "#182533"};
            color: white;
            padding: 7px 15px;
            {radius_css}
        """)
        
        if side == "out":
            main_layout.addStretch()
            main_layout.addWidget(self.label)
        else:
            main_layout.addWidget(self.label)
            main_layout.addStretch()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Dispatcher [github.com/radmin1337]")
        self.setFixedSize(1150, 800)
        self.setStyleSheet(QSS)

        self.full_config = {}
        self.chats = {} 
        self.current_token = ""
        self.current_id = None
        self.worker = None
        self.thread = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.load_all_configs()
        self.init_login_ui()
        self.init_main_ui()

    def load_all_configs(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.full_config = json.load(f)
            except: self.full_config = {}
        else: self.full_config = {}

    def save_all_configs(self):
        if self.current_token:
            self.full_config[self.current_token] = {"chats": self.chats}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.full_config, f, ensure_ascii=False, indent=4)

    def init_login_ui(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        frame = QFrame(objectName="login_frame")
        frame.setFixedSize(450, 280)
        f_lay = QVBoxLayout(frame)
        f_lay.setContentsMargins(40, 40, 40, 40)
        f_lay.setSpacing(20)
        
        title = QLabel("Telegram Dispatcher")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #3390ec;")
        title.setAlignment(Qt.AlignCenter)
        
        self.token_input = QLineEdit(placeholderText="Paste Bot Token here...")
        if self.full_config:
            try: self.token_input.setText(list(self.full_config.keys())[-1])
            except: pass
            
        btn = QPushButton("CONNECT")
        btn.setObjectName("start_btn")
        btn.clicked.connect(self.authorize)
        
        f_lay.addWidget(title)
        f_lay.addWidget(self.token_input)
        f_lay.addWidget(btn)
        layout.addWidget(frame)
        self.stack.addWidget(page)

    def init_main_ui(self):
        self.main_page = QWidget()
        main_layout = QHBoxLayout(self.main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame(objectName="sidebar_frame")
        sidebar.setFixedWidth(320)
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(15, 15, 15, 15)

        man_box = QVBoxLayout()
        lab = QLabel("CHATS")
        lab.setObjectName("sidebar_label")
        man_box.addWidget(lab)
        self.id_manage_input = QLineEdit(placeholderText="ID...")
        man_box.addWidget(self.id_manage_input)
        
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.setObjectName("action_btn")
        add_btn.setFixedHeight(30)
        rem_btn = QPushButton("Delete")
        rem_btn.setObjectName("del_btn")
        rem_btn.setFixedHeight(30)
        
        add_btn.clicked.connect(self.manual_add)
        rem_btn.clicked.connect(self.manual_rem)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rem_btn)
        man_box.addLayout(btn_row)
        side_lay.addLayout(man_box)

        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.switch_chat)
        side_lay.addWidget(self.chat_list)

        v_sep = QFrame()
        v_sep.setStyleSheet("background-color: #242f3d;")
        v_sep.setFixedWidth(1)

        chat_container = QWidget()
        c_lay = QVBoxLayout(chat_container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        header = QFrame(styleSheet="background-color: #17212b;")
        header.setFixedHeight(60)
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(25, 0, 25, 0)
        self.title_lab = QLabel("A new chat will appear when someone starts your bot")
        self.title_lab.setStyleSheet("font-weight: bold; font-size: 14px;")
        h_lay.addWidget(self.title_lab, alignment=Qt.AlignVCenter)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background-color: #0e1621;")
        self.scroll_content = QWidget()
        self.msg_layout = QVBoxLayout(self.scroll_content)
        self.msg_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        
        in_frame = QFrame(styleSheet="background-color: #17212b;")
        in_frame.setFixedHeight(85)
        i_lay = QHBoxLayout(in_frame)
        i_lay.setContentsMargins(20, 10, 20, 10)
        self.msg_input = QLineEdit(placeholderText="Write a message...", styleSheet="background: #0e1621; border: none; border-radius: 22px; padding: 12px 18px; font-size: 15px;")
        self.msg_input.returnPressed.connect(self.send_message)
        
        self.btn_send = QPushButton("➤", objectName="send_btn")
        self.btn_send.setFixedSize(55, 55)
        self.btn_send.clicked.connect(self.send_message)
        i_lay.addWidget(self.msg_input)
        i_lay.addWidget(self.btn_send)

        c_lay.addWidget(header)
        c_lay.addWidget(self.scroll)
        c_lay.addWidget(in_frame)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(v_sep)
        main_layout.addWidget(chat_container)
        self.stack.addWidget(self.main_page)

    def authorize(self):
        token = self.token_input.text().strip()
        if not token: return
        self.current_token = token
        token_data = self.full_config.get(token, {})
        saved_chats = token_data.get("chats", {})
        self.chats = {int(k): v for k, v in saved_chats.items()}
        self.stack.setCurrentIndex(1)
        self.populate_chats()
        self.start_bot_thread()

    def start_bot_thread(self):
        self.thread = QThread()
        self.worker = BotWorker(self.current_token)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.msg_signal.connect(self.handle_incoming)
        self.worker.err_signal.connect(lambda e: QMessageBox.critical(self, "API Error", e))
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def manual_add(self):
        raw_id = self.id_manage_input.text().strip()
        if not raw_id: return
        try:
            cid = int(raw_id)
            if cid not in self.chats:
                try:
                    chat_info = self.worker.bot.get_chat(cid)
                    name = f"@{chat_info.username}" if chat_info.username else chat_info.first_name
                except: name = f"User_{cid}"
                self.chats[cid] = {"name": name, "messages": []}
                self.populate_chats()
                self.save_all_configs()
            self.id_manage_input.clear()
        except: QMessageBox.warning(self, "Error", "Invalid Chat ID")

    def manual_rem(self):
        raw_id = self.id_manage_input.text().strip()
        if not raw_id: return
        try:
            cid = int(raw_id)
            if cid in self.chats:
                self.chats.pop(cid)
                if self.current_id == cid:
                    self.current_id = None
                    self.clear_layout(self.msg_layout)
                    self.title_lab.setText("A new chat will appear when someone starts your bot")
                self.populate_chats()
                self.save_all_configs()
            self.id_manage_input.clear()
        except: pass

    def populate_chats(self):
        self.chat_list.clear()
        for cid, info in self.chats.items():
            item = QListWidgetItem(f"{info['name']}\n{cid}")
            item.setData(Qt.UserRole, cid)
            self.chat_list.addItem(item)

    def handle_incoming(self, chat_id, name, text):
        if chat_id not in self.chats:
            self.chats[chat_id] = {"name": name, "messages": []}
            self.populate_chats()
        self.chats[chat_id]["messages"].append({"side": "in", "text": text})
        self.save_all_configs()
        if self.current_id == chat_id:
            bubble = MessageBubble(text, "in")
            self.msg_layout.insertWidget(self.msg_layout.count()-1, bubble)
            self.scroll_to_bottom()

    def send_message(self):
        if not self.current_id: return
        text = self.msg_input.text().strip()
        if not text: return
        try:
            self.worker.bot.send_message(self.current_id, text)
            self.chats[self.current_id]["messages"].append({"side": "out", "text": text})
            self.save_all_configs()
            bubble = MessageBubble(text, "out")
            self.msg_layout.insertWidget(self.msg_layout.count()-1, bubble)
            self.msg_input.clear()
            self.scroll_to_bottom()
        except Exception as e: QMessageBox.warning(self, "API Error", str(e))

    def clear_layout(self, layout):
        while layout.count() > 1:
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

    def switch_chat(self, item):
        self.current_id = item.data(Qt.UserRole)
        self.title_lab.setText(f"{self.chats[self.current_id]['name']}  |  {self.current_id}")
        self.update_view()

    def update_view(self):
        self.clear_layout(self.msg_layout)
        chat_data = self.chats[self.current_id]
        for msg in chat_data["messages"]:
            bubble = MessageBubble(msg["text"], msg["side"])
            self.msg_layout.insertWidget(self.msg_layout.count()-1, bubble)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum() + 200)

    def closeEvent(self, event):
        if self.worker: self.worker.stop()
        self.save_all_configs()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
