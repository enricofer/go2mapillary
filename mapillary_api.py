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


from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMessageLog, Qgis

ROOT = 'https://a.mapillary.com/v3/'
CLIENT_ID = 'ZUZ1MWdOaW1IXzRucVgxNzhwWTBlZzoyNWJjODcwMWIzNzNjNGQ0'

def getProxiesConf():
    s = QSettings() #getting proxy from qgis options settings
    proxyEnabled = s.value("proxy/proxyEnabled", "")
    proxyType = s.value("proxy/proxyType", "" )
    proxyHost = s.value("proxy/proxyHost", "" )
    proxyPort = s.value("proxy/proxyPort", "" )
    proxyUser = s.value("proxy/proxyUser", "" )
    proxyPassword = s.value("proxy/proxyPassword", "" )
    if proxyEnabled == "true" and proxyType == 'HttpProxy': # test if there are proxy settings
        proxyDict = {
            "http"  : "http://%s:%s@%s:%s" % (proxyUser,proxyPassword,proxyHost,proxyPort),
            "https" : "http://%s:%s@%s:%s" % (proxyUser,proxyPassword,proxyHost,proxyPort)
        }
        return proxyDict
    else:
        return None

class mapillaryApi:

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
        kwargs['client_id'] =  CLIENT_ID
        res = requests.get(ROOT+endpoint, params=kwargs, proxies=getProxiesConf())
        if res.status_code == 200:
            return res.json()
        else:
            QgsMessageLog.logMessage("mapillary connection error: %d" % res.status_code, tag="go2mapillary",level=Qgis.Info)
