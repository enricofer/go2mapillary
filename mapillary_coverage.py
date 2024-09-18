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

from shapely.geometry import Polygon
from go2mapillary.extlibs import mapbox_vector_tile

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

from qgis.core import QgsVectorLayer, QgsVectorTileLayer, QgsDataSourceUri, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsLayerTreeLayer, QgsProject, QgsExpressionContextUtils, Qgis, QgsMessageLog, QgsMapLayer
from qgis.gui import QgsMessageBar

from .identifygeometry import IdentifyGeometry


VECTOR_TILES_ENDPOINTS = {
    "original": r"https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=" + ACCESS_TOKEN,
    "computed": r"https://tiles.mapillary.com/maps/vtp/mly1_computed_public/2/{z}/{x}/{y}?access_token=" + ACCESS_TOKEN,
}

LAYER_LEVELS = ['overview', 'sequence', 'image']

SERVER_URL = r"https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=MLY|4756369651124824|daee50b6cb15570a90b6a151bbd97bf3"

CACHE_EXPIRE_HOURS = 24

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def ZoomForPixelSize(pixelSize):
    "Maximal scaledown zoom of the pyramid closest to the pixelSize."
    for i in range(30):
        if pixelSize > (180 / 256.0 / 2**i):
            return i-1 if i!=0 else 0 # We don't want to scale up

#get the range of tiles that intersect with the bounding box of the polygon
def getTileRange(bnds, zoom):
    xm=bnds[0]
    xmx=bnds[2]
    ym=bnds[1]
    ymx=bnds[3]
    bottomRight=(xmx,ym)
    starting=deg2num(ymx,xm, zoom)
    ending=deg2num(ym,xmx, zoom) # this will be the tiles containing the ending
    x_range=(starting[0],ending[0])
    y_range=(starting[1],ending[1])
    return(x_range,y_range)

#to get the tile as a polygon object
def getTileASpolygon(z,y,x):
    nw=num2deg(x,y,z)
    se=num2deg(x+1, y+1, z)
    xm=nw[1]
    xmx=se[1]
    ym=se[0]
    ymx=nw[0]
    tile_bound=Polygon([(xm,ym),(xmx,ym),(xmx,ymx),(xm,ymx)])
    return tile_bound

#to tell if the tile intersects with the given polygon
def doesTileIntersects(z, y, x, polygon):
    if(z<10):   #Zoom tolerance; Below these zoom levels, only check if tile intersects with bounding box of polygon
        return True
    else:
        #get the four corners
        tile=getTileASpolygon(x,y,z)
        return polygon.intersects(tile)

#convert the URL to get URL of Tile
def getURL(x,y,z,url):
    u=url.replace("{x}", str(x))
    u=u.replace("{y}", str(y))
    u=u.replace("{z}", str(z))
    return u

def getProxiesConf():
    s = QSettings()  # getting proxy from qgis options settings
    proxyEnabled = s.value("proxy/proxyEnabled", "")
    proxyType = s.value("proxy/proxyType", "")
    proxyHost = s.value("proxy/proxyHost", "")
    proxyPort = s.value("proxy/proxyPort", "")
    proxyUser = s.value("proxy/proxyUser", "")
    proxyPassword = s.value("proxy/proxyPassword", "")
    if proxyEnabled == "true" and proxyType == 'HttpProxy':  # test if there are proxy settings
        proxyDict = {
            "http": "http://%s:%s@%s:%s" % (proxyUser, proxyPassword, proxyHost, proxyPort),
            "https": "http://%s:%s@%s:%s" % (proxyUser, proxyPassword, proxyHost, proxyPort)
        }
        return proxyDict
    else:
        return None

class progressBar:
    def __init__(self, parent, title = ''):
        '''
        progressBar class instatiation method. It creates a QgsMessageBar with provided msg and a working QProgressBar
        :param parent:
        :param msg: string
        '''
        self.iface = parent.iface
        self.title = title

    def start(self,max=0, msg = ''):
        self.widget = self.iface.messageBar().createMessage(self.title,msg)
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0,max)
        self.progressBar.setValue(0)
        self.progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.widget.layout().addWidget(self.progressBar)
        QApplication.processEvents()
        self.iface.messageBar().pushWidget(self.widget, Qgis.Info, 50)
        QApplication.processEvents()

    def setProgress(self,value):
        try:
            self.progressBar.setValue(value)
            QApplication.processEvents()
        except:
            pass

    def setMsg(self,msg):
        self.widget.setText(msg)
        QApplication.processEvents()

    def stop(self, msg = ''):
        '''
        the progressbar is stopped with a succes message
        :param msg: string
        :return:
        '''
        self.iface.messageBar().clearWidgets()
        message = self.iface.messageBar().createMessage(self.title,msg)
        self.iface.messageBar().pushWidget(message, Qgis.Info, 2)


class mapillary_coverage(QObject):

    expire_time = datetime.timedelta(hours=CACHE_EXPIRE_HOURS)

    changeVisibility = pyqtSignal(bool)

    def __init__(self, explorer, callback, vectorTileSet='computed'):
        self.explorer = explorer
        self.iface = explorer.iface
        self.canvas = explorer.iface.mapCanvas()
        self.actual_ranges = None
        self.previuosTool = None
        self.active = False
        self.callback = callback
        self.legendRoot = QgsProject.instance().layerTreeRoot()
        self.defaultLayers()
        self.canvas.mapCanvasRefreshed.connect(self.mapRefreshed)

        self.cache_dir = os.path.join(tempfile.gettempdir(),'go2mapillary')
        QgsMessageLog.logMessage("CACHE_DIR"+self.cache_dir, tag="go2mapillary",level=Qgis.Info)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        super(mapillary_coverage, self).__init__(None)

    def defaultLayers(self):
        for level in LAYER_LEVELS:
            setattr(self, level + 'Layer', None)

    def removeLayers(self):
        for level in LAYER_LEVELS:
            try:
                QgsProject.instance().removeMapLayer(getattr(self, level + 'Layer'))
            except:
                pass
            setattr(self, level + 'Layer', None)


    def mapRefreshed(self, force=None):
        if not self.active:
            self.removeLayers()
            return
        #calculate zoom_level con current canvas extents
        ex = self.iface.mapCanvas().extent()
        wgs84_minimum = self.transformToWGS84(QgsPointXY (ex.xMinimum(),ex.yMinimum()))
        wgs84_maximum = self.transformToWGS84(QgsPointXY (ex.xMaximum(),ex.yMaximum()))
        bounds =(wgs84_minimum.x(),wgs84_minimum.y(),wgs84_maximum.x(),wgs84_maximum.y())
        map_units_per_pixel = (wgs84_maximum.x() - wgs84_minimum.x())/self.iface.mapCanvas().width()
        zoom_level = ZoomForPixelSize(map_units_per_pixel)
        if zoom_level > 14:
            zoom_level = 14

        try:
            ranges = getTileRange(bounds, zoom_level)
        except ValueError:
            return

        if force or not self.actual_ranges or not (
                                    ranges[0][0]==self.actual_ranges[0][0] and
                                    ranges[0][1]==self.actual_ranges[0][1] and
                                    ranges[1][0]==self.actual_ranges[1][0] and
                                    ranges[1][1]==self.actual_ranges[1][1]):
            #print ("ZOOM_LEVEL", zoom_level, "NEW RANGES", ranges, "LAST RANGES", self.actual_ranges)
            self.actual_ranges = ranges
            x_range = ranges[0]
            y_range = ranges[1]

            overview_features = []
            sequence_features = []
            image_features = []

            progress = progressBar(self, 'go2mapillary')

            start_time = datetime.datetime.now()

            for y in range(y_range[0], y_range[1] + 1):
                for x in range(x_range[0], x_range[1] + 1):
                    folderPath = os.path.join(self.cache_dir, str(zoom_level), str(x))
                    filePathMvt = os.path.join(folderPath, str(y) + '.mvt')
                    #filePathJson = os.path.join(folderPath, str(y) + '.json')
                    if not os.path.exists(folderPath):
                        os.makedirs(folderPath)
                    res = None

                    if not os.path.exists(filePathMvt) or (datetime.datetime.fromtimestamp(os.path.getmtime(filePathMvt)) < (datetime.datetime.now() - self.expire_time) ):
                        # make the URL
                        url = getURL(x, y, zoom_level, SERVER_URL)
                        with open(filePathMvt, 'wb') as f:
                            response = requests.get(url, proxies=getProxiesConf(), stream=True)
                            total_length = response.headers.get('content-length')

                            if total_length is None:  # no content length header
                                f.write(response.content)
                            else:
                                dl = 0
                                total_length = int(total_length)
                                progress.start(total_length,'caching vector tile [%d,%d,%d]' % (x, y, zoom_level))
                                QgsMessageLog.logMessage("MISS [%d,%d,%d]" % (x, y, zoom_level), tag="go2mapillary",
                                                         level=Qgis.Info)
                                for data in response.iter_content(chunk_size=4096):
                                    dl += len(data)
                                    f.write(data)
                                    progress.setProgress(dl)


                    if os.path.exists(filePathMvt):
                        progress.start(0, 'loading vector tile [%d,%d,%d]' % (x, y, zoom_level))
                        if not res:
                            with open(filePathMvt, "rb") as f:
                                mvt = f.read()
                                QgsMessageLog.logMessage("CACHE [%d,%d,%d]" % (x, y, zoom_level), tag="go2mapillary",
                                                         level=Qgis.Info)
                        else:
                            mvt = res.content

                        bounds = mercantile.bounds(x,y,zoom_level)
                        tile_box = (bounds.west,bounds.south,bounds.east,bounds.north)
                        json_data = mapbox_vector_tile.decode(mvt, quantize_bounds=tile_box)
                        if "overview" in json_data:
                            overview_features = overview_features + json_data["overview"]["features"]
                        elif "sequence" in json_data:
                            sequence_features = sequence_features + json_data["sequence"]["features"]
                        if "image" in json_data and zoom_level>=14:
                            image_features = image_features + json_data["image"]["features"]

            # print("loading time", datetime.datetime.now() - start_time)
            progress.stop('loading complete')
            rendered_layers = []
            for level in LAYER_LEVELS:
                geojson_file = os.path.join(self.cache_dir, "mapillary_%s.geojson" % level)
                try:
                    QgsProject.instance().removeMapLayer(getattr(self, level+'Layer').id())
                except:
                    pass
                if locals()[level+'_features']:
                    setattr(self, level, True)
                    geojson = {
                        "type": "FeatureCollection",
                        "features": locals()[level+'_features']
                    }

                    with open(geojson_file, 'w') as outfile:
                        json.dump(geojson, outfile)
                    defLyr = QgsVectorLayer(os.path.join(self.cache_dir, 'mapillary_%s.geojson' % level),"Mapillary " + level, "ogr")
                    defLyr.loadNamedStyle(os.path.join(os.path.dirname(__file__), "res", "mapillary_%s.qml" % level))
                    defLyr.setCrs(QgsCoordinateReferenceSystem(4326))
                    self.setCurrentKey(self.explorer.viewer.locationKey)
                    QgsProject.instance().addMapLayer(defLyr)
                    rendered_layers.append(defLyr)
                    #self.iface.addCustomActionForLayerType(getattr(self.explorer,'filterAction_'+level), None, QgsMapLayer.VectorLayer, allLayers=False)
                    #self.explorer.filterDialog.applySqlFilter(layer=defLyr)
                    #self.iface.addCustomActionForLayer(getattr(self.explorer,'filterAction_'+level), defLyr)
                    legendLayerNode = QgsProject.instance().layerTreeRoot().findLayer(defLyr.id())
                    legendLayerNode.setExpanded(False)
                    defLyr.setDisplayExpression('"key"')
                    setattr(self, level + 'Layer', defLyr)
                else:
                    setattr(self, level, False)
            return rendered_layers
        else:
            pass
            #print ("SAME RANGES")

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
        if not zl:
            return
        elif zl < 6:
            return 'overview'
        elif zl < 14:
            return 'sequence'
        else:
            return 'image'
    
    def getCurrentLayerLevel(self):
        return getattr(self, self.getLevel() + 'Layer')
        

    def setCurrentKey(self, key):
        for level in LAYER_LEVELS:
            layer = getattr(self, level + 'Layer')
            try:
                QgsExpressionContextUtils.setLayerVariable(layer, "mapillaryCurrentKey", key)
                layer.triggerRepaint()
            except:
                pass

    def activate(self):
        print ("activate")
        self.active = True
        rendered_layers = self.mapRefreshed()
        self.reorderLegendInterface()
        self.previuosTool = self.canvas.mapTool()
        self.mapSelectionTool = IdentifyGeometry(self.canvas, rendered_layers) #self.parentInstance.sample_cursor.samplesLayer
        self.mapSelectionTool.geomIdentified.connect(self.callback)
        self.canvas.setMapTool(self.mapSelectionTool) 
        self.active = True
 
    def deactivate(self):
        print ("deactivate")
        #self.reorderLegendInterface(False)
        self.active = False
        self.mapRefreshed()
        self.defaultLayers()
        self.removeMapillaryLayerGroup()
        self.canvas.setMapTool(self.previuosTool) 
        self.iface.mapCanvas().refresh()

    def removeMapillaryLayerGroup(self):
        mapillaryGroup = self.getMapillaryLayerGroup()
        QgsProject.instance().layerTreeRoot().removeChildNode(mapillaryGroup)

    def getMapillaryLayerGroup(self):
        legendRoot = QgsProject.instance().layerTreeRoot()
        mapillaryGroupName = 'Mapillary'
        mapillaryGroup = legendRoot.findGroup(mapillaryGroupName)
        if not mapillaryGroup:
            mapillaryGroup = legendRoot.insertGroup(0, mapillaryGroupName)
        mapillaryGroup.setExpanded(False)
        return mapillaryGroup

    def reorderLegendInterface(self):
        print ("reorderLegendInterface")
        legendRoot = QgsProject.instance().layerTreeRoot()
        mapillaryGroup = self.getMapillaryLayerGroup()

        for level in LAYER_LEVELS:
            layer = getattr(self, level + 'Layer')
            try:
                layerNode = legendRoot.findLayer(layer)
            except:
                layerNode = None
            if layerNode:# and layerNode.parent() != mapillaryGroup:
                cloned_node = layerNode.clone()
                mapillaryGroup.insertChildNode(0, cloned_node)
                if layerNode.parent():
                    layerNode.parent().removeChildNode(layerNode)
                else:
                    legendRoot.removeChildNode(layerNode)

    def applyFilter(self, sqlFilter):
        print ("applyFilter")
        for level in LAYER_LEVELS:
            layer = getattr(self, level + 'Layer')
            layer.dataProvider().setSubsetString(sqlFilter)
            layer.triggerRepaint()
    
    def transformToWGS84(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsSrc = crcMappaCorrente
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint) # forward transformation: src -> dest
