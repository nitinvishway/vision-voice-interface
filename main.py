import logging

import config
from tray_app import TrayApp


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    TrayApp().run()


if __name__ == "__main__":
    main()
