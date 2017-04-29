# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go2mapillaryDockWidget
                                 A QGIS plugin
 mapillary explorer
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

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal
from .mapillary_explorer_dockwidget_base import Ui_go2mapillaryDockWidgetBase

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mapillary_explorer_dockwidget_base.ui'))


class exgo2mapillaryDockWidget(QtWidgets.QDockWidget, Ui_go2mapillaryDockWidgetBase):

    closingPlugin = pyqtSignal()

    def __init__(self):
        """Constructor."""
        QtWidgets.QDockWidget.__init__(self)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()


class go2mapillaryDockWidget(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(go2mapillaryDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

