# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go2mapillary
                                 A QGIS plugin
 mapillary viewer
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
import os
import json


class mapillaryViewer(QObject):

    messageArrived = pyqtSignal(dict)

    def __init__(self, viewport):
        super(mapillaryViewer, self).__init__()
        self.viewport = viewport
        self.viewport.statusBarMessage.connect(self.getJSONmessage)
        #self.viewport.setPage(MyBrowser())
        #self.page = os.path.join(os.path.dirname(__file__),'res','browse.html')
        self.page = 'qrc:///plugins/go2mapillary/res/browse.html'
        self.openLocation('')
        self.enabled = True
        print self.page
    
    def openLocation(self, key):
        self.locationKey = key
        print QUrl(self.page+'?key='+key)
        self.viewport.load(QUrl(self.page+'?key='+key))

    def getJSONmessage(self,status):
        try:
            message = json.JSONDecoder().decode(status)
        except:
            message = None
        if message:
            self.messageArrived.emit(message)

    def enable(self):
        js = 'document.getElementById("focus").classList.add("hidden");'
        self.viewport.page().mainFrame().evaluateJavaScript(js)
        self.enabled = True

    def disable(self):
        js = 'document.getElementById("focus").classList.remove("hidden");'
        print self.viewport
        self.viewport.page().mainFrame().evaluateJavaScript(js)
        self.enabled = None

    def isEnabled(self):
        return self.enabled