# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go2mapillaryDockWidget
                                 A QGIS plugin
 mapillary filter
                             -------------------
        begin                : 2016-01-21
        git sha              : $Format:%H$
        copyright            : (C) 2016 by enrico ferreguti
        email                : enricofer@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import sys
import datetime

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QColor

from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, Qgis
from qgis.gui import QgsFileWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mapillary_settings_dialog_base.ui'))


class mapillarySettings(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self,module, parent=None):
        """Constructor."""
        super(mapillarySettings, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.module = module
        self.iface = module.iface
        self.setWindowTitle("go2mapillary settings")
        self.fileWidget.setStorageMode(QgsFileWidget.SaveFile)
        self.buttonBox.accepted.connect(self.applySettings)
        self.addCategoryButton.clicked.connect(self.addCategoryAction)
        self.removeCategoryButton.clicked.connect(self.removeCategoryAction)
        self.tableWidget.setColumnWidth(1 , 150)

    def loadSettings(self):
        pass

    def applySettings(self):
        self.new_settings = {}

    def addCategoryAction(self):
        if self.newCategoryEdit.text():
            self.tableWidget.setRowCount(self.tableWidget.rowCount()+1)
            self.tableWidget.setItem(self.tableWidget.rowCount()-1, 0, QTableWidgetItem())
            self.tableWidget.item(self.tableWidget.rowCount()-1, 0).setBackground(self.mColorButton.color())
            self.tableWidget.setItem(self.tableWidget.rowCount()-1, 1, QTableWidgetItem(self.newCategoryEdit.text()))
            self.newCategoryEdit.setText("")

    def removeCategoryAction(self):
        if self.tableWidget.selectedItems():
            del_row = self.tableWidget.selectedItems()[0].row()
            self.tableWidget.clearSelection()
            self.tableWidget.removeRow(del_row)
            self.tableWidget.clearSelection()
        elif self.tableWidget.rowCount() > 0:
            self.tableWidget.removeRow(self.tableWidget.rowCount()-1)