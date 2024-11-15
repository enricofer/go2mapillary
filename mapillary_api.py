# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go2mapillary
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
import sys
import requests
import webbrowser
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.core import QgsMessageLog, Qgis


from .mapillary_settings import mapillarySettings
from .mapillary_coverage import networkConnection

ROOT = 'https://graph.mapillary.com/' # ?????
#ACCESS_TOKEN = 'MLY|4756369651124824|daee50b6cb15570a90b6a151bbd97bf3'
DOWNLOAD_ENDPOINT = 'https://d1cuyjsrcm0gby.cloudfront.net/%s/thumb-2048.jpg' # ?????
BROWSER_ENDPOINT = 'https://www.mapillary.com/app/?pKey=%s&focus=photo' 

        
class mapillaryApi:

    def __init__(self):
        self.settings = mapillarySettings()

    def users(self, **kwargs):
        return self.proto_method('users', **kwargs)

    def sequences(self, **kwargs):
        return self.proto_method('sequences', **kwargs)

    def image(self, key):
        return self.proto_method('images/'+key)

    def images(self, **kwargs):
        return self.proto_method('images', **kwargs)

    def map_features(self, **kwargs):
        return self.proto_method('map_features', **kwargs)

    def map_features(self, **kwargs):
        return self.proto_method('map_features', **kwargs)

    def proto_method(self, endpoint, **kwargs):
        kwargs['access_token'] = self.settings.get("access_token","")
        #res = requests.get(ROOT+endpoint, params=kwargs, proxies=getProxiesConf(self.settings.get("use_proxy")))
        res = networkConnection.getJson(ROOT + endpoint + "?" + urlencode(kwargs))
        if res["status"] == 'OK':
            return res.json()
        else:
            QgsMessageLog.logMessage("mapillary connection error: %d" % res["error"], tag="go2mapillary",level=Qgis.Info)

    def download(self,key):
        res = requests.get(DOWNLOAD_ENDPOINT % key, proxies=getProxiesConf(self.settings.get("use_proxy")))
        
        if res.status_code == 200:
            fileName = QFileDialog.getSaveFileName(None,'Save mapillary Image',key+'.jpg',"JPG (*.jpg)")
            if fileName:
                res = networkConnection.getFile(DOWNLOAD_ENDPOINT % self.settings.get("access_token",""), fileName)
                if res["status"] != 'OK':
                    QgsMessageLog.logMessage("mapillary connection error: %d" % res["error"], tag="go2mapillary",level=Qgis.Info)

    def browser(self,key):
        webbrowser.open_new_tab(BROWSER_ENDPOINT % key)