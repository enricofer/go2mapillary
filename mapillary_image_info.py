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


from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, Qgis, QgsMessageLog

from .mapillary_api import mapillaryApi

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mapillary_image_info_dialog_base.ui'))


class mapillaryImageInfo(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self,module, parent=None):
        """Constructor."""
        super(mapillaryImageInfo, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.module = module
        self.setWindowTitle("go2mapillary image info")
        self.okButton.clicked.connect(self.closeAction)
        self.panToButton.clicked.connect(self.panToAction)
        self.level = None
        self.mapillaryApi = mapillaryApi()

    def setup(self,key):
        props = ['ca','camera_make','camera_model','captured_at','key','pano','project_key','user_key','username','latitude','longitude']
        self.label_ca.hide()
        self.field_ca.hide()
        self.label_project_key.hide()
        self.field_project_key.hide()
        res = self.mapillaryApi.image(key)
        print (res)
        if res:
            self.field_latitude.setText(str(res["geometry"]["coordinates"][1]))
            self.field_longitude.setText(str(res["geometry"]["coordinates"][0]))
            for prop,value in res["properties"].items():
                getattr(self, 'label_' + prop).show()
                getattr(self, 'field_' + prop).show()
                getattr(self, 'field_' + prop).setText(str(value))
            #self.adjustSize()


    def closeAction(self):
        self.close()

    def panToAction(self):
        crsCanvas = self.module.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsWGS84 = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsWGS84, crsCanvas, QgsProject.instance())
        sourcePoint = QgsPointXY(float(self.field_longitude.text()),float(self.field_latitude.text()))
        self.module.iface.mapCanvas().setCenter(xform.transform(sourcePoint))
        self.module.iface.mapCanvas().refresh()

    @staticmethod
    def openKey(module,key):
        dialog = mapillaryImageInfo(module)
        #dialog.setWindowFlags(Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        dialog.setup(key)
        dialog.exec_()