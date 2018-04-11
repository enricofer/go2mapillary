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
import math
import os
import urllib
from shapely.geometry import Polygon
import mapbox_vector_tile
import requests
import math
import json
import datetime
import mercantile
import tempfile

from qgis.PyQt.QtCore import QSettings

from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsVectorLayer, QgsProject, QgsExpressionContextUtils

SERVER_URL = r"https://d25uarhxywzl1j.cloudfront.net/v0.1/{z}/{x}/{y}.mvt"

LAYER_LEVELS = ['overview', 'sequences', 'images']

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

class mapillary_coverage:

    expire_time = datetime.timedelta(hours=12)

    def __init__(self,iface):
        self.iface = iface
        self.cache_dir = os.path.join(tempfile.gettempdir(),'go2mapillary')
        print ("CACHE_DIR", self.cache_dir)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.setDefaultLayers()
        self.actual_ranges = None

    def setDefaultLayers(self):
        defaultContent = '{"type": "FeatureCollection", "features": []}'
        for ld in LAYER_LEVELS:
            with open(os.path.join(self.cache_dir, 'mapillary_%s.geojson' % ld), 'w') as f:
                f.write(defaultContent)
                defLyr = QgsVectorLayer(os.path.join(self.cache_dir, 'mapillary_%s.geojson' % ld),"Mapillary "+ld, "ogr")
                defLyr.setCrs(QgsCoordinateReferenceSystem(4326))
            setattr(self, ld+'Layer', defLyr)

    def transformToWGS84(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsSrc = crcMappaCorrente
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint) # forward transformation: src -> dest

    def download_tiles(self):

        #calculate zoom_level con current canvas extents
        ex = self.iface.mapCanvas().extent()
        wgs84_minimum = self.transformToWGS84(QgsPointXY (ex.xMinimum(),ex.yMinimum()))
        wgs84_maximum = self.transformToWGS84(QgsPointXY (ex.xMaximum(),ex.yMaximum()))
        bounds =(wgs84_minimum.x(),wgs84_minimum.y(),wgs84_maximum.x(),wgs84_maximum.y())
        map_units_per_pixel = (wgs84_maximum.x() - wgs84_minimum.x())/self.iface.mapCanvas().width()
        zoom_level = ZoomForPixelSize(map_units_per_pixel)
        if zoom_level > 14:
            zoom_level = 14

        ranges = getTileRange(bounds, zoom_level)

        #print ("ZOOM_LEVEL", zoom_level, "RANGES", self.actual_ranges, ranges)
        if not self.actual_ranges or not (
                                    ranges[0][0]==self.actual_ranges[0][0] and
                                    ranges[0][1]==self.actual_ranges[0][1] and
                                    ranges[1][0]==self.actual_ranges[1][0] and
                                    ranges[1][1]==self.actual_ranges[1][1]):
            print ("ZOOM_LEVEL", zoom_level, "NEW RANGES", ranges, "LAST RANGES", self.actual_ranges)
            self.actual_ranges = ranges
            x_range = ranges[0]
            y_range = ranges[1]

            overview_features = []
            sequences_features = []
            images_features = []

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
                        res = requests.get(url, proxies=getProxiesConf())
                        print ('MISS',x, y, zoom_level, res, url)
                        if res.status_code == 200:
                            with open(filePathMvt, 'wb') as f:
                                f.write(res.content)
                            print (os.path.getmtime(filePathMvt))

                    if os.path.exists(filePathMvt):
                        if not res:
                            with open(filePathMvt, "rb") as f:
                                mvt = f.read()
                            print ('CACHE', x, y, zoom_level)
                        else:
                            mvt = res.content

                        bounds = mercantile.bounds(x,y,zoom_level)
                        tile_box = (bounds.west,bounds.south,bounds.east,bounds.north)
                        json_data = mapbox_vector_tile.decode(mvt, quantize_bounds=tile_box)
                        if "mapillary-sequence-overview" in json_data:
                            overview_features = overview_features + json_data["mapillary-sequence-overview"]["features"]
                        elif "mapillary-sequences" in json_data:
                            sequences_features = sequences_features + json_data["mapillary-sequences"]["features"]
                        if "mapillary-images" in json_data and zoom_level==14:
                            images_features = images_features + json_data["mapillary-images"]["features"]

            for level in LAYER_LEVELS:
                geojson_file = os.path.join(self.cache_dir, "mapillary_%s.geojson" % level)
                try:
                    QgsProject.instance().removeMapLayer(getattr(self, level+'Layer').id())
                except:
                    pass
                if  locals()[level+'_features']:
                    setattr(self,level,True)
                    geojson = {
                        "type": "FeatureCollection",
                        "features": locals()[level+'_features']
                    }

                    with open(geojson_file, 'w') as outfile:
                        json.dump(geojson, outfile)
                    defLyr = QgsVectorLayer(os.path.join(self.cache_dir, 'mapillary_%s.geojson' % level),"Mapillary " + level, "ogr")
                    defLyr.loadNamedStyle(os.path.join(os.path.dirname(__file__), "res", "mapillary_%s.qml" % level))
                    QgsExpressionContextUtils.setLayerVariable(defLyr, "mapillaryCurrentKey", "noKey")
                    defLyr.setCrs(QgsCoordinateReferenceSystem(4326))
                    QgsProject.instance().addMapLayer(defLyr)
                    QgsProject.instance().layerTreeRoot().findLayer(defLyr.id()).setExpanded(False)
                    setattr(self, level + 'Layer', defLyr)
                else:
                    setattr(self, level, False)

        else:
            pass
            #print ("SAME RANGES")

    def has_overview(self):
        return self.overview

    def has_sequences(self):
        return self.sequences

    def has_images(self):
        return self.images

    def get_overview_layer(self):
        if self.overview:
            self.mapillary_overview_layer = QgsVectorLayer(os.path.join(self.cache_dir, 'mapillary_overview.geojson'), "Mapillary Coverage", "ogr")
            self.mapillary_overview_layer.setCrs(QgsCoordinateReferenceSystem(4326))
        else:
            self.mapillary_overview_layer = None
        return self.mapillary_overview_layer

    def get_coverage_layer(self):
        if self.coverage:
            self.mapillary_coverage_layer = QgsVectorLayer(os.path.join(self.cache_dir, 'mapillary_coverage.geojson'), "Mapillary Coverage", "ogr")
            self.mapillary_coverage_layer.setCrs(QgsCoordinateReferenceSystem(4326))
        else:
            self.mapillary_coverage_layer = None
        return self.mapillary_coverage_layer

    def get_images_layer(self):
        if self.images:
            self.mapillary_images_layer = QgsVectorLayer(os.path.join(self.cache_dir, 'mapillary_images.geojson'), "Mapillary Images", "ogr")
            self.mapillary_images_layer.setCrs (QgsCoordinateReferenceSystem(4326))
        else:
            self.mapillary_images_layer = None
        return self.mapillary_images_layer

    def removeLevels(self):
        for level in LAYER_LEVELS:
            try:
                QgsProject.instance().removeMapLayer(getattr(self, level + 'Layer').id())
            except:
                pass
        self.iface.mapCanvas().refresh()

    def getActiveLevels(self):
        activeLevels = {}
        for level in LAYER_LEVELS:
            if getattr(self,level):
                activeLevels[level] = getattr(self, level+'Layer')
        return activeLevels

    def update_coverage(self):
        self.download_tiles()
        return self.getActiveLevels()
