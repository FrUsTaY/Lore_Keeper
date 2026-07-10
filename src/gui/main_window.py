from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QTextEdit, QListWidget, QLabel, QStatusBar, QMessageBox,
    QSystemTrayIcon, QMenu, QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QCheckBox,
    QApplication
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QStyle
import os

from src.gui.workers import CaptureWorker, GenerationWorker
from src.session_manager import SessionManager
from src.config_manager import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["LM Studio", "Hugging Face"])
        self.provider_combo.setCurrentText(self.config_manager.get("llm_provider", "LM Studio"))
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        layout.addRow("Провайдер LLM:", self.provider_combo)

        self.url_input = QLineEdit(self.config_manager.get("api_url"))
        self.url_label = QLabel("LM Studio API URL:")
        layout.addRow(self.url_label, self.url_input)

        self.hf_token_input = QLineEdit(self.config_manager.get("hf_token", ""))
        self.hf_token_input.setEchoMode(QLineEdit.Password)
        self.hf_token_label = QLabel("Hugging Face Token:")
        layout.addRow(self.hf_token_label, self.hf_token_input)

        self.hf_model_input = QLineEdit(self.config_manager.get("hf_model", "mistralai/Mistral-7B-Instruct-v0.2"))
        self.hf_model_label = QLabel("Hugging Face Model:")
        layout.addRow(self.hf_model_label, self.hf_model_input)

        self.on_provider_changed(self.provider_combo.currentText())

        self.genre_combo = QComboBox()
        self.genre_combo.addItems(["fantasy", "cyberpunk", "realism", "horror"])
        self.genre_combo.setCurrentText(self.config_manager.get("genre", "fantasy"))
        layout.addRow("Жанр по умолчанию:", self.genre_combo)

        self.tesseract_input = QLineEdit(self.config_manager.get("tesseract_path", r"C:\Program Files\Tesseract-OCR\tesseract.exe"))
        layout.addRow("Путь к Tesseract:", self.tesseract_input)

        self.save_screenshots_cb = QCheckBox()
        self.save_screenshots_cb.setChecked(self.config_manager.get("save_screenshots", True))
        layout.addRow("Сохранять скриншоты:", self.save_screenshots_cb)

        self.screenshots_path_input = QLineEdit(self.config_manager.get("screenshots_path", "outputs/screenshots"))
        layout.addRow("Путь к скриншотам:", self.screenshots_path_input)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)
        layout.addRow("", save_btn)

    def on_provider_changed(self, provider):
        is_lm_studio = (provider == "LM Studio")

        self.url_label.setVisible(is_lm_studio)
        self.url_input.setVisible(is_lm_studio)

        self.hf_token_label.setVisible(not is_lm_studio)
        self.hf_token_input.setVisible(not is_lm_studio)
        self.hf_model_label.setVisible(not is_lm_studio)
        self.hf_model_input.setVisible(not is_lm_studio)

    def save_settings(self):
        config = self.config_manager.config
        config["llm_provider"] = self.provider_combo.currentText()
        config["api_url"] = self.url_input.text()
        config["hf_token"] = self.hf_token_input.text()
        config["hf_model"] = self.hf_model_input.text()
        config["genre"] = self.genre_combo.currentText()
        config["tesseract_path"] = self.tesseract_input.text()
        config["save_screenshots"] = self.save_screenshots_cb.isChecked()
        config["screenshots_path"] = self.screenshots_path_input.text()
        self.config_manager.save_config(config)
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Нарративный Архивариус (Lore Keeper)")
        self.resize(800, 600)

        self.config_manager = ConfigManager()
        self.session_manager = SessionManager()
        self.capture_worker = None
        self.generation_worker = None

        self.setup_ui()
        self.setup_tray()
        self.load_sessions()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Старт Записи")
        self.btn_start.clicked.connect(self.start_recording)

        self.btn_stop = QPushButton("⏹ Стоп Записи")
        self.btn_stop.clicked.connect(self.stop_recording)
        self.btn_stop.setEnabled(False)

        self.btn_settings = QPushButton("⚙ Настройки")
        self.btn_settings.clicked.connect(self.open_settings)

        toolbar_layout.addWidget(self.btn_start)
        toolbar_layout.addWidget(self.btn_stop)
        toolbar_layout.addWidget(self.btn_settings)
        toolbar_layout.addStretch()

        main_layout.addLayout(toolbar_layout)

        # Tabs
        self.tabs = QTabWidget()

        # Tab 1: Sessions
        self.tab_sessions = QWidget()
        sess_layout = QVBoxLayout(self.tab_sessions)
        self.list_sessions = QListWidget()

        btn_generate = QPushButton("Сгенерировать историю из выбранной сессии")
        btn_generate.clicked.connect(self.start_generation)

        sess_layout.addWidget(QLabel("Сохраненные сессии:"))
        sess_layout.addWidget(self.list_sessions)
        sess_layout.addWidget(btn_generate)
        self.tabs.addTab(self.tab_sessions, "Сессии")

        # Tab 2: Live Log
        self.tab_live = QWidget()
        live_layout = QVBoxLayout(self.tab_live)
        self.text_live_log = QTextEdit()
        self.text_live_log.setReadOnly(True)
        live_layout.addWidget(self.text_live_log)
        self.tabs.addTab(self.tab_live, "Текущий Лог")

        # Tab 3: Story Library
        self.tab_stories = QWidget()
        stories_layout = QHBoxLayout(self.tab_stories)

        self.list_stories = QListWidget()
        self.list_stories.itemClicked.connect(self.load_story_text)

        self.text_story_view = QTextEdit()
        self.text_story_view.setReadOnly(True)

        stories_layout.addWidget(self.list_stories, 1)
        stories_layout.addWidget(self.text_story_view, 2)

        self.tabs.addTab(self.tab_stories, "Библиотека историй")
        self.load_stories()

        main_layout.addWidget(self.tabs)

        # Bottom layout for Exit button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_exit = QPushButton("Выход из программы")
        self.btn_exit.clicked.connect(self.quit_app)
        bottom_layout.addWidget(self.btn_exit)
        main_layout.addLayout(bottom_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Idle")

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Note: We need a real icon in a real app, using default empty icon for MVP
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        tray_menu = QMenu()

        show_action = QAction("Показать окно", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        quit_action = QAction("Выйти", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def load_sessions(self):
        self.list_sessions.clear()
        sessions = self.session_manager.get_all_sessions()
        for s in sessions:
            self.list_sessions.addItem(f"{s['id']} (Событий: {s['event_count']}) | {s['file']}")

    def load_stories(self):
        self.list_stories.clear()
        stories_dir = "outputs/stories"
        os.makedirs(stories_dir, exist_ok=True)
        for f in os.listdir(stories_dir):
            if f.endswith(".md"):
                self.list_stories.addItem(f)

    def load_story_text(self, item):
        filepath = os.path.join("outputs/stories", item.text())
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.text_story_view.setText(f.read())
        except Exception as e:
            self.text_story_view.setText(f"Ошибка загрузки: {e}")

    def start_recording(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.text_live_log.clear()

        session_id = self.session_manager.start_new_session()
        self.text_live_log.append(f"--- Начало сессии: {session_id} ---")
        self.tabs.setCurrentWidget(self.tab_live)

        self.capture_worker = CaptureWorker(self.session_manager)
        self.capture_worker.new_event.connect(self.on_new_event)
        self.capture_worker.status_changed.connect(self.status_bar.showMessage)
        self.capture_worker.start()

    def stop_recording(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if self.capture_worker:
            self.capture_worker.stop()
            self.capture_worker.wait()

        self.text_live_log.append("--- Запись остановлена ---")
        self.load_sessions()

    @Slot(str, str)
    def on_new_event(self, timestamp, text):
        time_str = timestamp.split("T")[-1][:8]
        self.text_live_log.append(f"[{time_str}] {text}")

    def open_settings(self):
        dlg = SettingsDialog(self.config_manager, self)
        dlg.exec()

    def start_generation(self):
        selected = self.list_sessions.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сессию для генерации")
            return

        filepath = selected.text().split(" | ")[-1]

        self.generation_worker = GenerationWorker(
            log_path=filepath,
            config_manager=self.config_manager,
            genre=self.config_manager.get("genre", "fantasy")
        )
        self.generation_worker.progress_update.connect(self.status_bar.showMessage)
        self.generation_worker.generation_complete.connect(self.on_generation_complete)
        self.generation_worker.generation_error.connect(self.on_generation_error)
        self.generation_worker.start()

    @Slot(str, str)
    def on_generation_complete(self, path, text):
        self.status_bar.showMessage("Генерация завершена", 5000)
        self.load_stories()
        self.tabs.setCurrentWidget(self.tab_stories)
        # Select the newly created story (it will be the latest file usually)

    @Slot(str)
    def on_generation_error(self, error_msg):
        self.status_bar.showMessage("Ошибка генерации")
        QMessageBox.critical(self, "Ошибка", f"Не удалось сгенерировать историю:\n{error_msg}")

    def closeEvent(self, event):
        # Override to minimize to tray
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Нарративный Архивариус",
            "Приложение свернуто в трей и продолжает работать в фоне.",
            QSystemTrayIcon.Information,
            2000
        )

    def quit_app(self):
        if self.capture_worker and self.capture_worker.is_running:
            self.capture_worker.stop()
            self.capture_worker.wait()
        if self.generation_worker and self.generation_worker.isRunning():
            self.generation_worker.quit()
            self.generation_worker.wait()
        QApplication.quit()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # QSS Styling (Dark Theme)
    app.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; color: #ffffff; }
        QWidget { background-color: #1e1e1e; color: #ffffff; }
        QPushButton { background-color: #333333; border: 1px solid #555555; padding: 5px; border-radius: 3px; }
        QPushButton:hover { background-color: #444444; }
        QPushButton:disabled { color: #777777; }
        QTextEdit, QListWidget { background-color: #252526; border: 1px solid #333333; }
        QTabBar::tab { background: #333333; padding: 8px; border: 1px solid #1e1e1e; }
        QTabBar::tab:selected { background: #1e1e1e; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
