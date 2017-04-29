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

from qgis.core import QgsPoint, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsVectorLayer

SERVER_URL = r"https://d25uarhxywzl1j.cloudfront.net/v0.1/{z}/{x}/{y}.mvt"

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
        self.cache_dir = loc=os.path.join(tempfile.gettempdir(),'temp','tiles')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.actual_ranges = None
        self.images = None

    def transformToWGS84(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsSrc = crcMappaCorrente
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest)
        return xform.transform(pPoint) # forward transformation: src -> dest

    def download_tiles(self):

        #calculate zoom_level con current canvas extents
        ex = self.iface.mapCanvas().extent()
        wgs84_minimum = self.transformToWGS84(QgsPoint (ex.xMinimum(),ex.yMinimum()))
        wgs84_maximum = self.transformToWGS84(QgsPoint (ex.xMaximum(),ex.yMaximum()))
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
            coverage_features = []
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
                            coverage_features = coverage_features + json_data["mapillary-sequences"]["features"]
                        if "mapillary-images" in json_data:
                            images_features = images_features + json_data["mapillary-images"]["features"]

            geojson_overview_file = os.path.join(self.cache_dir, "mapillary_overview.geojson")
            if overview_features:
                self.overview = True
                geojson_overview = {
                    "type": "FeatureCollection",
                    "features": overview_features
                }

                with open(geojson_overview_file, 'w') as outfile:
                    json.dump(geojson_overview, outfile)
            else:
                self.overview = None
                if os.path.exists(geojson_overview_file):
                    os.remove(geojson_overview_file)

            geojson_coverage_file = os.path.join(self.cache_dir, "mapillary_coverage.geojson")
            if coverage_features:
                self.coverage = True
                geojson_coverage = {
                    "type": "FeatureCollection",
                    "features": coverage_features
                }

                with open(geojson_coverage_file, 'w') as outfile:
                    json.dump(geojson_coverage, outfile)
            else:
                self.coverage = None
                if os.path.exists(geojson_coverage_file):
                    os.remove(geojson_coverage_file)

            geojson_images_file = os.path.join(self.cache_dir, "mapillary_images.geojson")
            if zoom_level==14 and images_features:
                self.images = True
                geojson_images = {
                    "type": "FeatureCollection",
                    "features": images_features
                }

                with open(geojson_images_file, 'w') as outfile:
                    json.dump(geojson_images, outfile)
            else:
                self.images = None
                if os.path.exists(geojson_images_file):
                    os.remove(geojson_images_file)
        else:
            pass
            #print ("SAME RANGES")

    def has_overview(self):
        return self.overview

    def has_coverage(self):
        return self.coverage

    def has_images(self):
        return self.images

    def get_overview_layer(self):
        if self.overview:
            self.mapillary_overview_layer = QgsVectorLayer(os.path.join(os.path.dirname(__file__), 'temp', 'mapillary_overview.geojson'), "Mapillary Coverage", "ogr")
            self.mapillary_overview_layer.setCrs(QgsCoordinateReferenceSystem(4326))
        else:
            self.mapillary_overview_layer = None
        return self.mapillary_overview_layer

    def get_coverage_layer(self):
        if self.coverage:
            self.mapillary_coverage_layer = QgsVectorLayer(os.path.join(os.path.dirname(__file__), 'temp', 'mapillary_coverage.geojson'), "Mapillary Coverage", "ogr")
            self.mapillary_coverage_layer.setCrs(QgsCoordinateReferenceSystem(4326))
        else:
            self.mapillary_coverage_layer = None
        return self.mapillary_coverage_layer

    def get_images_layer(self):
        if self.images:
            self.mapillary_images_layer = QgsVectorLayer(os.path.join(os.path.dirname(__file__), 'temp', 'mapillary_images.geojson'), "Mapillary Images", "ogr")
            self.mapillary_images_layer.setCrs (QgsCoordinateReferenceSystem(4326))
        else:
            self.mapillary_images_layer = None
        return self.mapillary_images_layer

    def update_coverage(self):
        self.download_tiles()


'''
#this is your study Area. You need to change the extent here
#In this Example, I've given the boundary of Mumbai
    
#stArea=Polygon([(11.84741,45.39398),(11.86360,45.39328),(11.86223,45.38308),(11.84645,45.38348)])
stArea=Polygon([(11.80,45.47),(11.96,45.47),(11.96,45.32),(11.80,45.32)])

print stArea.bounds
zl = ZoomForPixelSize(0.00015838789012617165)
print zl
print getTileRange(stArea,zl)

loc=os.path.join(os.path.dirname(__file__),'temp','tiles') #You need to change the location for files to download
server_url=r"https://d25uarhxywzl1j.cloudfront.net/v0.1/{z}/{x}/{y}.mvt" #This is the template for the Tile Sets


tileList=[]

ranges=getTileRange(stArea, zl)
x_range=ranges[0]
y_range=ranges[1]

for y in range(y_range[0], y_range[1]+1):
    for x in range(x_range[0], x_range[1]+1):
        if(doesTileIntersects(x,y,zl,stArea)):
            tileList.append((zl, y, x))
tileCount=len(tileList)


print 'Total number of Tiles: ' + str(tileCount)
count=0
features = []
# Now do the downloading
for y in range(y_range[0], y_range[1] + 1):
    for x in range(x_range[0], x_range[1] + 1):
        #make the URL
        url=getURL(x, y, zl, SERVER_URL)
        print url

        #urllib.urlretrieve(url,filePathM)
        res = requests.get(url)
        print ("COUNT",count,res.status_code, mercantile.bounds(x,y,zl))
        if res.status_code == 200:
            bounds = mercantile.bounds(x,y,zl)
            tile_box = (bounds.west,bounds.south,bounds.east,bounds.north)
            json_data = mapbox_vector_tile.decode(res.content, quantize_bounds=tile_box)
            features = features + json_data["mapillary-sequences"]["features"]
        count=count+1
        print 'finished '+str(count)+'/'+str(tileCount)

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open(os.path.join(os.path.dirname(__file__),"temp","mapillary_coverage.geojson"), 'w') as outfile:
    json.dump(geojson, outfile)

'''