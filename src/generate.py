import argparse
import sys
from src.story_generator import StoryGenerator

def main():
    parser = argparse.ArgumentParser(description="Сгенерировать рассказ из лога событий.")
    parser.add_argument("--input", required=True, help="Путь к JSON-логу")
    parser.add_argument("--output", help="Куда сохранить рассказ (опционально)")
    parser.add_argument("--genre", help="Жанр (fantasy, cyberpunk, realism, horror)")
    parser.add_argument("--max-events", type=int, default=100, help="Макс. количество событий")

    args = parser.parse_args()

    generator = StoryGenerator()
    try:
        generator.generate_story_from_log(
            log_path=args.input,
            output_path=args.output,
            genre=args.genre,
            max_events=args.max_events
        )
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
