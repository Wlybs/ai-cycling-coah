import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.brief_updater import update_brief


def main():
    update_brief(gemini_path=REPO / "GEMINI.md", memory_dir=REPO / "coach_memory")
    print("coach brief updated")


if __name__ == "__main__":
    main()
