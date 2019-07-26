import functools
import tempfile
import os
import sys

from typing import Callable, Dict, List, Tuple, Any

from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt5.QtWidgets import (
    QApplication,
    qApp,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QMessageBox,
    QAction,
    QFileDialog,
    QGridLayout,
    QLabel,
    QWidget,
    QDockWidget,
    QMainWindow
)

from PyQt5.QtGui import(
    QIcon,
)

from PyQt5.QtCore import(
    QSettings,
    QFileInfo
)

from ..utils import (
    list_available_plugins,
    load_plugin,
    assemble,
    disassemble_file
)

from ..emulator import Emulator
from ..shortcuts import Shortcut
from ..arch import (
    Architectures,
    get_architecture_by_name,
    Endianness,
    Syntax
)

from ..const import (
    COMMENT_MARKER,
    PROPERTY_MARKER,
    EXAMPLE_PATH,
    TEMPLATE_PATH,
    HOME,
    TITLE,
    AUTHOR,
    VERSION,
    URL,
    ISSUE_LINK,
)

from .codeeditor import CodeWidget
from .mapping import MemoryMappingWidget
from .emulator import EmulatorWidget
from .log import LogWidget
from .command import CommandWidget
from .registers import RegistersWidget
from .memory import MemoryWidget

from ..settings import Settings


class CEmuWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(CEmuWindow, self).__init__()
        self.settings = Settings()
        self.arch = get_architecture_by_name(self.settings.get("Global", "DefaultArchitecture", "x86_64"))
        self.recentFileActions = []
        self.__plugins = []
        self.archActions = {}
        self.signals = {}
        self.current_file = None
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.shortcuts = Shortcut()

        # prepare the emulator
        self.emulator = Emulator(self)

        # set up the menubar, status and main window
        self.setMainWindowProperty()
        self.setMainWindowMenuBar()

        # set up the dockable items
        self.__regsWidget           = RegistersWidget(self)
        self.__mapWidget            = MemoryMappingWidget(self)
        self.__memWidget            = MemoryWidget(self)
        self.__cmdWidget            = CommandWidget(self)
        self.__emuWidget            = EmulatorWidget(self)
        self.__logWidget            = LogWidget(self)

        # the code editor is the central canvas, the rest are dockable items
        self.__codeWidget           = CodeWidget(self)
        self.setCentralWidget(self.__codeWidget)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.__regsWidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.__mapWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.__memWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.__cmdWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.__emuWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.__logWidget)

        # ... and the extra plugins too
        self.LoadExtraPlugins()


        # show everything
        self.show()
        return


    def LoadExtraPlugins(self) -> int:
        nb_added = 0

        for p in list_available_plugins():
            module = load_plugin(p)
            if not module or not getattr(module, "register"):
                continue

            m = module.register(self)
            if not m:
                continue

            self.__plugins.append(m)
            nb_added += 1
            self.addDockWidget(Qt.RightDockWidgetArea, m)
            self.log("Loaded plugin '{}'".format(p))
        return nb_added


    def setMainWindowProperty(self) -> None:
        width = self.settings.getint("Global", "WindowWidth", 1600)
        heigth = self.settings.getint("Global", "WindowHeigth", 800)
        self.resize(width, heigth)
        self.updateTitle()

        # center the window
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

        # apply the style
        style = self.settings.get("Theme", "QtStyle", "Cleanlooks")
        qApp.setStyle(style)
        return


    def add_menu_item(self, title: str, callback: Callable, description:str=None, shortcut:str=None):
        action = QAction(QIcon(), title, self)
        action.triggered.connect( callback )
        if description:
            action.setStatusTip(description)
        if shortcut:
            action.setShortcut(shortcut)
        return action


    def setMainWindowMenuBar(self):
        statusBar = self.statusBar()
        menubar = self.menuBar()
        maxRecentFiles = self.settings.getint("Global", "MaxRecentFiles")

        # Add File menu bar
        fileMenu = menubar.addMenu("&File")

        loadAsmAction = self.add_menu_item("Load Assembly", self.loadCodeText,
                                           self.shortcuts.description("load_assembly"),
                                           self.shortcuts.shortcut("load_assembly"))

        loadBinAction = self.add_menu_item("Load Binary", self.loadCodeBin,
                                           self.shortcuts.description("load_binary"),
                                           self.shortcuts.shortcut("load_binary"))

        for i in range(maxRecentFiles):
            self.recentFileActions.append(QAction(self, visible=False, triggered=self.openRecentFile))

        clearRecentFilesAction = self.add_menu_item("Clear Recent Files", self.clearRecentFiles,
                                                    "Clear Recent Files", "")

        saveAsmAction = self.add_menu_item("Save Assembly", self.saveCodeText,
                                           self.shortcuts.description("save_as_asm"),
                                           self.shortcuts.shortcut("save_as_asm"))

        saveBinAction = self.add_menu_item ("Save Binary", self.saveCodeBin,
                                            self.shortcuts.description("save_as_binary"),
                                            self.shortcuts.shortcut("save_as_binary"))

        saveCAction = self.add_menu_item("Generate C code", self.saveAsCFile,
                                         self.shortcuts.description("generate_c_file"),
                                         self.shortcuts.shortcut("generate_c_file"))

        saveAsAsmAction = self.add_menu_item("Generate Assembly code", self.saveAsAsmFile,
                                             self.shortcuts.description("generate_asm_file"),
                                             self.shortcuts.shortcut("generate_asm_file"))

        quitAction = self.add_menu_item("Quit", QApplication.quit,
                                        self.shortcuts.shortcut("exit_application"),
                                        self.shortcuts.description("exit_application"))

        fileMenu.addAction(loadAsmAction)
        fileMenu.addAction(loadBinAction)
        fileMenu.addSeparator()

        for i in range(maxRecentFiles):
            fileMenu.addAction(self.recentFileActions[i])
        self.updateRecentFileActions()
        fileMenu.addSeparator()

        fileMenu.addAction(clearRecentFilesAction)
        fileMenu.addSeparator()

        fileMenu.addAction(saveAsmAction)
        fileMenu.addAction(saveBinAction)
        fileMenu.addAction(saveCAction)
        fileMenu.addAction(saveAsAsmAction)
        fileMenu.addSeparator()

        fileMenu.addAction(quitAction)

        # Add Architecture menu bar
        archMenu = menubar.addMenu("&Architecture")
        for abi in sorted(Architectures.keys()):
            archSubMenu = archMenu.addMenu(abi)
            for arch in Architectures[abi]:
                self.archActions[arch.name] = QAction(QIcon(), str(arch), self)
                if arch == self.arch:
                    self.archActions[arch.name].setEnabled(False)
                    self.currentAction = self.archActions[arch.name]

                self.archActions[arch.name].setStatusTip("Switch context to architecture: '%s'" % arch)
                self.archActions[arch.name].triggered.connect( functools.partial(self.updateMode, arch) )
                archSubMenu.addAction(self.archActions[arch.name])

        # Add Help menu bar
        helpMenu = menubar.addMenu("&Help")
        shortcutAction = self.add_menu_item("Shortcuts", self.showShortcutPopup,
                                            self.shortcuts.description("shortcut_popup"),
                                            self.shortcuts.shortcut("shortcut_popup"))

        aboutAction = self.add_menu_item("About", self.about_popup,
                                         self.shortcuts.description("about_popup"))

        helpMenu.addAction(shortcutAction)
        helpMenu.addAction(aboutAction)
        return


    def loadFile(self, fname, data=None):

        if data is None:
            data = open(fname, 'r').read()

        for line in data.splitlines():
            part = line.strip().split()
            if len(part) < 3:
                continue

            if not (part[0] == COMMENT_MARKER and part[1] == PROPERTY_MARKER):
                continue

            if part[2].startswith("arch:"):
                try:
                    arch_from_file = part[2][5:]
                    arch = get_architecture_by_name(arch_from_file)
                    self.updateMode(arch)
                except KeyError:
                    self.__logWidget.editor.append("Unknown architecture '{:s}', discarding...".format(arch_from_file))
                    continue

            if part[2].startswith("endian:"):
                endian_from_file = part[2][7:].lower()
                if endian_from_file not in ("little", "big"):
                    self.__logWidget.editor.append("Incorrect endianness '{:s}', discarding...".format(endian_from_file))
                    continue
                self.arch.endianness = Endianness.LITTLE if endian_from_file == "little" else Endianness.BIG
                self.__logWidget.editor.append("Changed endianness to '{:s}'".format(endian_from_file))

            if part[2].startswith("syntax:"):
                syntax_from_file = part[2][7:].lower()
                if syntax_from_file not in ("att", "intel"):
                    self.__logWidget.editor.append("Incorrect syntax '{:s}', discarding...".format(syntax_from_file))
                    continue
                self.arch.syntax = Syntax.ATT if syntax_from_file=="att" else Syntax.INTEL
                self.__logWidget.editor.append("Changed syntax to '{:s}'".format(syntax_from_file))


        self.__codeWidget.editor.setPlainText(data)
        self.__logWidget.editor.append("Loaded '%s'" % fname)
        self.updateRecentFileActions(fname)
        self.current_file = fname
        self.updateTitle(self.current_file)
        return

    def openRecentFile(self):
        action = self.sender()
        if action:
            self.loadFile(action.data())
        return

    def loadCode(self, title, filter, run_disassembler):
        qFile, _ = QFileDialog.getOpenFileName(self, title, EXAMPLE_PATH, filter + ";;All files (*.*)")

        if not os.access(qFile, os.R_OK):
            return

        if run_disassembler or qFile.endswith(".raw"):
            body = disassemble_file(qFile, self.arch)
            self.loadFile(qFile, data=body)
        else:
            self.loadFile(qFile)
        return


    def loadCodeText(self):
        return self.loadCode("Open Assembly file", "Assembly files (*.asm *.s)", False)


    def loadCodeBin(self):
        return self.loadCode("Open Raw file", "Raw binary files (*.raw)", True)


    def saveCode(self, title, filter, run_assembler):
        qFile, _ = QFileDialog().getSaveFileName(self, title, HOME, filter=filter + ";;All files (*.*)")
        if qFile is None or len(qFile)==0 or qFile=="":
            return

        if run_assembler:
            asm = self.get_code(as_string=True)
            txt, cnt = assemble(asm, self.arch)
            if cnt < 0:
                self.__logWidget.editor.append("Failed to compile: error at line {:d}".format(-cnt))
                return
        else:
            txt = self.get_code(as_string=True)

        with open(qFile, "wb") as f:
            f.write(txt)

        self.__logWidget.editor.append("Saved as '%s'" % qFile)
        return


    def saveCodeText(self):
        return self.saveCode("Save Assembly Pane As", "Assembly files (*.asm *.s)", False)


    def saveCodeBin(self):
        return self.saveCode("Save Raw Binary Pane As", "Raw binary files (*.raw)", True)


    def saveAsCFile(self):
        template = open(os.sep.join([TEMPLATE_PATH, "template.c"]), "rb").read()
        insns = self.__codeWidget.parser.getCleanCodeAsByte(as_string=False)
        title = bytes(self.arch.name, encoding="utf-8")
        sc = b'""\n'
        i = 0
        for insn in insns:
            txt, cnt = assemble(insn, self.arch)
            if cnt < 0:
                self.__logWidget.editor.append("Failed to compile: error at line {:d}".format(-cnt))
                return

            c = b'"' + b''.join([ b'\\x%.2x'%txt[i] for i in range(len(txt)) ]) + b'"'
            c = c.ljust(60, b' ')
            c+= b'// ' + insn + b'\n'
            sc += b'\t' + c
            i += len(txt)

        sc += b'\t""'
        body = template % (title, i, sc)
        fd, fpath = tempfile.mkstemp(suffix=".c")
        os.write(fd, body)
        os.close(fd)
        self.__logWidget.editor.append("Saved as '%s'" % fpath)
        return


    def saveAsAsmFile(self):
        asm_fmt = open( os.sep.join([TEMPLATE_PATH, "template.asm"]), "rb").read()
        txt = self.__codeWidget.parser.getCleanCodeAsByte(as_string=True)
        title = bytes(self.arch.name, encoding="utf-8")
        asm = asm_fmt % (title, b'\n'.join([b"\t%s"%x for x in txt.split(b'\n')]))
        fd, fpath = tempfile.mkstemp(suffix=".asm")
        os.write(fd, asm)
        os.close(fd)
        self.__logWidget.editor.append("Saved as '%s'" % fpath)


    def updateMode(self, arch):
        self.currentAction.setEnabled(True)
        self.arch = arch
        print("Switching to '%s'" % self.arch)
        self.__logWidget.editor.append("Switching to '%s'" % self.arch)
        self.__registerWidget.updateGrid()
        self.archActions[arch.name].setEnabled(False)
        self.currentAction = self.archActions[arch.name]
        self.updateTitle()
        return


    def updateTitle(self, msg=None):
        title = "{} ({})".format(TITLE, self.arch)
        if msg:
            title+=": {}".format(msg)
        self.setWindowTitle(title)
        return


    def showShortcutPopup(self):
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle("CEMU Shortcuts")

        wid = QWidget()
        grid = QGridLayout()
        for j, title in enumerate(["Shortcut", "Description"]):
            lbl = QLabel()
            lbl.setTextFormat(Qt.RichText)
            lbl.setText("<b>{}</b>".format(title))
            grid.addWidget(lbl, 0, j)

        for i, config_item in enumerate(self.shortcuts._config):
            sc, desc = self.shortcuts._config[config_item]
            if not sc:
                continue
            grid.addWidget(QLabel(sc), i+1, 0)
            grid.addWidget(QLabel(desc), i+1, 1)

        wid.setMinimumWidth(800)
        wid.setLayout(grid)
        msgbox.layout().addWidget(wid)
        msgbox.exec_()
        return

    def about_popup(self):
        templ = open(TEMPLATE_PATH + "/about.html", "r").read()
        desc = templ.format(author=AUTHOR, version=VERSION, project_link=URL, issues_link=ISSUE_LINK)
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Information)
        msgbox.setWindowTitle("About CEMU")
        msgbox.setTextFormat(Qt.RichText)
        msgbox.setText(desc)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec_()
        return

    def updateRecentFileActions(self, insert_file=None):
        settings = QSettings('Cemu', 'Recent Files')
        files = settings.value('recentFileList')
        if files is None:
            # if setting doesn't exist, create it
            settings.setValue('recentFileList', [])
            files = settings.value('recentFileList')

        maxRecentFiles = self.settings.getint("Default", "MaxRecentFiles")

        if insert_file:
            if insert_file not in files:
                files.insert(0, insert_file)
            if len(files) > maxRecentFiles:
                files = files[0:maxRecentFiles]

            settings.setValue('recentFileList', files)

        numRecentFiles = min(len(files), maxRecentFiles)

        for i in range(numRecentFiles):
            text = "&%d %s" % (i + 1, self.strippedName(files[i]))
            self.recentFileActions[i].setText(text)
            self.recentFileActions[i].setData(files[i])
            self.recentFileActions[i].setVisible(True)

        for j in range(numRecentFiles, maxRecentFiles):
            self.recentFileActions[j].setVisible(False)
        return

    def strippedName(self, fullFileName) -> str:
        return QFileInfo(fullFileName).fileName()


    def clearRecentFiles(self) -> None:
        settings = QSettings('Cemu', 'Recent Files')
        settings.setValue('recentFileList', [])
        self.updateRecentFileActions()
        return


    def log(self, msg, to_cli=False) -> None:
        """
        Log `msg` into the logging window
        """
        self.__logWidget.log(msg)
        if to_cli:
            print(msg)
        return


    def get_code(self, as_string: bool=False) -> bytearray:
        """
        Return as a bytearray the code from the code editor.
        """
        return self.__codeWidget.parser.getCleanCodeAsByte(as_string)


    def get_registers(self) -> Dict[str, int]:
        """
        Returns the register widget values as a Dict
        """
        return self.__regsWidget.getRegisters()


    def get_memory_layout(self) -> List[ Tuple[str, int, int, str, Any] ]:
        """
        Returns the memory layout as defined by the __mapWidget values as a structured list.
        """
        return self.__mapWidget.maps






