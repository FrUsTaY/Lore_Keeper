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
    "Test 123", # this should fail normally
    "123",
    "только цифры 123"
]

for raw_text in test_strings:
    try:
        model.apply_tts(text=raw_text, speaker="xenia", sample_rate=48000)
        print(f"SUCCESS: '{raw_text}'")
    except Exception as e:
        print(f"FAILED: '{raw_text}' | Error: {type(e).__name__}")
