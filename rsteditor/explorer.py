
import os
import os.path
import sys
import shutil
import logging
from unicodedata import east_asian_width
from functools import partial

from PyQt5 import QtCore, QtWidgets

from rsteditor.util import toUtf8

logger = logging.getLogger(__name__)


class Explorer(QtWidgets.QTreeWidget):
    fileLoaded = QtCore.pyqtSignal('QString')
    pathLoaded = QtCore.pyqtSignal('QString')
    fileDeleted = QtCore.pyqtSignal('QString')
    fileRenamed = QtCore.pyqtSignal('QString', 'QString')
    fileNew = QtCore.pyqtSignal()

    def __init__(self, parent, style=None):
        super(Explorer, self).__init__(parent)
        self.header().close()
        self.root_path = None
        self.root_item = None
        self.padding_right = 32
        # QStyle, such as QtWidgets.QStyleFactory.create('windows')
        self.qstyle = style
        # QT BUG, must keep reference or crash
        self.iconProvider = QtWidgets.QFileIconProvider()

        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.itemActivated.connect(self.onItemActivated)
        self.pathLoaded.connect(self.onPathLoaded)
        # popup menu
        newAction = QtWidgets.QAction(self.tr('&New'), self)
        newAction.triggered.connect(self.onNewFile)
        newdirectoryAction = QtWidgets.QAction(self.tr('New &directory'), self)
        newdirectoryAction.triggered.connect(self.onNewDirectory)
        self.renameAction = QtWidgets.QAction(self.tr('&Rename...'), self)
        self.renameAction.triggered.connect(self.onRename)
        self.deleteAction = QtWidgets.QAction(self.tr('Delete'), self)
        self.deleteAction.triggered.connect(self.onDelete)
        refreshAction = QtWidgets.QAction(self.tr('Refresh'), self)
        refreshAction.triggered.connect(self.onRefresh)
        drivers_path = self.getDrivesPath()
        self.driveGroup = QtWidgets.QActionGroup(self)
        for drive_path in drivers_path:
            act = QtWidgets.QAction(drive_path,
                                self,
                                checkable=True)
            act.triggered.connect(partial(self.onDriveChanged, drive_path))
            self.driveGroup.addAction(act)
        self.popupMenu = QtWidgets.QMenu(self)
        self.popupMenu.addAction(newAction)
        self.popupMenu.addAction(newdirectoryAction)
        self.popupMenu.addSeparator()
        self.popupMenu.addAction(self.renameAction)
        self.popupMenu.addAction(self.deleteAction)
        self.popupMenu.addSeparator()
        self.popupMenu.addAction(refreshAction)
        self.popupMenu.addSeparator()
        for act in self.driveGroup.actions():
            self.popupMenu.addAction(act)
        # drag & drop
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    def resizeEvent(self, event):
        if self.root_item:
            self.root_item.setText(0, self.getDisplayName(self.root_path))
            self.setColumnWidth(0, self.width() - self.padding_right)
        return

    def contextMenuEvent(self, event):
        if event.reason() == event.Mouse:
            pos = event.globalPos()
            item = self.itemAt(event.pos())
        else:
            pos = None
            item = self.currentItem()
            self.scrollToItem(item)
        if item is None:
            item = self.root_item
            self.scrollToItem(item)
        if pos is None:
            rect = self.visualItemRect(item)
            pos = self.mapToGlobal(rect.center())
        self.renameAction.setEnabled(item != self.root_item)
        self.deleteAction.setEnabled(item != self.root_item)
        self.popupMenu.popup(pos)

    def onItemActivated(self, item, col):
        if col > 0:
            return
        if item == self.root_item:
            new_path = os.path.dirname(self.root_path)
            self.setRootPath(new_path)
        else:
            child_name = toUtf8(item.text(0))
            new_path = os.path.join(self.root_path, child_name)
            if os.path.isdir(new_path):
                self.setRootPath(new_path)
            else:
                self.loadFile(new_path)
        return

    def onPathLoaded(self, path):
        self.setRootPath(path)

    def onNewFile(self):
        self.fileNew.emit()

    def onNewDirectory(self):
        newpath = self.newDirectory()
        if newpath:
            self.appendItem(self.root_item, newpath)

    def onRename(self):
        item = self.currentItem()
        if not item or item == self.root_item:
            return
        filename = toUtf8(item.text(0))
        newname = self.renamePath(filename)
        if newname:
            if os.path.dirname(newname) == self.root_path:
                item.setText(0, os.path.basename(newname))
            else:
                self.root_item.removeChild(item)

    def onDelete(self):
        item = self.currentItem()
        if not item or item == self.root_item:
            return
        filename = toUtf8(item.text(0))
        if self.deletePath(filename):
            self.root_item.removeChild(item)

    def onRefresh(self):
        self.setRootPath(self.root_path, True)

    def onDriveChanged(self, drive, checked):
        self.setRootPath(drive)

    def dragMoveEvent(self, event):
        super(Explorer, self).dragMoveEvent(event)
        if (event.source() == self and
                self.dragDropMode() == QtWidgets.QAbstractItemView.InternalMove):
            item = self.itemAt(event.pos())
            if item is None:
                event.ignore()
            elif item.flags() & QtCore.Qt.ItemIsDropEnabled:
                event.accept()
            else:
                event.ignore()

    def dropEvent(self, event):
        # InternalMove mode will ignore function dropMimeData
        if (event.source() == self and
                (event.dropAction == QtCore.Qt.MoveAction or
                 self.dragDropMode() == QtWidgets.QAbstractItemView.InternalMove)):
            drop_item = self.itemAt(event.pos())
            if drop_item is None:
                return
            if drop_item == self.root_item:
                dest_dir = os.path.dirname(self.root_path)
            else:
                dest_dir = os.path.join(self.root_path, toUtf8(drop_item.text(0)))
            mimeData = event.mimeData()
            if mimeData.hasFormat('application/x-qabstractitemmodeldatalist'):
                bytearray = mimeData.data('application/x-qabstractitemmodeldatalist')
                for drag_item in self.decodeMimeData(bytearray):
                    name = toUtf8(drag_item.text(0))
                    oldpath = os.path.join(self.root_path, name)
                    newpath = os.path.join(dest_dir, name)
                    if self.movePath(oldpath, newpath):
                        self.root_item.removeChild(drag_item)
        else:
            return super(Explorer, self).dropEvent(event)

    def decodeMimeData(self, bytearray):
        data = []
        ds = QtCore.QDataStream(bytearray)
        root_index = self.indexFromItem(self.root_item)
        while not ds.atEnd():
            row = ds.readInt32()
            column = ds.readInt32()
            index = root_index.child(row, column)
            map_items = ds.readInt32()
            for i in range(map_items):
                ds.readInt32()    # QtCore.Qt.ItemDataRole(key)
                value = QtCore.QVariant()
                ds >> value
            item = self.itemFromIndex(index)
            data.append(item)
        return data

    def addRoot(self, name):
        root = QtWidgets.QTreeWidgetItem(self)
        root.setText(0, self.getDisplayName(name))
        root.setIcon(0, self.getFileIcon('/'))
        return root

    def appendItem(self, rootitem, name):
        if not rootitem:
            raise Exception('Add root item firstly!')
        child = QtWidgets.QTreeWidgetItem(rootitem)
        child.setText(0, name)
        child.setIcon(0, self.getFileIcon(name))
        path = os.path.join(self.root_path, name)
        if os.path.isfile(path):
            child.setFlags(child.flags() & ~QtCore.Qt.ItemIsDropEnabled)
        return child

    def setRootPath(self, path, refresh=False):
        """ set exporer root path """
        def pathkey(path):
            if os.path.isdir(os.path.join(self.root_path, path)):
                prefix = '0_'
            else:
                prefix = '1_'
            path = prefix + path
            return path.lower()

        if not os.path.exists(path):
            return
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        if not refresh and path == self.root_path:
            return
        for act in self.driveGroup.actions():
            drive = toUtf8(act.text())
            if drive[:2] == path[:2]:
                act.setChecked(True)
        self.clear()
        self.root_path = os.path.realpath(path)
        os.chdir(path)
        self.root_item = self.addRoot(self.root_path)
        dirs = sorted(os.listdir(self.root_path), key=pathkey)
        for d in dirs:
            if d.startswith('.'):
                continue
            self.appendItem(self.root_item, d)
        self.expandItem(self.root_item)

    def getDisplayName(self, name):
        """ directory display name """
        client_width = self.width() - self.padding_right
        char_width = self.fontMetrics().width(' ')
        disp_char_num = int(client_width / char_width) - 1
        full_char = 'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ'
        w = sum(east_asian_width(x) == 'W' or x in full_char for x in name)
        char_length = len(name) + w
        if (char_length - 3) > disp_char_num:
            display_name = '<<<%s' % name[-disp_char_num + 4:]
        else:
            display_name = name
        return display_name

    def getRootPath(self):
        return self.root_path

    def getFileIcon(self, name, style=None):
        if name == '/':
            if self.qstyle:
                icon = self.qstyle.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
            else:
                icon = self.iconProvider.icon(self.iconProvider.Folder)
        else:
            path = os.path.join(self.root_path, name)
            if os.path.isdir(path):
                if self.qstyle:
                    icon = self.qstyle.standardIcon(QtWidgets.QStyle.SP_DirIcon)
                else:
                    icon = self.iconProvider.icon(self.iconProvider.Folder)
            else:
                icon = self.iconProvider.icon(QtCore.QFileInfo(path))
        return icon

    def loadFile(self, filename):
        """
        set root directory and sent signal to request load file.
        """
        if filename:
            if os.path.exists(filename):
                logger.debug('Loading file: %s', filename)
                self.setRootPath(os.path.dirname(filename))
                self.fileLoaded.emit(filename)
        return

    def deletePath(self, filename):
        path = os.path.join(self.root_path, filename)
        if not os.path.exists(path):
            return False
        ret = QtWidgets.QMessageBox.question(self,
                                             self.tr('Delete'),
                                             self.tr('Do you want to delete "%s"?') % (filename),
                                             QtWidgets.QMessageBox.Yes,
                                             QtWidgets.QMessageBox.No)
        if ret == QtWidgets.QMessageBox.Yes:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                    self.fileDeleted.emit(path)
                return True
            except OSError as err:
                QtWidgets.QMessageBox.critical(self,
                                           self.tr('Error'),
                                           err)
        return False

    def newDirectory(self):
        text, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr('New directory'),
                                                  self.tr('Please input name:'))
        if ok:
            filename = toUtf8(text)
            path = os.path.join(self.root_path, filename)
            if os.path.exists(path):
                QtWidgets.QMessageBox.warning(self,
                                              self.tr('File exists'),
                                              self.tr('File "%s" has existed!') % (filename)
                                              )
            else:
                os.mkdir(path)
                return filename
        return

    def renamePath(self, filename):
        path = os.path.join(self.root_path, filename)
        if not os.path.exists(path):
            return
        text, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr('Rename'),
                                                  self.tr('Please input new name:'),
                                                  QtWidgets.QLineEdit.Normal,
                                                  filename)
        if ok:
            newname = toUtf8(text)
            newpath = os.path.abspath(os.path.join(self.root_path, newname))
            return self.movePath(path, newpath)
        return

    def movePath(self, src, dest):
        if os.path.exists(dest):
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('File exists'),
                self.tr('File "%s" has existed!') % (os.path.basename(dest)),
            )
            return
        try:
            os.rename(src, dest)
        except OSError as err:
            QtWidgets.QMessageBox.critical(
                self,
                self.tr('Error'),
                err,
            )
            return
        if os.path.isfile(dest):
            self.fileRenamed.emit(src, dest)
        return dest

    def getDrivesPath(self):
        if sys.platform != 'win32':
            return []
        drivers = []
        for drive in toUtf8('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
            path = '%s:\\' % drive
            if os.path.exists(path):
                drivers.append(path)
        return drivers
