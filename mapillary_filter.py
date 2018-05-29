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
from PyQt5.QtCore import pyqtSignal, QDate, QDateTime, QPoint


from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, Qgis
from qgis.gui import QgsMapTool

from .mapillary_api import mapillaryApi

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mapillary_filter_dialog_base.ui'))


class mapillaryFilter(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self,module, parent=None):
        """Constructor."""
        super(mapillaryFilter, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.module = module
        self.iface = module.iface
        self.setWindowTitle("go2mapillary filter")
        self.fromDateWidget.setDate(QDate(2014, 1, 1))
        self.toDateWidget.setDate(QDate.currentDate())
        self.buttonBox.accepted.connect(self.setFilter)
        self.addUserFilter.clicked.connect(self.addUserAction)
        self.removeUserFilter.clicked.connect(self.removeUserAction)
        self.sampleButton.clicked.connect(self.sampleOnCanvasAction)
        self.level = None
        self.mapillaryApi = mapillaryApi()
        self.setFilter()


    def setFilter(self):
        users_list = []
        userkeys_list = []
        for row in range(0,self.userFiltersTable.rowCount()):
            users_list.append(self.userFiltersTable.item(row,0).text())
            userkeys_list.append("'%s'" % self.userFiltersTable.item(row,1).text())

        self.filter = {
            'byDate':{
                'enabled': self.date_group.isChecked(),
                'from':  self.fromDateWidget.dateTime().toTime_t()*1000, #QDateTime(self.fromDateWidget.date()).toTime_t()*1000,
                'to': self.toDateWidget.dateTime().toTime_t()*1000 #QDateTime(self.toDateWidget.date()).toTime_t()*1000
            },
            'byUser':{
                'enabled': self.users_group.isChecked(),
                'users': users_list,
                'userkeys': userkeys_list,
            },
            'lookAt':{
                'enabled': self.looking_at_group.isChecked(),
                'lat':float(self.lat_widget.text() or '0'),
                'lon':float(self.lon_widget.text() or '0')
            },
            'onlyPanorama': self.onlyPanorama.isChecked()
        }
        for level in ['images','sequences','overview']:
            self.applySqlFilter(level)

    def getFilter(self):
        return self.filter

    def show(self, level):
        self.level = level
        super(mapillaryFilter, self).show()
        self.populateSearch()


    def applySqlFilter(self,level=None,layer=None):
        sqlFilter = ''
        if self.filter['byDate']['enabled']:
            sqlFilter += '("captured_at" > %d and "captured_at" < %d)' %(self.filter['byDate']['from'],self.filter['byDate']['to'])
        if self.filter['byUser']['enabled'] and self.filter['byUser']['userkeys']:
            if sqlFilter:
                sqlFilter += ' and '
            userkeys_list = ','.join(self.filter['byUser']['userkeys'])
            sqlFilter += '("userkey" in (%s))' % userkeys_list
        if self.filter['lookAt']['enabled'] and self.filter['lookAt']['lat'] and self.filter['lookAt']['lon']:
            bbox = "%f,%f,%f,%f" % (
                self.filter['lookAt']["lon"]-0.005,
                self.filter['lookAt']["lat"]-0.005,
                self.filter['lookAt']["lon"]+0.005,
                self.filter['lookAt']["lat"]+0.005,
            )
            lookat = '%f,%f' % (
                self.filter['lookAt']["lon"],
                self.filter['lookAt']["lat"],
            )
            res = self.mapillaryApi.images(bbox=bbox,lookat=lookat)
            if res:
                keys_looking_at = ""
                for feat in res["features"]:
                    keys_looking_at += "'%s'," % feat["properties"]["key"]
                if keys_looking_at:
                    if sqlFilter:
                        sqlFilter += ' and '
                    sqlFilter += '("key" in (%s))' % keys_looking_at[:-1]

        if self.filter['onlyPanorama']:
            if sqlFilter:
                sqlFilter += ' and '
            sqlFilter += '("pano" = 1)'

        if not layer:
            layer = getattr(self.module.coverage,level+'Layer')
        try:
            layer.setSubsetString(sqlFilter)
            layer.triggerRepaint()
        except:
            pass

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def populateSearch(self):
        layer = getattr(self.module.coverage, self.level + 'Layer')
        userkeys = []
        max = 0
        min_timestamp = sys.maxsize
        max_timestamp = 0
        for feat in layer.getFeatures():
            if feat['captured_at'] < min_timestamp:
                min_timestamp = feat['captured_at']
            if feat['captured_at'] > max_timestamp:
                max_timestamp = feat['captured_at']
            if max<100 and not feat['userkey'] in userkeys:
                userkeys.append(feat['userkey'])
                max += 1

        user_search = self.mapillaryApi.users(userkeys=','.join(userkeys))
        if user_search:
            usermap = {}
            for user in user_search:
                usermap[user['username']] = user['key']
            self.usersSearchFilter.clear()
            for user in sorted(usermap.keys()):
                self.usersSearchFilter.addItem(user, usermap[user])

            if not self.date_group.isChecked():
                mintime = QDateTime()
                mintime.setTime_t(min_timestamp/1000)
                self.fromDateWidget.setDateTime(mintime)
                maxtime = QDateTime()
                maxtime.setTime_t(max_timestamp/1000)
                self.toDateWidget.setDateTime(maxtime)

    def addUserAction(self):
        userCell = QtWidgets.QTableWidgetItem(self.usersSearchFilter.currentText())
        if userCell:
            userkeyCell = QtWidgets.QTableWidgetItem(self.usersSearchFilter.currentData())
            self.userFiltersTable.insertRow(self.userFiltersTable.rowCount())
            self.userFiltersTable.setItem(self.userFiltersTable.rowCount()-1,0,userCell)
            self.userFiltersTable.setItem(self.userFiltersTable.rowCount()-1,1,userkeyCell)


    def removeUserAction(self):
        if self.userFiltersTable.selectedItems():
            selected_rows = set()
            for item in self.userFiltersTable.selectedItems():
                selected_rows.add(item.row())
            for row_idx in list(selected_rows):
                self.userFiltersTable.removeRow(row_idx)

    def sampleOnCanvasAction(self):
        sampleTool = samplePointOnCanvas(self.iface.mapCanvas())
        sampleTool.pointClicked.connect(self.clickedOnCanvasAction)
        self.iface.mapCanvas().setMapTool(sampleTool)
        self.hide()

    def clickedOnCanvasAction(self,clickedPoint):
        self.iface.mapCanvas().setMapTool(self.module.mapSelectionTool)
        crsCanvas = self.module.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsWGS84 = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsCanvas, crsWGS84, QgsProject.instance())
        wgs84point = xform.transform(clickedPoint)
        self.lon_widget.setText(str(wgs84point.x()))
        self.lat_widget.setText(str(wgs84point.y()))
        super(mapillaryFilter, self).show()
        self.raise_()


class samplePointOnCanvas(QgsMapTool):

    pointClicked = pyqtSignal(QgsPointXY)

    def canvasPressEvent(self, event):
        px = event.pos().x()
        py = event.pos().y()
        pressedPoint = QPoint(px, py)
        self.pointClicked.emit(self.toMapCoordinates(pressedPoint))


