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
import json

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QLineEdit
from PyQt5.QtGui import QColor

from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, Qgis, QgsExpressionContextUtils
from qgis.gui import QgsFileWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mapillary_settings_dialog_base.ui'))


class mapillarySettings(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self,parentInstance=None, parent=None):
        """Constructor."""
        super(mapillarySettings, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parentInstance = parentInstance
        if self.parentInstance:
            self.iface = parentInstance.iface
            self.setWindowTitle("go2mapillary settings")
            #self.fileWidget.setStorageMode(QgsFileWidget.SaveFile)
            #self.fileWidget.setFilter("SHP files (*.shp)")
            self.buttonBox.accepted.connect(self.applySettings)
            #self.addCategoryButton.clicked.connect(self.addCategoryAction)
            #self.removeCategoryButton.clicked.connect(self.removeCategoryAction)
            self.tableWidget.setColumnWidth(1 , 150)
            #self.newCategoryEdit.setMaxLength(20)

        #self.settings_ = {
        #    'sample_source': 'memory',
        #    'auto_open_form': True,
        #    'categories': {
        #        'cat_a':'#ff0000',
        #        'cat_b':'#0000ff',
        #        'cat_c':'#00ff00',
        #    }
        #}

        self.proto_settings = {
            'access_token': '',
            'computed_tiles_coverage': True,
            'use_proxy': True,
            'sample_source': 'memory',
        }


        if QgsExpressionContextUtils.globalScope().hasVariable('mapillarySettings'):
            self.settings = json.loads(QgsExpressionContextUtils.globalScope().variable('mapillarySettings'))
        else:
            self.settings = self.proto_settings
            QgsExpressionContextUtils.setGlobalVariable("mapillarySettings", json.dumps(self.settings))
        
        print (self.settings)
        
        self.loadSettings()
    

    def open(self):
        self.loadSettings()
        super().open()

    def loadSettings(self):
        self.tableWidget.clear()
        self.tableWidget.setRowCount(0)
        print (self.settings)
        for key,proto_value in self.proto_settings.items():
            value = self.settings.get(key) if key in self.settings else proto_value
            print ("*",key, self.settings.get(key), value, proto_value)
            self.tableWidget.insertRow(0)
            self.tableWidget.setItem(0, 0, QTableWidgetItem(key))
            self.tableWidget.item(0, 0).setFlags(Qt.NoItemFlags)
            if isinstance(proto_value, bool):
                self.tableWidget.setItem(0, 1, QTableWidgetItem())
                self.tableWidget.item(0, 1).setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                self.tableWidget.item(0, 1).setCheckState(Qt.Checked if value == True else Qt.Unchecked)
            elif isinstance(proto_value, str):
                self.tableWidget.setItem(0, 1, QTableWidgetItem(value))
        self.tableWidget.resizeColumnsToContents()
            # elif isinstance(int, self.proto_settings[key]):
            # elif isinstance(float, self.proto_settings[key]):

    def applySettings_(self):
        self.settings = {}
        if self.radioButtonMemorySource.isChecked():
            self.settings['sample_source'] = 'memory'
        else:
            self.settings['sample_source'] = self.fileWidget.filePath()
        self.settings['auto_open_form'] = self.autoOpenCheckBox.isChecked()
        categories = {}
        for row in range(0,self.tableWidget.rowCount()):
            categories[self.tableWidget.item(row,1).text()[:20]] = self.tableWidget.item(row,0).background().color().name()
        self.settings['categories'] = categories
        self.parentInstance.sample_cursor.update_ds(self.settings['sample_source'])
        QgsExpressionContextUtils.setGlobalVariable("mapillarySettings", json.dumps(self.settings))

    def applySettings(self):
        self.settings = {}
        for row in range(0,self.tableWidget.rowCount()):
            if isinstance(self.proto_settings[self.tableWidget.item(row,0).text()],str):
                self.settings[self.tableWidget.item(row,0).text()] = self.tableWidget.item(row,1).text()
            elif isinstance(self.proto_settings[self.tableWidget.item(row,0).text()],bool):
                self.settings[self.tableWidget.item(row,0).text()] = self.tableWidget.item(row,1).checkState() == Qt.Checked
        if self.parentInstance:
            self.parentInstance.sample_cursor.update_ds(self.settings['sample_source'])
        print (self.settings)
        QgsExpressionContextUtils.setGlobalVariable("mapillarySettings", json.dumps(self.settings))

    def get(self,key,default=None):
        return self.settings.get(key,default)