import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor

class SessionEditorDialog(QDialog):
    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.data = None
        self.is_modified = False

        self.setWindowTitle("Редактирование сессии")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Настройка таблицы
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Время", "Текст транскрипции"])

        # Настройка столбцов: время - фиксированный, текст - растягивается
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)

        self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self.save_changes)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        self.load_data()

    def load_data(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            events = self.data.get('events', [])
            self.table.blockSignals(True) # Отключаем сигналы, чтобы не триггерить itemChanged при загрузке
            self.table.setRowCount(len(events))

            for i, event in enumerate(events):
                timestamp = event.get('timestamp', '')
                # Парсим время для красивого отображения (только HH:MM:SS)
                time_str = timestamp.split('T')[-1][:8] if 'T' in timestamp else timestamp

                item_time = QTableWidgetItem(time_str)
                item_time.setFlags(item_time.flags() & ~Qt.ItemIsEditable) # Read-only
                item_time.setForeground(QBrush(QColor(128, 128, 128))) # Серый цвет
                # Сохраняем оригинальный timestamp в данных ячейки, чтобы не потерять
                item_time.setData(Qt.UserRole, timestamp)

                item_text = QTableWidgetItem(event.get('text', ''))

                self.table.setItem(i, 0, item_time)
                self.table.setItem(i, 1, item_text)

            self.table.blockSignals(False)
            self.is_modified = False

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл сессии:\n{e}")
            self.reject()

    def on_item_changed(self, item):
        if item.column() == 1: # Изменился текст
            self.is_modified = True

    def save_changes(self):
        if not self.data:
            return False

        events = self.data.get('events', [])

        # Проверка на пустоту (валидация)
        all_empty = True

        for i in range(self.table.rowCount()):
            text_item = self.table.item(i, 1)
            text = text_item.text().strip() if text_item else ""
            if text:
                all_empty = False

            if i < len(events):
                events[i]['text'] = text

        if all_empty and len(events) > 0:
            reply = QMessageBox.question(
                self,
                "Предупреждение",
                "Все строки транскрипции пусты. Вы уверены, что хотите сохранить пустую сессию?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            self.is_modified = False
            QMessageBox.information(self, "Успех", "Изменения успешно сохранены.")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл сессии:\n{e}")
            return False

    def closeEvent(self, event):
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "Есть несохраненные изменения. Сохранить перед закрытием?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                if self.save_changes():
                    event.accept()
                else:
                    event.ignore() # Если не удалось сохранить, не закрываем
            elif reply == QMessageBox.No:
                event.accept()
            else: # Cancel
                event.ignore()
        else:
            event.accept()
