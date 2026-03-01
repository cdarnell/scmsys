import time
from polling.loop import run_polling
from config import Settings


def main():
    settings = Settings()
    run_polling(settings)


if __name__ == "__main__":
    main()
