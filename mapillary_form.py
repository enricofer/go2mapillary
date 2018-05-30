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
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QColor

from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, Qgis, QgsExpressionContextUtils
from qgis.gui import QgsFileWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mapillary_form_dialog_base.ui'))


class mapillaryForm(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self,parentInstance, parent=None):
        """Constructor."""
        super(mapillaryForm, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parentInstance = parentInstance
        self.iface = parentInstance.iface
        self.setWindowTitle("go2mapillary sample form")
        self.buttonBox.accepted.connect(self.applyForm)
        self.deleteButton.clicked.connect(self.deleteFeatureAction)

    def open(self,feat):
        self.comboBox.clear()
        for cat,color in self.parentInstance.sample_settings.settings['categories'].items():
            self.comboBox.addItem(cat,color)
        self.keyEdit.setText(str(feat['key']))
        self.typeEdit.setText(str(feat['type']))
        if feat['cat']:
            cat_idx = self.comboBox.findText(str(feat['cat']))
        else:
            cat_idx = 0
        self.comboBox.setCurrentIndex(cat_idx)
        if feat['note']:
            self.noteEdit.setPlainText(str(feat['note']))
        else:
            self.noteEdit.setPlainText("")
        self.currentFeat = feat
        super(mapillaryForm, self).open()

    def applyForm(self):
        cat_idx = self.parentInstance.sample_cursor.samplesLayer.fields().indexFromName('cat')
        note_idx = self.parentInstance.sample_cursor.samplesLayer.fields().indexFromName('note')
        color_idx = self.parentInstance.sample_cursor.samplesLayer.fields().indexFromName('color')

        if self.currentFeat['cat']:
            color = self.parentInstance.sample_settings.settings['categories'][str(self.currentFeat['cat'])]
        else:
            color = '#ffffff'

        attrs = {
            cat_idx: self.comboBox.currentText(),
            note_idx: self.noteEdit.toPlainText()[:99],
            color_idx:color
        }
        self.parentInstance.sample_cursor.samplesLayer.dataProvider().changeAttributeValues({self.currentFeat.id(): attrs})
        self.parentInstance.viewer.change_sample(self.currentFeat.id())

    def deleteFeatureAction(self):
        key = self.currentFeat['key']
        id = self.currentFeat['id']
        type = self.currentFeat['type']
        self.parentInstance.sample_cursor.samplesLayer.dataProvider().deleteFeatures([self.currentFeat.id()])
        self.parentInstance.sample_cursor.samplesLayer.triggerRepaint()
        self.parentInstance.viewer.removeSample(type,key,id)
        self.close()