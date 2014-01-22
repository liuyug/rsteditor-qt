
import os.path

from PyQt4 import QtGui, QtCore
from PyQt4.Qsci import QsciScintilla
from PyQt4.Qsci import QsciLexerPython, QsciLexerHTML, QsciLexerBash
try:
    from rsteditor.scilexerrest import QsciLexerRest
except Exception as err:
    print('Use python lexer', err)
    from rsteditor.scilexerrestructedtext import QsciLexerRest
from rsteditor.util import toUtf8


class FindDialog(QtGui.QDialog):
    findNext = QtCore.pyqtSignal(str, int)
    findPrevious = QtCore.pyqtSignal(str, int)

    def __init__(self, *args, **kwargs):
        super(FindDialog, self).__init__(*args, **kwargs)
        label = QtGui.QLabel(self.tr('&Search for:'))
        self.lineEdit = QtGui.QLineEdit()
        label.setBuddy(self.lineEdit)

        self.wholewordCheckBox = QtGui.QCheckBox(self.tr('Match &whole word'))
        self.caseCheckBox = QtGui.QCheckBox(self.tr('&Match case'))

        self.findButton = QtGui.QPushButton(self.tr("&Find"))
        self.findButton.setDefault(True)
        self.findButton.setEnabled(False)

        closeButton = QtGui.QPushButton(self.tr('&Close'))

        self.lineEdit.textChanged.connect(self.enableFindButton)
        self.findButton.clicked.connect(self.findClicked)
        closeButton.clicked.connect(self.close)

        topLeftLayout = QtGui.QHBoxLayout()
        topLeftLayout.addWidget(label)
        topLeftLayout.addWidget(self.lineEdit)

        leftLayout = QtGui.QVBoxLayout()
        leftLayout.addLayout(topLeftLayout)
        leftLayout.addWidget(self.caseCheckBox)
        leftLayout.addWidget(self.wholewordCheckBox)

        rightLayout = QtGui.QVBoxLayout()
        rightLayout.addWidget(self.findButton)
        rightLayout.addWidget(closeButton)
        rightLayout.addStretch()

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.addLayout(leftLayout)
        mainLayout.addLayout(rightLayout)
        self.setLayout(mainLayout)

        self.setWindowTitle(self.tr("Find"))
        self.setFixedHeight(self.sizeHint().height())

    def enableFindButton(self, text):
        self.findButton.setEnabled(not text.isEmpty())

    def findClicked(self):
        self.close()

    def getFindText(self):
        return self.lineEdit.text()

    def isCaseSensitive(self):
        return self.caseCheckBox.isChecked()

    def isWholeWord(self):
        return self.caseCheckBox.isChecked()


class Editor(QsciScintilla):
    """
    Scintilla Offical Document: http://www.scintilla.org/ScintillaDoc.html
    """
    lineInputed = QtCore.pyqtSignal()
    enable_lexer = True
    filename = None
    input_count = 0
    find_text = None
    find_forward = True
    lexer = None

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginWidth(0, 30)
        self.setMarginWidth(1, 5)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setEdgeMode(QsciScintilla.EdgeLine)
        self.setEdgeColumn(78)
        self.setWrapMode(QsciScintilla.WrapCharacter)
        self.setUtf8(True)
        self.findDialog = FindDialog(self)
        self.copy_available = False
        self.copyAvailable.connect(self.setCopyAvailable)

    def inputMethodEvent(self, event):
        super(Editor, self).inputMethodEvent(event)
        commit_text = toUtf8(event.commitString())
        if commit_text:
            self.input_count += len(commit_text)
        if self.input_count > 5:
            self.lineInputed.emit()
            self.input_count = 0
        return

    def keyPressEvent(self, event):
        super(Editor, self).keyPressEvent(event)
        input_text = toUtf8(event.text())
        if (input_text or
            (event.key() == QtCore.Qt.Key_Enter or
             event.key() == QtCore.Qt.Key_Return)):
            self.input_count += 1
        if (self.input_count > 5 or
            (event.key() == QtCore.Qt.Key_Enter or
             event.key() == QtCore.Qt.Key_Return)):
            self.lineInputed.emit()
            self.input_count = 0
        return

    def contextMenuEvent(self, event):
        if event.reason() == event.Mouse:
            super(Editor, self).contextMenuEvent(event)

    def setCopyAvailable(self, yes):
        self.copy_available = yes

    def isCopyAvailable(self):
        return self.copy_available

    def isPasteAvailable(self):
        """ always return 1 in GTK+ """
        result = self.SendScintilla(QsciScintilla.SCI_CANPASTE)
        return True if result > 0 else False

    def getHScrollValue(self):
        pos = self.horizontalScrollBar().value()
        return pos

    def getVScrollValue(self):
        pos = self.verticalScrollBar().value()
        return pos

    def getVScrollMaximum(self):
        return self.verticalScrollBar().maximum()

    def getFileName(self):
        return self.filename

    def setFileName(self, path):
        """
        set filename and enable lexer
        """
        self.filename = path
        self.setStyle(self.filename)

    def enableLexer(self, enable=True):
        self.enable_lexer = enable

    def getValue(self):
        """ get all text """
        return self.text()

    def setValue(self, text):
        """
        set utf8 text
        modified state is false
        """
        self.setText(toUtf8(text))
        self.setCursorPosition(0, 0)
        self.setModified(False)

    def readFile(self, filename):
        with open(filename) as f:
            text = f.read()
            self.setValue(text)
            self.setFileName(filename)
            return True
        return False

    def writeFile(self, filename=None):
        text = toUtf8(self.getValue())
        if filename is None:
            filename = self.getFileName()
        else:
            self.setFileName(filename)
        if filename:
            with open(filename, 'wb') as f:
                f.write(text.encode('utf-8'))
                self.setModified(False)
                return True
        return False

    def emptyFile(self):
        self.clear()
        self.setFileName(None)
        self.setModified(False)

    def delete(self):
        self.removeSelectedText()

    def find(self):
        self.findDialog.exec_()
        self.find_text = self.findDialog.getFindText()
        bfind = self.findFirst(
            self.find_text,
            False,  # re
            self.findDialog.isCaseSensitive(),  # cs
            self.findDialog.isWholeWord(),   # wo
            True,   # wrap
            True,   # forward
        )
        if not bfind:
            QtGui.QMessageBox.information(
                self,
                self.tr('Find'),
                self.tr('Not found "%s"' % self.find_text),
            )
        return

    def findNext(self):
        line, index = self.getCursorPosition()
        bfind = self.findFirst(
            self.find_text,
            False,  # re
            self.findDialog.isCaseSensitive(),  # cs
            self.findDialog.isWholeWord(),   # wo
            True,   # wrap
            True,   # forward
            line, index
        )
        if not bfind:
            QtGui.QMessageBox.information(
                self,
                self.tr('Find'),
                self.tr('Not found "%s"' % self.find_text),
            )
        return

    def findPrevious(self):
        line, index = self.getCursorPosition()
        index -= len(self.find_text)
        bfind = self.findFirst(
            self.find_text,
            False,  # re
            self.findDialog.isCaseSensitive(),  # cs
            self.findDialog.isWholeWord(),   # wo
            True,   # wrap
            False,   # forward
            line, index
        )
        if not bfind:
            QtGui.QMessageBox.information(
                self,
                self.tr('Find'),
                self.tr('Not found "%s"' % self.find_text),
            )
        return

    def setStyle(self, filename):
        lexer = None
        if filename and self.enable_lexer:
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.html', '.htm']:
                lexer = QsciLexerHTML(self)
            elif ext in ['.py']:
                lexer = QsciLexerPython(self)
            elif ext in ['.sh']:
                lexer = QsciLexerBash(self)
            elif ext in ['.rst', '.rest']:
                lexer = QsciLexerRest(self)
        self.lexer = lexer
        if lexer:
            if not isinstance(lexer, QsciLexerRest):
                lexer.setFont(QtGui.QFont('Monospace', 12))
            self.setLexer(lexer)
        else:
            self.setLexer(None)
            self.setFont(QtGui.QFont('Monospace', 12))
        return


class CodeViewer(Editor):
    """ code viewer, readonly """
    def __init__(self, *args, **kwargs):
        super(CodeViewer, self).__init__(*args, **kwargs)
        self.setReadOnly(True)

    def setValue(self, text):
        """ set all readonly text """
        self.setReadOnly(False)
        super(CodeViewer, self).setValue(text)
        self.setReadOnly(True)
        self.setStyle('unknown.html')
