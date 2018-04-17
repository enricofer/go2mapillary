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
from PyQt5.QtCore import pyqtSignal, QDate, QDateTime

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
        self.setWindowTitle("go2mapillary filter")
        self.fromDateWidget.setDate(QDate(2014, 1, 1))
        self.toDateWidget.setDate(QDate.currentDate())
        self.buttonBox.accepted.connect(self.setFilter)
        self.addUserFilter.clicked.connect(self.addUserAction)
        self.removeUserFilter.clicked.connect(self.removeUserAction)
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
                'from':  QDateTime(self.fromDateWidget.date()).toTime_t()*1000,
                'to': QDateTime(self.toDateWidget.date()).toTime_t()*1000
            },
            'byUser':{
                'enabled': self.users_group.isChecked(),
                'users': users_list,
                'userkeys': userkeys_list,
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
        if self.filter['onlyPanorama']:
            if sqlFilter:
                sqlFilter += ' and '
            sqlFilter += '("pano" = 1)'

        #print("sqlFilter", sqlFilter)
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
                self.fromDateWidget.setDate(mintime.date())
                maxtime = QDateTime()
                maxtime.setTime_t(max_timestamp/1000)
                self.toDateWidget.setDate(maxtime.date())

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