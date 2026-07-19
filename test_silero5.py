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

text = "Привет мир! 123... А-Б-В. Ё. ё. Только цифры 123. \n\n Test English! #$@!"

import re
clean_text = re.sub(r'[#*_`~>\[\]\(\)\-\=]', '', text)
clean_text = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?:;"\'-]', '', clean_text)
clean_text = re.sub(r'\n+', ' ', clean_text)
clean_text = clean_text.strip()

sentences = re.split(r'(?<=[.!?]) +', clean_text)
audio_chunks = []

for sent in sentences:
    sent = sent.strip()
    if not sent:
        continue
    if not re.search(r'[а-яА-ЯёЁ]', sent):
        print(f"SKIPPED (no cyrillic): '{sent}'")
        continue
    try:
        model.apply_tts(text=sent, speaker="xenia", sample_rate=48000)
        print(f"SUCCESS: '{sent}'")
        audio_chunks.append("audio")
    except Exception as e:
        print(f"FAILED: '{sent}' | Error: {type(e).__name__}")

if not audio_chunks:
    print("FINISHED: NO AUDIO PRODUCED")
else:
    print("FINISHED: AUDIO PRODUCED")
