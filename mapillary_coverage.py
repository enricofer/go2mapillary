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
from .mapillary_api import ACCESS_TOKEN

import requests
import math
import json
import datetime
import mercantile
import tempfile
import urllib.parse
import math

from PyQt5.QtCore import pyqtSignal
from qgis.PyQt.QtCore import QObject, QSettings, Qt
from qgis.PyQt.QtWidgets import QProgressBar, QApplication, QAction

from qgis.core import QgsVectorTileLayer, QgsDataSourceUri, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsLayerTreeLayer, QgsProject, QgsExpressionContextUtils, Qgis, QgsMessageLog, QgsMapLayer
from qgis.gui import QgsMessageBar

from .identifygeometry import IdentifyGeometry


VECTOR_TILES_ENDPOINTS = {
    "original": r"https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=" + ACCESS_TOKEN,
    "computed": r"https://tiles.mapillary.com/maps/vtp/mly1_computed_public/2/{z}/{x}/{y}?access_token=" + ACCESS_TOKEN,
}

LAYER_LEVELS = ['overview', 'sequences', 'images']


class mapillary_coverage(QObject):

    changeVisibility = pyqtSignal(bool)

    def __init__(self, explorer, callback, vectorTileSet='computed'):
        self.explorer = explorer
        self.iface = explorer.iface
        self.canvas = explorer.iface.mapCanvas()
        self.actual_ranges = None
        self.vectorTileSet = vectorTileSet
        self.vectorTileLayer = None
        self.previuosTool = None
        self.active = False
        self.callback = callback
        self.legendRoot = QgsProject.instance().layerTreeRoot()
        super(mapillary_coverage, self).__init__(None)

    def zoomLevel(self): # courtesy of https://github.com/datalyze-solutions/TileMapScaleLevels/blob/master/tilemapscalelevels.py
        scale = self.canvas.scale()
        dpi = self.iface.mainWindow().physicalDpiX()
        maxScalePerPixel = 156543.04
        inchesPerMeter = 39.37
        zoomlevel = int(round(math.log( ((dpi* inchesPerMeter * maxScalePerPixel) / scale), 2 ), 0))
        return zoomlevel

    def getURI(self):
        u = QgsDataSourceUri()
        u.setParam('type', 'xyz')
        u.setParam('zmax', '14')
        u.setParam('zmin', '0')
        u.setParam('http-header:referer', None)
        u.setParam('url', VECTOR_TILES_ENDPOINTS[self.vectorTileSet])
        print(VECTOR_TILES_ENDPOINTS[self.vectorTileSet])
        print(u.encodedUri().data().decode())
        return u.encodedUri().data().decode()
    
    def getLevel(self):
        zl = self.zoomLevel()
        if zl < 6:
            return 'overview'
        elif zl < 14:
            return 'sequences'
        else:
            return 'images'

    def setCurrentKey(self, imageKey=None, sequenceKey=None, overviewKey=None):
        print("imageKey", imageKey)
        QgsExpressionContextUtils.setLayerVariable(self.vectorTileLayer, "mapillaryImageKey",imageKey)
        QgsExpressionContextUtils.setLayerVariable(self.vectorTileLayer, "mapillarySequenceKey",sequenceKey)
        QgsExpressionContextUtils.setLayerVariable(self.vectorTileLayer, "mapillaryOverviewKey",overviewKey)
        if self.vectorTileLayer:
            self.vectorTileLayer.triggerRepaint()

    def activate(self):
        print ("activate",self.getURI())
        if not self.vectorTileLayer:
            self.vectorTileLayer = QgsVectorTileLayer(self.getURI(), "Mapillary")
            QgsProject.instance().addMapLayer(self.vectorTileLayer, False)
            self.legendRoot.insertLayer(0, self.vectorTileLayer)
        self.previuosTool = self.canvas.mapTool()
        self.mapSelectionTool = IdentifyGeometry(self.canvas, [self.vectorTileLayer]) #self.parentInstance.sample_cursor.samplesLayer
        self.mapSelectionTool.geomIdentified.connect(self.callback)
        self.canvas.setMapTool(self.mapSelectionTool) 
        self.active = True
 
    def deactivate(self):
        print ("deactivate")
        #self.reorderLegendInterface(False)
        if self.vectorTileLayer:
            QgsProject.instance().removeMapLayer(self.vectorTileLayer.id())
        self.canvas.setMapTool(self.previuosTool) 
        self.vectorTileLayer = None
        self.iface.mapCanvas().refresh()
        self.active = False

    def reorderLegendInterface(self, show):
        print ("reorderLegendInterface")
        
        layerNode = legendRoot.findLayer(self.vectorTileLayer)
        if layerNode:
            layerNode.parent().removeChildNode(layerNode)
        if show:
            legendRoot.insertLayer(0, self.vectorTileLayer)

    def applyFilter(self, sqlFilter):
        print ("applyFilter")
        self.vectorTileLayer.dataProvider().setSubsetString(sqlFilter)
        self.vectorTileLayer.triggerRepaint()
    
    def transformToWGS84(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsSrc = crcMappaCorrente
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint) # forward transformation: src -> dest
