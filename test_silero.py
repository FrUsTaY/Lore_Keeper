import torch
import warnings
warnings.filterwarnings('ignore')

model_path = "models/silero/v4_ru.pt"
try:
    model = torch.package.PackageImporter(model_path).load_pickle("tts_models", "model")
    model.to(torch.device('cpu'))
    print("Model loaded successfully")
except Exception as e:
    print(f"Model load failed: {e}")
    exit(1)

test_strings = [
    "Привет мир",
    "Ведьмак - каменные сердца часть 1.",
    "Привет, как дела?",
    "А-Б-В",
    "Ой...",
    "Ё",
    "ё",
    "Test 123", # this should fail normally
    "123"
]

import re
for raw_text in test_strings:
    clean_text = re.sub(r'[#*_`~>\[\]\(\)\-\=]', '', raw_text)
    clean_text = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?:;"\'-]', '', clean_text)
    clean_text = re.sub(r'\n+', ' ', clean_text)
    clean_text = clean_text.strip()

    try:
        if clean_text:
            model.apply_tts(text=clean_text, speaker="xenia", sample_rate=48000)
            print(f"SUCCESS: '{raw_text}' -> '{clean_text}'")
        else:
            print(f"EMPTY (skipped): '{raw_text}'")
    except Exception as e:
        print(f"FAILED: '{raw_text}' -> '{clean_text}' | Error: {type(e).__name__}")
