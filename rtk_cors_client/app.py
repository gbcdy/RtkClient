# -*- coding: utf-8 -*-
"""Точка входа модульного приложения RTK CORS Client.

Запуск из корня репозитория:
    python -m rtk_cors_client
"""
import sys


def run():
    """Создаёт QApplication и MainWindow; возвращает код выхода."""
    from PyQt5.QtWidgets import QApplication

    from rtk_cors_client.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec_()


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
