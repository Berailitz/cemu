import time

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QTextEdit,
    QFrame,
    QDockWidget,
)

from PyQt6.QtGui import(
    QFont,
)


class LogWidget(QDockWidget):
    def __init__(self, parent, *args, **kwargs):
        super(LogWidget, self).__init__("Cemu Logs", parent)
        self.parent = self.parentWidget()
        self.__editor = QTextEdit()
        self.__editor.setFont(QFont('Courier', 11))
        self.__editor.setFrameStyle(QFrame.Shape.Panel | QFrame.Shape.NoFrame)
        self.__editor.setReadOnly(True)
        self.setWidget(self.__editor)
        self.__timestamp_format = "%Y/%m/%d - %H:%M:%S"
        return


    def log(self, msg: str, add_timestamp: bool = True) -> None:
        ts = ""
        if add_timestamp:
            ts = time.strftime(self.__timestamp_format)
        self.__editor.append("{}: {}".format(ts, msg))
        return


    def error(self, msg: str) -> None:
        return self.log("[-] {}".format(msg))


    def warn(self, msg: str) -> None:
        return self.log("[!] {}".format(msg))


    def info(self, msg: str) -> None:
        return self.log("[*] {}".format(msg))


    def ok(self, msg: str) -> None:
        return self.log("[+] {}".format(msg))


    def clear(self) -> None:
        self.__editor.clear()
        return
