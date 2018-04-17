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
from PyQt5.QtCore import QSettings, QObject, QUrl, QDir, pyqtSignal, pyqtProperty, pyqtSlot
from PyQt5.QtGui import *
from PyQt5.QtWebKit import QWebSettings
from qgis.PyQt.QtNetwork import QNetworkProxy

from qgis.core import QgsNetworkAccessManager

import os
import sys
import json


class mapillaryViewer(QObject):

    messageArrived = pyqtSignal(dict)

    def __init__(self, viewport):
        super(mapillaryViewer, self).__init__()
        self.viewport = viewport
        #self.viewport.statusBarMessage.connect(self.getJSONmessage)
        self.viewport.page().mainFrame().javaScriptWindowObjectCleared.connect(self.registerJS)
        self.locationKey = None
        WS = self.viewport.settings()
        WS.setAttribute(QWebSettings.JavascriptEnabled,True)
        WS.setAttribute(QWebSettings.DeveloperExtrasEnabled,True)
        WS.setAttribute(QWebSettings.JavascriptCanAccessClipboard,True)
        WS.setAttribute(QWebSettings.PrintElementBackgrounds,True)
        WS.setAttribute(QWebSettings.OfflineStorageDatabaseEnabled,True)
        WS.setAttribute(QWebSettings.LocalStorageEnabled,True)
        WS.setAttribute(QWebSettings.PluginsEnabled,True)
        WS.setAttribute(QWebSettings.WebGLEnabled,True)
        self.viewport.page().setNetworkAccessManager(QgsNetworkAccessManager.instance())
        
        s = QSettings() #getting proxy from qgis options settings
        proxyEnabled = s.value("proxy/proxyEnabled", "")
        proxyType = s.value("proxy/proxyType", "" )
        proxyHost = s.value("proxy/proxyHost", "" )
        proxyPort = s.value("proxy/proxyPort", "" )
        proxyUser = s.value("proxy/proxyUser", "" )
        proxyPassword = s.value("proxy/proxyPassword", "" )
        print (proxyEnabled+"; "+proxyType+"; "+proxyHost+"; " + proxyPort+"; " + proxyUser+"; " +proxyPassword)
        
        if proxyEnabled == "true": # test if there are proxy settings
            proxy = QNetworkProxy()
            if proxyType == "DefaultProxy":
               proxy.setType(QNetworkProxy.DefaultProxy)
            elif proxyType == "Socks5Proxy":
               proxy.setType(QNetworkProxy.Socks5Proxy)
            elif proxyType == "HttpProxy":
               proxy.setType(QNetworkProxy.HttpProxy)
            elif proxyType == "HttpCachingProxy":
               proxy.setType(QNetworkProxy.HttpCachingProxy)
            elif proxyType == "FtpCachingProxy":
               proxy.setType(QNetworkProxy.FtpCachingProxy)
            proxy.setHostName(proxyHost)
            proxy.setPort(int(proxyPort))
            proxy.setUser(proxyUser)
            proxy.setPassword(proxyPassword)
            #QNetworkProxy.setApplicationProxy(proxy)
        
        self.page = os.path.join(os.path.dirname(__file__),'res','browser.html')
        #self.page = os.path.join(os.path.dirname(__file__),'res','browser_test_cursor.html')
        self.openLocation('')
        self.enabled = True

    def registerJS(self):
        self.viewport.page().mainFrame().addToJavaScriptWindowObject("QgisConnection", self)



    def openLocation(self, key):
        if not self.locationKey:
            print('file:///' + QDir.fromNativeSeparators(self.page+'?key='+key))
            self.viewport.load(QUrl('file:///' + QDir.fromNativeSeparators(self.page+'?key='+key))) #'file:///'+
        else:
            js = 'this.key_param = "%s";this.mly.moveToKey(this.key_param).then(function() {},function(e) { console.error(e); })' % key
            self.viewport.page().mainFrame().evaluateJavaScript(js)
        self.locationKey = key



    @pyqtSlot(str)
    def JSONmessage(self,status):
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
        self.viewport.page().mainFrame().evaluateJavaScript(js)
        self.enabled = None

    def isEnabled(self):
        return self.enabled
