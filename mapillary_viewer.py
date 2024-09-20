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
from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from qgis.PyQt.QtNetwork import QNetworkProxy
from PyQt5.QtCore import pyqtSlot
from qgis.core import QgsNetworkAccessManager
from .mapillary_api import ACCESS_TOKEN

from .mapillary_api import getProxySettings, mapillaryApi

from .mapillary_image_info import mapillaryImageInfo

import os
import sys
import json

DEBUG_PORT = '5588'
DEBUG_URL = 'http://127.0.0.1:%s' % DEBUG_PORT
os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = DEBUG_PORT

class mapillaryViewer(QObject):

    messageArrived = pyqtSignal(dict)
    openFilter = pyqtSignal()

    def __init__(self, parentInstance):
        super(mapillaryViewer, self).__init__()
        self.parentInstance = parentInstance
        self.viewport = parentInstance.dlg.webView
        #self.viewport.statusBarMessage.connect(self.getJSONmessage)
        #self.viewport.page().javaScriptWindowObjectCleared.connect(self.registerJS)
        self.locationKey = None

        self.channel = QWebChannel()
        self.channel.registerObject('backend', self)
        self.viewport.page().setWebChannel(self.channel)

        manager = QgsNetworkAccessManager.instance()

        WS = self.viewport.settings()
 

        WS.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        WS.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        WS.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        WS.setAttribute(QWebEngineSettings.PluginsEnabled, True)

        self.mly_api = mapillaryApi()
        self.page = 'https://enricofer.github.io/go2mapillary/res/browser_test.html?accessToken=' + ACCESS_TOKEN
        self.openLocation('')
        self.enabled = True
        self.showWebInspectorAction()

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

    def showWebInspectorAction(self):
        self.inspector = QWebEngineView()
        self.inspector.setWindowTitle('Web Inspector')
        self.inspector.load(QUrl(DEBUG_URL))
        self.viewport.page().setDevToolsPage(self.inspector.page())
        self.inspector.show()
        self.inspector.raise_()

    def registerJS(self):
        #self.viewport.page().mainFrame().addToJavaScriptWindowObject("QgisConnection", self)
        pass

    def open(self, key):
        """
        API Dedicated method to open a user specified mapillary_key:

        from qgis.utils import plugins
        if 'go2mapillary' in plugins:
            plugins['go2mapillary'].viewer.open('ub0cIhoZ7apeuyidB5qyyw')

        """
        status = self.parentInstance.mainAction.isChecked()
        self.parentInstance.dockwidget.show()
        self.parentInstance.mainAction.setChecked(status)
        self.openLocation(key)

    def openLocation(self, key):
        key = str(key)
        print(self.page+'&key='+key)
        if not self.locationKey:
            self.viewport.setUrl(QUrl(self.page+'&key='+key))
        else:
            #js = 'this.key_param = "%s";this.mly.moveToKey(this.key_param).then(function() {},function(e) { console.error(e); })' % key
            js = 'this.changeImgKey("%s")' % key
            self.viewport.page().runJavaScript(js)
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
            self.viewport.page().runJavaScript(js)

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
        self.viewport.page().runJavaScript(js)

    def removeTag(self,key):
        self.restoreTags(key)

    def removeMarker (self,key,id):
        js = "this.mHandler.removeMarker(['id:%s:%s']);" % (key,id)
        # print ('REMOVE',js)
        self.viewport.page().runJavaScript(js)

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
        self.viewport.page().runJavaScript(js)

    def enable(self):
        js = 'document.getElementById("focus").classList.add("hidden");'
        self.viewport.page().runJavaScript(js)
        self.enabled = True

    def disable(self):
        js = 'document.getElementById("focus").classList.remove("hidden");'
        self.viewport.page().runJavaScript(js)
        self.enabled = None

    def isEnabled(self):
        return self.enabled
