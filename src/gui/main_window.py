from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QTextEdit, QListWidget, QLabel, QStatusBar, QMessageBox,
    QSystemTrayIcon, QMenu, QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QCheckBox,
    QApplication, QListWidgetItem
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QStyle
import os

from src.gui.workers import CaptureWorker, GenerationWorker
from src.session_manager import SessionManager
from src.config_manager import ConfigManager
from src.utils.path_utils import get_path

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["LM Studio", "Groq"])
        self.provider_combo.setCurrentText(self.config_manager.get("llm_provider", "LM Studio"))
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        layout.addRow("Провайдер LLM:", self.provider_combo)

        self.url_input = QLineEdit(self.config_manager.get("api_url"))
        self.url_label = QLabel("LM Studio API URL:")
        layout.addRow(self.url_label, self.url_input)

        self.groq_token_input = QLineEdit(self.config_manager.get("groq_token", ""))
        self.groq_token_input.setEchoMode(QLineEdit.Password)
        self.groq_token_label = QLabel("Groq Token:")
        layout.addRow(self.groq_token_label, self.groq_token_input)

        self.groq_model_input = QLineEdit(self.config_manager.get("groq_model", "llama-3.1-8b-instant"))
        self.groq_model_label = QLabel("Groq Model:")

        # Кнопка для проверки доступных моделей
        self.btn_check_groq = QPushButton("Проверить доступные мне модели")
        self.btn_check_groq.clicked.connect(self.check_groq_models)

        groq_model_layout = QHBoxLayout()
        groq_model_layout.addWidget(self.groq_model_input)
        groq_model_layout.addWidget(self.btn_check_groq)

        layout.addRow(self.groq_model_label, groq_model_layout)

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

    def check_groq_models(self):
        import requests
        token = self.groq_token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите Groq Token перед проверкой моделей.")
            return

        try:
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                models = [model.get("id") for model in data.get("data", [])]
                if models:
                    models_text = "\n".join(models)
                    # Используем QInputDialog с большим текстом, чтобы можно было скопировать
                    text_edit = QTextEdit()
                    text_edit.setReadOnly(True)
                    text_edit.setPlainText(models_text)

                    dialog = QDialog(self)
                    dialog.setWindowTitle("Доступные модели Groq")
                    dialog.resize(300, 400)
                    dlg_layout = QVBoxLayout(dialog)
                    dlg_layout.addWidget(QLabel("Вы можете скопировать название нужной модели:"))
                    dlg_layout.addWidget(text_edit)
                    dialog.exec()
                else:
                    QMessageBox.information(self, "Модели", "Список моделей пуст.")
            else:
                QMessageBox.warning(self, "Ошибка API", f"Код ошибки: {response.status_code}\nПроверьте правильность токена.")
        except Exception as e:
            QMessageBox.critical(self, "Сетевая ошибка", f"Не удалось подключиться к Groq API:\n{e}")

    def on_provider_changed(self, provider):
        is_lm_studio = (provider == "LM Studio")

        self.url_label.setVisible(is_lm_studio)
        self.url_input.setVisible(is_lm_studio)

        self.groq_token_label.setVisible(not is_lm_studio)
        self.groq_token_input.setVisible(not is_lm_studio)
        self.groq_model_label.setVisible(not is_lm_studio)
        self.groq_model_input.setVisible(not is_lm_studio)
        self.btn_check_groq.setVisible(not is_lm_studio)

    def save_settings(self):
        config = self.config_manager.config
        config["llm_provider"] = self.provider_combo.currentText()
        config["api_url"] = self.url_input.text()
        config["groq_token"] = self.groq_token_input.text()
        config["groq_model"] = self.groq_model_input.text()
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

        btn_delete_session = QPushButton("Удалить выбранную сессию")
        btn_delete_session.clicked.connect(self.delete_session)

        sess_buttons_layout = QHBoxLayout()
        sess_buttons_layout.addWidget(btn_generate)
        sess_buttons_layout.addWidget(btn_delete_session)

        sess_layout.addWidget(QLabel("Сохраненные сессии:"))
        sess_layout.addWidget(self.list_sessions)
        sess_layout.addLayout(sess_buttons_layout)
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

        btn_delete_story = QPushButton("Удалить выбранную историю")
        btn_delete_story.clicked.connect(self.delete_story)

        story_list_layout = QVBoxLayout()
        story_list_layout.addWidget(self.list_stories)
        story_list_layout.addWidget(btn_delete_story)

        self.text_story_view = QTextEdit()
        self.text_story_view.setReadOnly(True)

        stories_layout.addLayout(story_list_layout, 1)
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
        show_action.triggered.connect(self.restore_window)
        tray_menu.addAction(show_action)

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about_dialog)
        tray_menu.addAction(about_action)

        quit_action = QAction("Выйти", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        # We start with the tray icon hidden because the main window is visible
        self.tray_icon.hide()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.restore_window()

    def restore_window(self):
        self.showNormal()
        self.activateWindow()
        self.tray_icon.hide()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "О программе",
            "<h3>Нарративный Архивариус (Lore Keeper)</h3>"
            "<p>Это программа для автоматического создания красивых литературных дневников "
            "и историй из ваших игровых сессий.</p>"
            "<p><b>Как это работает:</b><br>"
            "Вы запускаете запись сессии во время игры. Программа автоматически считывает важные "
            "события (например, логи в играх, используя распознавание текста) и сохраняет их в "
            "хронологическом порядке. Когда вы закончите, программа использует искусственный "
            "интеллект, чтобы превратить эти сухие логи в увлекательную историю, которую "
            "можно сохранить и прочитать в библиотеке.</p>"
            "<p>Просто нажмите <b>Старт Записи</b>, играйте в любимую игру, а затем "
            "сгенерируйте свою собственную уникальную историю!</p>"
        )

    def load_sessions(self):
        self.list_sessions.clear()
        sessions = self.session_manager.get_all_sessions()
        for s in sessions:
            item = QListWidgetItem(f"{s['id']} (Событий: {s['event_count']}) | {s['file']}")
            item.setData(Qt.UserRole, s['file'])
            self.list_sessions.addItem(item)

    def load_stories(self):
        self.list_stories.clear()
        stories_dir = get_path("outputs/stories")
        os.makedirs(stories_dir, exist_ok=True)
        for f in os.listdir(stories_dir):
            if f.endswith(".md"):
                self.list_stories.addItem(f)

    def load_story_text(self, item):
        filepath = os.path.join(get_path("outputs/stories"), item.text())
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.text_story_view.setText(f.read())
        except Exception as e:
            self.text_story_view.setText(f"Ошибка загрузки: {e}")

    def delete_story(self):
        selected = self.list_stories.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите историю для удаления")
            return

        filepath = os.path.join(get_path("outputs/stories"), selected.text())

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить эту историю?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.load_stories()
                self.text_story_view.clear()
                self.status_bar.showMessage("История удалена", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить историю:\n{e}")

    def start_recording(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.text_live_log.clear()

        session_id = self.session_manager.start_new_session()
        self.text_live_log.append(f"--- Начало сессии: {session_id} ---")
        self.tabs.setCurrentWidget(self.tab_live)

        try:
            self.capture_worker = CaptureWorker(self.session_manager)
            self.capture_worker.new_event.connect(self.on_new_event)
            self.capture_worker.status_changed.connect(self.status_bar.showMessage)
            self.capture_worker.start()
        except Exception as e:
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить запись:\n{str(e)}")
            return

    def stop_recording(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if self.capture_worker:
            self.capture_worker.stop()

        self.text_live_log.append("--- Запись остановлена ---")
        self.load_sessions()

    @Slot(str, str)
    def on_new_event(self, timestamp, text):
        time_str = timestamp.split("T")[-1][:8]
        self.text_live_log.append(f"[{time_str}] {text}")

    def open_settings(self):
        dlg = SettingsDialog(self.config_manager, self)
        dlg.exec()

    def delete_session(self):
        selected = self.list_sessions.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сессию для удаления")
            return

        filepath = selected.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить эту сессию?\n\nБудет удален только лог файл.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.load_sessions()
                self.status_bar.showMessage("Сессия удалена", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить сессию:\n{e}")

    def start_generation(self):
        selected = self.list_sessions.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сессию для генерации")
            return

        filepath = selected.data(Qt.UserRole)
        provider = self.config_manager.get("llm_provider", "LM Studio")

        self.status_bar.showMessage(f"Обращение к {provider} для генерации истории...")

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
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "Нарративный Архивариус",
            "Приложение свернуто в трей и продолжает работать в фоне.",
            QSystemTrayIcon.Information,
            2000
        )

    def quit_app(self):
        if self.capture_worker and self.capture_worker.is_running:
            self.capture_worker.stop()
        if self.generation_worker and self.generation_worker.isRunning():
            self.generation_worker.quit()
            self.generation_worker.wait()
        QApplication.quit()
