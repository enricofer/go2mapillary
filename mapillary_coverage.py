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
from shapely.geometry import Polygon
from go2mapillary.extlibs import mapbox_vector_tile
from .mapillary_api import ACCESS_TOKEN
import requests
import math
import json
import datetime
import mercantile
import tempfile

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import QProgressBar, QApplication, QAction

from qgis.core import QgsVectorTileLayer, QgsRectangle, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsLayerTreeLayer, QgsProject, QgsExpressionContextUtils, Qgis, QgsMessageLog, QgsMapLayer
from qgis.gui import QgsMessageBar

VECTOR_TILES_ENDPOINTS = {
    "original": r"https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=" + ACCESS_TOKEN,
    "computed": r"https://tiles.mapillary.com/maps/vtp/mly1_computed_public/2/{z}/{x}/{y}?access_token=" + ACCESS_TOKEN,
}

LAYER_LEVELS = ['overview', 'sequences', 'images']

class mapillary_coverage:

    def __init__(self, module, vectorTileSet='original'):
        self.module = module
        self.iface = module.iface
        self.actual_ranges = None
        self.vectorTileSet = vectorTileSet
        #self.vectorTileLayer = QgsVectorTileLayer(VECTOR_TILES_ENDPOINTS[self.vectorTileSet], "Mapillary")
        self.mlyKey = None
    
    def setCurrentKey(self, imageKey=None, sequenceKey=None, overviewKey=None):
        QgsExpressionContextUtils.setLayerVariable(self.vectorTileLayer, "mapillaryImageKey",imageKey)
        QgsExpressionContextUtils.setLayerVariable(self.vectorTileLayer, "mapillarySequenceKey",sequenceKey)
        QgsExpressionContextUtils.setLayerVariable(self.vectorTileLayer, "mapillaryOverviewKey",overviewKey)
        self.vectorTileLayer.triggerRepaint()

    def activate(self):
        print ("activate")
        #self.deactivate()
        try:
            self.vectorTileLayer = QgsVectorTileLayer(VECTOR_TILES_ENDPOINTS[self.vectorTileSet], "Mapillary")
            print ("vectorTileLayer",self.vectorTileLayer, VECTOR_TILES_ENDPOINTS[self.vectorTileSet])
            QgsProject.instance().addMapLayer(self.vectorTileLayer,addToLegend=False)
        except Exception as E:
            print (E)
            pass
        self.reorderLegendInterface()

    def deactivate(self):
        print ("deactivate")
        try:
            QgsProject.instance().removeMapLayer(self.vectorTileLayer)
        except Exception as E:
            print (E)
            pass

    def reorderLegendInterface(self):
        print ("reorderLegendInterface")
        legendRoot = QgsProject.instance().layerTreeRoot()
        layerNode = legendRoot.findLayer(self.vectorTileLayer)
        if layerNode:
            layerNode.parent().removeChildNode(layerNode)
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
