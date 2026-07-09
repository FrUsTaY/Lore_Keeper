import sys
import signal
from src.trigger_manager import TriggerManager

def main():
    manager = TriggerManager()

    def signal_handler(sig, frame):
        print("\nStopping capture...")
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    print("Press Ctrl+C to stop.")

    try:
        manager.start()
    except Exception as e:
        print(f"Error: {e}")
        manager.stop()

if __name__ == "__main__":
    main()
