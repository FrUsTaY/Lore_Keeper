import re

with open('src/gui/main_window.py', 'r') as f:
    code = f.read()

# Replace duplicated start_recording block
old_block = """    def start_recording(self):
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
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить запись:\\n{str(e)}")
            return

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
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить запись:\\n{str(e)}")
            return"""

new_block = """    def start_recording(self):
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
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить запись:\\n{str(e)}")
            return"""

code = code.replace(old_block, new_block)

with open('src/gui/main_window.py', 'w') as f:
    f.write(code)
