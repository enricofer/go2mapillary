import math
import os
import urllib
from shapely.geometry import Polygon
import mapbox_vector_tile
import requests
import math
import json
import mercantile

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

def getZoomLevelold(min_lat,max_lat,min_lon,max_lon):
    mapdisplay = 1
    dist = (6371 * math.acos(math.sin(min_lat / 57.2958) * math.sin(max_lat / 57.2958) +
                             (math.cos(min_lat / 57.2958) * math.cos(max_lat / 57.2958) * math.cos(
                                 (max_lon / 57.2958) - (min_lon / 57.2958)))))
    zoom = math.floor(8 - math.log(1.6446 * dist / math.sqrt(2 * (mapdisplay * mapdisplay))) / math.log(2))
    return zoom

def ZoomForPixelSize(pixelSize):
    "Maximal scaledown zoom of the pyramid closest to the pixelSize."
    for i in range(30):
        print (180 / 256.0 / 2**i)
        if pixelSize > (180 / 256.0 / 2**i):
            return i-1 if i!=0 else 0 # We don't want to scale up

#get the range of tiles that intersect with the bounding box of the polygon 
def getTileRange(polygon, zoom):
    bnds=polygon.bounds
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

#this is your study Area. You need to change the extent here
#In this Example, I've given the boundary of Mumbai
    
#stArea=Polygon([(11.84741,45.39398),(11.86360,45.39328),(11.86223,45.38308),(11.84645,45.38348)])
stArea=Polygon([(11.80,45.47),(11.96,45.47),(11.96,45.32),(11.80,45.32)])

print (stArea.bounds)
zl = ZoomForPixelSize(0.00015838789012617165)
print (zl)
print (getTileRange(stArea,zl))

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


print ('Total number of Tiles: ' + str(tileCount))
count=0
features = []
# Now do the downloading
for y in range(y_range[0], y_range[1] + 1):
    for x in range(x_range[0], x_range[1] + 1):
        #make the URL
        url=getURL(x, y, zl, server_url)
        print (url)

        #urllib.urlretrieve(url,filePathM)
        res = requests.get(url)
        print ("COUNT",count,res.status_code, mercantile.bounds(x,y,zl))
        if res.status_code == 200:
            bounds = mercantile.bounds(x,y,zl)
            tile_box = (bounds.west,bounds.south,bounds.east,bounds.north)
            json_data = mapbox_vector_tile.decode(res.content, quantize_bounds=tile_box)
            features = features + json_data["mapillary-sequences"]["features"]
        '''
        with open(filePathM, 'rb') as infile:
            raw = infile.read()
        json_data = mapbox_vector_tile.decode(raw)
        with open(filePathJ, 'w') as outfile:
            outfile.write(repr(json_data))
        os.remove(filePathM)
        '''
        count=count+1
        print ('finished '+str(count)+'/'+str(tileCount))

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open(os.path.join(os.path.dirname(__file__),"temp","mapillary_coverage.geojson"), 'w') as outfile:
    json.dump(geojson, outfile)