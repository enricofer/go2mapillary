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

from .mapillary_api import getProxySettings, mapillaryApi

from .mapillary_image_info import mapillaryImageInfo

import os
import sys
import json


class mapillaryViewer(QObject):

    messageArrived = pyqtSignal(dict)
    openFilter = pyqtSignal()

    def __init__(self, parentInstance):
        super(mapillaryViewer, self).__init__()
        self.parentInstance = parentInstance
        self.viewport = parentInstance.dlg.webView
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
        self.mly_api = mapillaryApi()
        self.page = 'https://enricofer.github.io/go2mapillary/res/browser.html'
        self.openLocation('')
        self.enabled = True

        proxy_conf = getProxySettings()
        if proxy_conf:
            proxy = QNetworkProxy()
            if proxy_conf['type'] == "DefaultProxy":
                proxy.setType(QNetworkProxy.DefaultProxy)
            elif proxy_conf['type'] == "Socks5Proxy":
                proxy.setType(QNetworkProxy.Socks5Proxy)
            elif proxy_conf['type'] == "HttpProxy":
                proxy.setType(QNetworkProxy.HttpProxy)
            elif proxy_conf['type'] == "HttpCachingProxy":
                proxy.setType(QNetworkProxy.HttpCachingProxy)
            elif proxy_conf['type'] == "FtpCachingProxy":
                proxy.setType(QNetworkProxy.FtpCachingProxy)
            proxy.setHostName(proxy_conf['host'])
            proxy.setPort(int(proxy_conf['port']))
            proxy.setUser(proxy_conf['user'])
            proxy.setPassword(proxy_conf['password'])
            QNetworkProxy.setApplicationProxy(proxy)

    def registerJS(self):
        self.viewport.page().mainFrame().addToJavaScriptWindowObject("QgisConnection", self)



    def openLocation(self, key):
        if not self.locationKey:
            self.viewport.load(QUrl(self.page+'?key='+key))
        else:
            #js = 'this.key_param = "%s";this.mly.moveToKey(this.key_param).then(function() {},function(e) { console.error(e); })' % key
            js = 'this.changeImgKey("%s")' % key
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

    @pyqtSlot(str)
    def restoreTags(self,key):
        print ('restoreTags')
        if key:
            js = "this.updateTags('%s')" % json.dumps(self.parentInstance.sample_cursor.restoreTags(key))
            self.viewport.page().mainFrame().evaluateJavaScript(js)

    @pyqtSlot()
    def openFilterDialog(self):
        self.openFilter.emit()

    @pyqtSlot(str)
    def setCompareKey(self,key):
        self.parentInstance.setCompareKey(key)

    @pyqtSlot(str)
    def saveImg(self,key):
        self.mly_api.download(key)

    @pyqtSlot(str)
    def openBrowser(self,key):
        self.mly_api.browser(key)

    @pyqtSlot(str)
    def openMarkerForm(self,mly_id):
        s,key,id = mly_id.split(':')
        self.parentInstance.sample_cursor.editSample('marker',key,id)

    @pyqtSlot(str)
    def locate(self,key):
        mapillaryImageInfo.locate(self.parentInstance,key)

    def addTag(self,key,id,color,loc):
        self.restoreTags(key)

    def addMarkers(self,markers_def):
        js = "this.enableMarkers();;this.mHandler.restoreMarkers(JSON.parse('%s'));" % json.dumps(markers_def)
        #js = "this.currentHandler.unsubscribe();this.mHandler.subscribe();"
        #js += "this.mHandler.restoreMarkers(JSON.parse('%s'));this.currentHandler.subscribe();" % json.dumps(markers_def)
        self.viewport.page().mainFrame().evaluateJavaScript(js)

    def removeTag(self,key):
        self.restoreTags(key)

    def removeMarker (self,key,id):
        js = "this.mHandler.removeMarker(['id:%s:%s']);" % (key,id)
        # print ('REMOVE',js)
        self.viewport.page().mainFrame().evaluateJavaScript(js)

    def removeSample(self,type,key,id):
        if type == 'tag':
            self.removeTag()
        elif type == 'marker':
            self.removeMarker(key,id)

    def change_sample(self,featId):
        feat = self.parentInstance.sample_cursor.samplesLayer.getFeature(featId)
        if feat['cat']:
            color = self.parentInstance.sample_settings.settings['categories'][feat['cat']]
        else:
            color = '#ffffff'
        if feat['type'] == 'tag':
            js = "this.changeTag('id:%s:%d','%s');" % (feat['key'],feat['id'],color)
        elif feat['type'] == 'marker':
            loc = feat.geometry().asPoint()
            latlon = '{lat:%f,lon:%f}' % (loc.y(),loc.x())
            js = "this.mHandler.addOrReplaceViewerMarker('id:%s:%s',%s,'%s');" % (feat['key'],feat['id'],latlon,color)
        self.viewport.page().mainFrame().evaluateJavaScript(js)

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
