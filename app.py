import sys
from importlib import import_module

if sys.platform == "darwin":
    MainWindow = import_module("ui.macos_window").MacMainWindow
else:
    MainWindow = import_module("ui.main_window").MainWindow


def main() -> int:
    window = MainWindow()
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
