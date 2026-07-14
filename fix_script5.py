with open("src/gui/main_window.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace QSlider,
content = content.replace("QComboBox, QSlider, QCheckBox,", "QComboBox, QCheckBox,")

# Replace QTimer,
content = content.replace("Qt, Slot, QTimer, Signal", "Qt, Slot, Signal")

# Replace QIcon,
content = content.replace("QIcon, QAction", "QAction")

# Remove duplicate on_provider_changed (it's exactly this string)
duplicate_on_provider_changed = """    def on_provider_changed(self, provider):
        is_lm_studio = (provider == "LM Studio")

        self.url_label.setVisible(is_lm_studio)
        self.url_input.setVisible(is_lm_studio)

        self.groq_token_label.setVisible(not is_lm_studio)
        self.groq_token_input.setVisible(not is_lm_studio)
        self.groq_model_label.setVisible(not is_lm_studio)
        self.groq_model_input.setVisible(not is_lm_studio)
        self.btn_check_groq.setVisible(not is_lm_studio)

"""
# Find the first occurrence and the second occurrence
parts = content.split(duplicate_on_provider_changed)
if len(parts) == 3:
    # Remove the second occurrence
    content = parts[0] + duplicate_on_provider_changed + parts[1] + parts[2]

duplicate_save_settings = """    def save_settings(self):
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
        config["enable_hotkey"] = self.enable_hotkey_cb.isChecked()
        config["hotkey_combo"] = self.hotkey_combo_input.text()

        self.config_manager.save_config(config)
        self.accept()

"""

parts2 = content.split(duplicate_save_settings)
if len(parts2) == 2: # the first one has tesseract logic, the second one doesn't! Let's just find and replace the second one
    content = content.replace(duplicate_save_settings, "")


with open("src/gui/main_window.py", "w", encoding="utf-8") as f:
    f.write(content)
