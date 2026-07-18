from PySide6.QtWidgets import (
    QGroupBox,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QTextEdit, QListWidget, QLabel, QStatusBar, QMessageBox,
    QSystemTrayIcon, QMenu, QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox,
    QApplication, QListWidgetItem, QSlider
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QStyle
import os
import threading
import time
import keyboard

from src.gui.workers import CaptureWorker, GenerationWorker
from src.session_manager import SessionManager
from src.config_manager import ConfigManager
from src.utils.path_utils import get_path

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        # --- Common API Settings ---
        self.api_group = QGroupBox("Настройка API-ключей")
        api_layout = QFormLayout()

        self.groq_token_input = QLineEdit(self.config_manager.get("groq_token", ""))
        self.groq_token_input.setEchoMode(QLineEdit.Password)

        self.btn_check_groq = QPushButton("Проверить доступные мне модели")
        self.btn_check_groq.clicked.connect(self.check_groq_models)

        groq_api_layout = QHBoxLayout()
        groq_api_layout.addWidget(self.groq_token_input)
        groq_api_layout.addWidget(self.btn_check_groq)

        api_layout.addRow("Groq Token:", groq_api_layout)
        self.api_group.setLayout(api_layout)
        main_layout.addWidget(self.api_group)

        # --- LLM Provider Settings (for text generation) ---
        llm_group = QGroupBox("Генерация Истории (ИИ)")
        llm_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Локально (LM Studio)", "Облако (Groq)"])

        # Миграция старых значений конфига
        current_llm_provider = self.config_manager.get("llm_provider", "Локально (LM Studio)")
        if current_llm_provider == "LM Studio":
            current_llm_provider = "Локально (LM Studio)"
        elif current_llm_provider == "Groq":
            current_llm_provider = "Облако (Groq)"

        self.provider_combo.setCurrentText(current_llm_provider)
        self.provider_combo.currentTextChanged.connect(self.update_visibility)
        llm_layout.addRow("Провайдер LLM:", self.provider_combo)

        self.url_input = QLineEdit(self.config_manager.get("api_url"))
        self.url_label = QLabel("LM Studio API URL:")
        llm_layout.addRow(self.url_label, self.url_input)

        self.groq_model_input = QLineEdit(self.config_manager.get("groq_model", "llama-3.1-8b-instant"))
        self.groq_model_label = QLabel("Groq Model:")
        llm_layout.addRow(self.groq_model_label, self.groq_model_input)

        self.genre_combo = QComboBox()
        self.genre_combo.addItems(["fantasy", "cyberpunk", "realism", "horror"])
        self.genre_combo.setCurrentText(self.config_manager.get("genre", "fantasy"))
        llm_layout.addRow("Жанр по умолчанию:", self.genre_combo)

        llm_group.setLayout(llm_layout)
        main_layout.addWidget(llm_group)

        # --- Audio Recognition Settings ---
        audio_group = QGroupBox("Распознавание Аудио")
        audio_layout = QFormLayout()

        self.audio_provider_combo = QComboBox()
        self.audio_provider_combo.addItems(["Облако (Groq API)", "Локально (Встроенный движок Faster-Whisper)"])

        # Миграция старых значений конфига
        current_audio_provider = self.config_manager.get("audio_provider", "Облако (Groq API)")
        if current_audio_provider in ["Groq API", "LM Studio (Custom URL)", "Облачный (Groq API)"]:
            current_audio_provider = "Облако (Groq API)"
        elif current_audio_provider in ["Local Whisper (CPU/GPU)", "Локальный (Встроенный движок)"]:
            current_audio_provider = "Локально (Встроенный движок Faster-Whisper)"

        self.audio_provider_combo.setCurrentText(current_audio_provider)
        self.audio_provider_combo.currentTextChanged.connect(self.update_visibility)
        audio_layout.addRow("Источник (Provider):", self.audio_provider_combo)

        self.audio_url_input = QLineEdit(self.config_manager.get("audio_api_url", "https://api.groq.com/openai/v1/audio/transcriptions"))
        self.audio_url_input.setToolTip("Используется только для сторонних OpenAI-совместимых серверов. По умолчанию скрыто/неактивно")
        self.audio_url_label = QLabel("Audio API URL:")
        audio_layout.addRow(self.audio_url_label, self.audio_url_input)

        self.local_model_combo = QComboBox()
        self.local_model_combo.addItems(["small", "medium", "large-v3-turbo"])

        current_model = self.config_manager.get("local_whisper_model", "large-v3-turbo")
        if current_model not in ["small", "medium", "large-v3-turbo"]:
            current_model = "large-v3-turbo"

        self.local_model_combo.setCurrentText(current_model)
        self.local_model_label = QLabel("Размер модели:")
        audio_layout.addRow(self.local_model_label, self.local_model_combo)

        self.whisper_device_combo = QComboBox()
        self.whisper_device_combo.addItems(["auto", "gpu", "cpu"])
        self.whisper_device_combo.setItemText(0, "Авто (Пытаться GPU, иначе CPU)")
        self.whisper_device_combo.setItemText(1, "GPU (CUDA)")
        self.whisper_device_combo.setItemText(2, "CPU")
        current_device = self.config_manager.get("whisper_device", "auto")
        if current_device == "auto":
            self.whisper_device_combo.setCurrentIndex(0)
        elif current_device == "gpu":
            self.whisper_device_combo.setCurrentIndex(1)
        else:
            self.whisper_device_combo.setCurrentIndex(2)

        self.whisper_device_label = QLabel("Устройство (CPU/GPU):")
        audio_layout.addRow(self.whisper_device_label, self.whisper_device_combo)

        self.whisper_device_combo.currentTextChanged.connect(self.on_device_changed)

        self.local_model_hint = QLabel("")
        self.local_model_hint.setStyleSheet("color: #aaaaaa; font-style: italic; font-size: 11px;")
        self.local_model_hint.setWordWrap(True)

        self.btn_open_cache = QPushButton("Открыть папку с моделями")
        self.btn_open_cache.clicked.connect(self.open_huggingface_cache)

        local_model_bottom_layout = QHBoxLayout()
        local_model_bottom_layout.addWidget(self.local_model_hint)
        local_model_bottom_layout.addWidget(self.btn_open_cache)

        # Use an empty string for the label side to push layout to the right
        audio_layout.addRow("", local_model_bottom_layout)

        self.local_model_combo.currentTextChanged.connect(self.update_local_model_hint)
        self.update_local_model_hint(self.local_model_combo.currentText())

        # Вызовем разок для первоначальной настройки видимости
        self.update_visibility()

        # Volume threshold slider
        self.min_volume_slider = QSlider(Qt.Horizontal)
        self.min_volume_slider.setRange(-60, 0)
        self.min_volume_slider.setSingleStep(1)
        self.min_volume_slider.setValue(self.config_manager.get("min_volume_db", -25))
        self.min_volume_slider.setToolTip("Порог чувствительности. Чем ближе к -60 дБ, тем тише звуки слышит программа (чувствительнее). Рекомендуется от -25 до -35 дБ")

        self.min_volume_label = QLabel(f"{self.min_volume_slider.value()} dB")
        self.min_volume_label.setToolTip("Порог чувствительности. Чем ближе к -60 дБ, тем тише звуки слышит программа (чувствительнее). Рекомендуется от -25 до -35 дБ")
        self.min_volume_slider.valueChanged.connect(lambda v: self.min_volume_label.setText(f"{v} dB"))

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.min_volume_slider)
        volume_layout.addWidget(self.min_volume_label)

        audio_layout.addRow("Минимальная громкость:", volume_layout)

        audio_group.setLayout(audio_layout)
        main_layout.addWidget(audio_group)

        # --- Hotkey Settings ---
        hotkey_group = QGroupBox("Глобальные Горячие Клавиши")
        hotkey_layout = QFormLayout()

        self.enable_hotkey_cb = QCheckBox()
        self.enable_hotkey_cb.setChecked(self.config_manager.get("enable_hotkey", True))
        hotkey_layout.addRow("Включить хоткей (Старт/Стоп):", self.enable_hotkey_cb)

        self.hotkey_combo_input = QLineEdit(self.config_manager.get("hotkey_combo", "ctrl+shift+f11"))
        hotkey_layout.addRow("Комбинация клавиш:", self.hotkey_combo_input)

        hotkey_group.setLayout(hotkey_layout)
        main_layout.addWidget(hotkey_group)

        # --- Screenshot Settings ---
        scr_group = QGroupBox("Скриншоты")
        scr_layout = QFormLayout()

        self.save_screenshots_cb = QCheckBox()
        self.save_screenshots_cb.setChecked(self.config_manager.get("save_screenshots", True))
        scr_layout.addRow("Сохранять скриншоты:", self.save_screenshots_cb)

        self.screenshots_path_input = QLineEdit(self.config_manager.get("screenshots_path", "outputs/screenshots"))
        scr_layout.addRow("Путь к скриншотам:", self.screenshots_path_input)

        scr_group.setLayout(scr_layout)
        main_layout.addWidget(scr_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

        # Initial states
        self.update_visibility()

    def open_huggingface_cache(self):
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            import os
            cache_path = os.path.expanduser("~/.cache/huggingface/hub")
            os.makedirs(cache_path, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(cache_path))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку: {e}")

    def on_device_changed(self, text):
        if text == "GPU (CUDA)" or text == "Авто (Пытаться GPU, иначе CPU)":
            # Switch to large-v3-turbo by default when selecting GPU
            self.local_model_combo.setCurrentText("large-v3-turbo")

    def update_local_model_hint(self, model_size):
        hints = {
            "small": "Сбалансированная, требует ~3 ГБ ОЗУ. Рекомендуется для базового распознавания.",
            "medium": "Медленная на CPU, требует ~6 ГБ ОЗУ. Отличная точность текста.",
            "large-v3-turbo": "Идеальный баланс феноменальной точности русского языка и высокой скорости (лучший выбор для GPU)."
        }
        self.local_model_hint.setText(hints.get(model_size, ""))

    def update_visibility(self, *args):
        llm_provider = self.provider_combo.currentText()
        audio_provider = self.audio_provider_combo.currentText()

        # Показываем блок с токеном, если выбран Groq хотя бы в одном из мест
        show_api_group = (llm_provider == "Облако (Groq)") or (audio_provider == "Облако (Groq API)")
        self.api_group.setVisible(show_api_group)

        # Специфично для LLM
        is_lm_studio = (llm_provider == "Локально (LM Studio)")
        self.url_label.setVisible(is_lm_studio)
        self.url_input.setVisible(is_lm_studio)

        self.groq_model_label.setVisible(not is_lm_studio)
        self.groq_model_input.setVisible(not is_lm_studio)

        # Специфично для Аудио
        is_local_audio = (audio_provider == "Локально (Встроенный движок Faster-Whisper)")

        self.audio_url_label.setVisible(not is_local_audio)
        self.audio_url_input.setVisible(not is_local_audio)

        self.local_model_label.setVisible(is_local_audio)
        self.local_model_combo.setVisible(is_local_audio)
        self.whisper_device_label.setVisible(is_local_audio)
        self.whisper_device_combo.setVisible(is_local_audio)
        self.local_model_hint.setVisible(is_local_audio)
        self.btn_open_cache.setVisible(is_local_audio)

    def save_settings(self):
        config = self.config_manager.config
        config["llm_provider"] = self.provider_combo.currentText()
        config["api_url"] = self.url_input.text()
        config["groq_token"] = self.groq_token_input.text()
        config["groq_model"] = self.groq_model_input.text()
        config["genre"] = self.genre_combo.currentText()
        config["save_screenshots"] = self.save_screenshots_cb.isChecked()
        config["screenshots_path"] = self.screenshots_path_input.text()
        config["audio_provider"] = self.audio_provider_combo.currentText()
        config["audio_api_url"] = self.audio_url_input.text()
        config["local_whisper_model"] = self.local_model_combo.currentText()

        idx = self.whisper_device_combo.currentIndex()
        if idx == 0:
            config["whisper_device"] = "auto"
        elif idx == 1:
            config["whisper_device"] = "gpu"
        else:
            config["whisper_device"] = "cpu"

        config["enable_hotkey"] = self.enable_hotkey_cb.isChecked()
        config["hotkey_combo"] = self.hotkey_combo_input.text()
        config["min_volume_db"] = self.min_volume_slider.value()

        # Remove old Tesseract path if it exists
        if "tesseract_path" in config:
            del config["tesseract_path"]

        self.config_manager.save_config(config)
        self.accept()

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

def _play_start_sound():
    try:
        import winsound
        winsound.Beep(1000, 150)
    except Exception:
        pass

def _play_stop_sound():
    try:
        import winsound
        winsound.Beep(800, 150)
        time.sleep(0.05)
        winsound.Beep(800, 150)
    except Exception:
        pass


class MainWindow(QMainWindow):
    hotkey_triggered = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Нарративный Архивариус (Lore Keeper)")
        self.resize(800, 600)

        self.config_manager = ConfigManager()
        self.session_manager = SessionManager()
        self.capture_worker = None
        self.generation_worker = None

        self.hotkey_hook = None
        self.hotkey_triggered.connect(self.toggle_recording)

        self.setup_ui()
        self.setup_tray()
        self.load_sessions()
        self.setup_hotkey()

    def setup_hotkey(self):
        if self.hotkey_hook is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_hook)
            except Exception:
                pass
            self.hotkey_hook = None

        if self.config_manager.get("enable_hotkey", True):
            combo = self.config_manager.get("hotkey_combo", "ctrl+shift+f11")
            if combo:
                try:
                    self.hotkey_hook = keyboard.add_hotkey(combo, self._on_hotkey_pressed)
                except Exception as e:
                    print(f"Error setting up hotkey: {e}")

    def _on_hotkey_pressed(self):
        self.hotkey_triggered.emit()

    def toggle_recording(self):
        if self.btn_start.isEnabled():
            threading.Thread(target=_play_start_sound, daemon=True).start()
            self.start_recording()
        elif self.btn_stop.isEnabled():
            threading.Thread(target=_play_stop_sound, daemon=True).start()
            self.stop_recording()

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

        self.list_sessions.itemDoubleClicked.connect(self.edit_session)
        self.list_sessions.setContextMenuPolicy(Qt.ActionsContextMenu)

        edit_sess_action = QAction("Редактировать", self)
        edit_sess_action.triggered.connect(self.edit_session)
        self.list_sessions.addAction(edit_sess_action)

        del_sess_action = QAction("Удалить", self)
        del_sess_action.setShortcut("Delete")
        del_sess_action.triggered.connect(self.delete_session)
        self.list_sessions.addAction(del_sess_action)

        btn_generate = QPushButton("Сгенерировать историю из выбранной сессии")
        btn_generate.clicked.connect(self.start_generation)

        btn_edit_session = QPushButton("Редактировать выбранную сессию")
        btn_edit_session.clicked.connect(self.edit_session)

        btn_delete_session = QPushButton("Удалить выбранную сессию")
        btn_delete_session.clicked.connect(self.delete_session)

        sess_buttons_layout = QHBoxLayout()
        sess_buttons_layout.addWidget(btn_generate)
        sess_buttons_layout.addWidget(btn_edit_session)
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

        self.list_stories.setContextMenuPolicy(Qt.ActionsContextMenu)
        del_story_action = QAction("Удалить", self)
        del_story_action.setShortcut("Delete")
        del_story_action.triggered.connect(self.delete_story)
        self.list_stories.addAction(del_story_action)

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
            self.capture_worker.model_load_error.connect(self.on_model_load_error)
            self.capture_worker.transcription_error.connect(self.on_transcription_error)
            self.capture_worker.download_requested.connect(self.on_download_requested)
            self.capture_worker.start()
        except Exception as e:
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить запись:\n{str(e)}")
            return

    @Slot(str)
    def on_model_load_error(self, error_msg):
        # We stop recording immediately since GPU failed and CPU fallback was disabled or user cancelled
        self.stop_recording()

        # Check if the session file is empty (only has the "--- Начало сессии ---" event we appended in UI)
        # Actually session_manager.get_all_sessions() returns the session with event_count
        # We can clean up empty sessions
        try:
            sessions = self.session_manager.get_all_sessions()
            if sessions:
                latest_session = sessions[0] # assuming sorted by descending time
                if latest_session['event_count'] == 0:
                    filepath = latest_session['file']
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(600, self.load_sessions)
        except Exception as e:
            print(f"Error cleaning up empty session on error: {e}")

        if "отменена пользователем" in error_msg:
            # We don't need a critical popup for a user cancellation, just status bar update
            self.status_bar.showMessage("Запись отменена.", 3000)
            return

        if "Missing DLL: cublas64_12.dll" in error_msg or "Missing DLL: cudnn" in error_msg or "nvcuda.dll not found" in error_msg or "GPU initialization failed" in error_msg:
            reply = QMessageBox.question(
                self,
                "Требуются компоненты CUDA",
                "Для работы локального распознавания на видеокартах NVIDIA RTX требуются библиотеки CUDA.\n\nБудет скачан архив размером около 800 МБ.\n\nПродолжить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self.start_cuda_download()
            else:
                QMessageBox.critical(self, "Ошибка инициализации GPU", f"Не удалось инициализировать видеокарту:\n\n{error_msg}\n\nПожалуйста, выберите 'CPU' или 'Auto' в настройках.")
        else:
            QMessageBox.critical(self, "Ошибка инициализации GPU", f"Не удалось инициализировать видеокарту:\n\n{error_msg}\n\nПожалуйста, выберите 'CPU' или 'Auto' в настройках.")

    def start_cuda_download(self):
        from PySide6.QtWidgets import QProgressDialog
        from src.gui.workers import CUDADownloadWorker

        self.progress_dialog = QProgressDialog("Подготовка к скачиванию...", "Отмена", 0, 100, self)
        self.progress_dialog.setWindowTitle("Загрузка CUDA DLL")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        self.cuda_worker = CUDADownloadWorker()
        self.cuda_worker.progress.connect(self.progress_dialog.setValue)
        self.cuda_worker.status_update.connect(self.progress_dialog.setLabelText)
        self.cuda_worker.finished.connect(self.on_cuda_download_finished)

        self.progress_dialog.canceled.connect(self.cuda_worker.terminate)

        self.cuda_worker.start()

    @Slot(bool, str)
    def on_cuda_download_finished(self, success, message):
        self.progress_dialog.close()

        if success:
            QMessageBox.information(self, "Установка завершена", message)
        else:
            QMessageBox.critical(self, "Ошибка установки", message)

    def stop_recording(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if self.capture_worker:
            self.capture_worker.stop()
            # Don't wait synchronously, let the worker's status_changed signal handle UI updates
            # or we can use QTimer to reload sessions slightly later to let flush complete.
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self.load_sessions)

        self.text_live_log.append("--- Запись остановлена ---")

    @Slot(str, str)
    def on_new_event(self, timestamp, text):
        time_str = timestamp.split("T")[-1][:8]
        self.text_live_log.append(f"[{time_str}] {text}")

    @Slot(str, str)
    def on_download_requested(self, title, message):
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if self.capture_worker:
            self.capture_worker.set_download_response(reply == QMessageBox.Yes)

    @Slot(str)
    def on_transcription_error(self, error_msg):
        self.status_bar.showMessage(error_msg, 5000)
        self.text_live_log.append(f"[ОШИБКА] {error_msg}")

    def open_settings(self):
        dlg = SettingsDialog(self.config_manager, self)
        dlg.exec()
        self.setup_hotkey()
        self.on_settings_saved()

    def on_settings_saved(self):
        # Перечитываем конфиг с диска, чтобы убедиться что get() вернет актуальные значения
        self.config_manager.config = self.config_manager.load_config()

        # Применяем громкость "на лету" если идет запись
        new_volume = self.config_manager.get("min_volume_db", -25)
        if self.capture_worker and self.capture_worker.is_running:
            if hasattr(self.capture_worker.trigger_manager, 'min_volume_db'):
                self.capture_worker.trigger_manager.min_volume_db = int(new_volume)
                import logging
                logging.info(f"Динамически обновлена минимальная громкость: {new_volume} dB")
                print(f"Динамически обновлена минимальная громкость: {new_volume} dB")

    def edit_session(self):
        selected = self.list_sessions.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сессию для редактирования")
            return

        filepath = selected.data(Qt.UserRole)
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Внимание", f"Файл сессии не найден:\n{filepath}")
            return

        from src.gui.session_editor_dialog import SessionEditorDialog
        dialog = SessionEditorDialog(filepath, self)
        # We use exec() so it blocks MainWindow while editing
        dialog.exec()

        # Reload sessions to reflect potentially changed event count or file modification time
        self.load_sessions()

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
        provider = self.config_manager.get("llm_provider", "Локально (LM Studio)")

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
        if self.hotkey_hook is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_hook)
            except Exception:
                pass

        if self.capture_worker and self.capture_worker.is_running:
            self.capture_worker.stop()
            # Wait with a short timeout to prevent zombie process/GUI freeze
            if not self.capture_worker.wait(2000):
                print("CaptureWorker did not finish in time, terminating...")
                self.capture_worker.terminate()
                self.capture_worker.wait()

        if self.generation_worker and self.generation_worker.isRunning():
            self.generation_worker.quit()
            if not self.generation_worker.wait(2000):
                self.generation_worker.terminate()
                self.generation_worker.wait()

        QApplication.quit()
