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

ROOT = 'https://a.mapillary.com/v3/'
CLIENT_ID = 'ZUZ1MWdOaW1IXzRucVgxNzhwWTBlZzoyNWJjODcwMWIzNzNjNGQ0'
#CLIENT_SECRET = 'ODkwNGFlYmQ5ZmQ2MGNhMjQ1YjZmMjE2ZjY1NTY3ZTM='

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

    def images(self, **kwargs):
        return self.proto_method('images', **kwargs)

    def map_features(self, **kwargs):
        return self.proto_method('map_features', **kwargs)

    def map_features(self, **kwargs):
        return self.proto_method('map_features', **kwargs)

    def proto_method(self, endpoint, **kwargs):
        print (kwargs)
        parameters = {'client_id': CLIENT_ID}
        for name, value in kwargs.items():
            parameters[name] = value

        res = requests.get(ROOT+endpoint, params=parameters, proxies=getProxiesConf())
        if res.status_code == 200:
            return res.json()
        else:
            pass #raise exception
