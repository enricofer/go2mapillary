# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go2mapillary
                                 A QGIS plugin
 mapillary explorer
                             -------------------
        begin                : 2016-01-21
        copyright            : (C) 2016 by enrico ferreguti
        email                : enricofer@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import os 
import site
import sys

from qgis.PyQt.QtWidgets import QMessageBox

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    QTWK_ENABLED = True
except ImportError:
    QTWK_ENABLED = False

sys.path.append(os.path.dirname(__file__))

site.addsitedir(os.path.join(os.path.dirname(__file__),'extlibs'))

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load go2mapillary class from file go2mapillary.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    if QTWK_ENABLED:
        from .mapillary_explorer import go2mapillary
        return go2mapillary(iface)
    else:
        QMessageBox.critical(None, "Can't install go2mapillary" ,
                             'QtWebKitWidgets python bindings module is required for plugin execution. \nManually install it from console typing: sudo apt install python3-pyqt5.qtwebkit')
        return fakePlugin()

class fakePlugin:
    def __init__(self):
        pass

    def initGui(self):
        pass

    def unload(self):
        pass