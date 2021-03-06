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
import json

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QColor

from qgis.core import (QgsExpressionContextUtils,
                       QgsProject,
                       QgsGeometry,
                       QgsFeature,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsPoint,
                       QgsPointXY,
                       QgsVectorLayer,
                       QgsDataSourceUri,
                       QgsExpression,
                       QgsFeatureRequest,
                       QgsField,
                       QgsFields,
                       QgsVectorFileWriter,
                       QgsWkbTypes,)


from qgis.gui import QgsRubberBand,QgsVertexMarker

SAMPLES_LAYER_NAME = 'Mapillary samples'

FIELDS_TEMPLATE = (
    ("id", "4|10|0", "mapillary tag-marker id"),
    ("type", "10|10|0", "sample type"),
    ("cat", "10|20|0", "user defined category"),
    ("color", "10|10|0", "color"),
    ("key", "10|20|0", "associated mapillary key"),
    ("note", "10|100|0", "user defined note"),
    ("img_coords", "10|100|0", "img coords on mapillary screen"),
)

MLY_COLOR = '#36AF6C'
CURSOR_COLOR = '#2B8E56'

class mapillary_cursor():

    def transformToWGS84(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs()  # get current crs
        crsSrc = crcMappaCorrente
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint)  # forward transformation: src -> dest

    def transformToCurrentSRS(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs()  # get current crs
        crsDest = crcMappaCorrente
        crsSrc = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint)  # forward transformation: src -> dest

    def __init__(self,parentInstance):
        self.parentInstance = parentInstance
        self.iface = parentInstance.iface
        self.mapCanvas = self.iface.mapCanvas()
        self.lineOfSight = QgsRubberBand(self.mapCanvas, QgsWkbTypes.LineGeometry)
        self.sightDirection = QgsRubberBand(self.mapCanvas, QgsWkbTypes.LineGeometry)
        self.pointOfView = QgsVertexMarker(self.mapCanvas)
        self.cursor = QgsVertexMarker(self.mapCanvas)
        self.sightDirection.setColor(QColor(CURSOR_COLOR))
        self.lineOfSight.setColor(QColor(CURSOR_COLOR))
        self.pointOfView.setColor(QColor(CURSOR_COLOR))
        self.cursor.setColor(QColor(CURSOR_COLOR))
        self.lineOfSight.setWidth(2)
        self.sightDirection.setWidth(1)
        self.sightDirection.setLineStyle(Qt.DashLine)
        self.pointOfView.setIconType(QgsRubberBand.ICON_CIRCLE)
        self.cursor.setIconType(QgsRubberBand.ICON_CIRCLE)
        self.pointOfView.setIconSize(20)
        self.cursor.setIconSize(20)
        self.cursor.setPenWidth(2)
        self.pointOfView.setPenWidth(2)
        self.samples_datasource = ''
        self.delete()
        #self.update_ds(self.parentInstance.sample_settings.settings['sample_source'])

    def getSamplesLayer(self, samples_datasource):
        if samples_datasource != 'memory':
            if not os.path.exists(samples_datasource):
                self.create_datasource_from_template(samples_datasource)
            samples_lyr = QgsVectorLayer(samples_datasource, SAMPLES_LAYER_NAME, 'ogr')
        else:
            samples_lyr = QgsVectorLayer("Point?crs=epsg:4326&index=yes", SAMPLES_LAYER_NAME, 'memory')
        self.checkForTemplateFields(samples_lyr)
        return samples_lyr

    def getFieldFromDefinition(self, field_type):
        type_pack = field_type[1].split("|")
        if field_type[2]:
            comment = field_type[2]
        else:
            comment = field_type[0]
        return QgsField(name=field_type[0], type=int(type_pack[0]), len=int(type_pack[1]), prec=int(type_pack[2]),comment=comment)

    def checkForTemplateFields(self, layer):

        layerFieldNamesList = []
        for field in layer.fields().toList():
            layerFieldNamesList.append(field.name())

        for fieldDef in FIELDS_TEMPLATE:
            if not fieldDef[0] in layerFieldNamesList:
                layer.startEditing()
                layer.addAttribute(self.getFieldFromDefinition(fieldDef))
                layer.commitChanges()

    def update_ds(self,ds):
        if self.samples_datasource != ds:
            self.samples_datasource = ds
            self.samplesLayer = self.getSamplesLayer(ds)
            self.samplesLayer.triggerRepaint()
        self.samplesLayer.loadNamedStyle(os.path.join(os.path.dirname(__file__), "res", "mapillary_samples.qml"))
        self.samplesLayer.featureAdded.connect(self.newAddedFeat)


    def create_datasource_from_template(self, datasource):
        fieldSet = QgsFields()
        for fieldDef in FIELDS_TEMPLATE:
            fieldSet.append(self.getFieldFromDefinition(fieldDef))
        writer = QgsVectorFileWriter(datasource, 'UTF-8', fieldSet, QgsWkbTypes.Point, QgsCoordinateReferenceSystem(4326),"ESRI Shapefile")
        if writer.hasError():
            print ("error",writer.errorMessage())
        del writer

    def draw(self,pointOfView_coords,orig_pointOfView_coords,cursor_coords,endOfSight_coords):
        if pointOfView_coords[0]:
            self.cursor.show()
            self.pointOfView.show()
            self.lineOfSight.reset()
            self.sightDirection.reset()
            pointOfView = self.transformToCurrentSRS(QgsPointXY(pointOfView_coords[1],pointOfView_coords[0]))
            cursor = self.transformToCurrentSRS(QgsPointXY(cursor_coords[1],cursor_coords[0]))
            endOfSight = self.transformToCurrentSRS(QgsPointXY(endOfSight_coords[1],endOfSight_coords[0]))
            self.pointOfView.setCenter (pointOfView)
            self.cursor.setCenter (cursor)
            self.lineOfSight.addPoint(pointOfView)
            self.lineOfSight.addPoint(cursor)
            self.sightDirection.addPoint(pointOfView)
            self.sightDirection.addPoint(endOfSight)
            self.cursor.updatePosition()
        else:
            self.delete()

    def delete(self):
        self.cursor.hide()
        self.pointOfView.hide()
        self.lineOfSight.reset()
        self.sightDirection.reset()

    def addSampleLayerToCanvas(self):
        if not QgsProject.instance().mapLayer(self.samplesLayer.id()):
            QgsProject.instance().addMapLayer(self.samplesLayer)
            self.restoreMarkers()


    def sample(self, type, id,key,sample_coords, img_coords=None):
        self.samplesLayer.startEditing()
        samplePoint = QgsPointXY(sample_coords[1],sample_coords[0])
        #sampleDevicePoint = self.iface.mapCanvas().getCoordinateTransform().transform(samplePoint.x(),samplePoint.y())
        self.addSampleLayerToCanvas()
        sampleFeat = QgsFeature(self.samplesLayer.fields())
        sampleFeat['type'] = type
        sampleFeat['id'] = id
        sampleFeat['key'] = key
        if img_coords:
            sampleFeat['img_coords'] = img_coords
        sampleFeat.setGeometry(QgsGeometry.fromPointXY(samplePoint))
        #self.samplesLayer.dataProvider().addFeatures([sampleFeat])
        print ('',self.samplesLayer.addFeature(sampleFeat))
        self.samplesLayer.commitChanges()

    def newAddedFeat(self,featId):
        if featId < 0:
            return
        self.samplesLayer.triggerRepaint()
        if self.parentInstance.sample_settings.settings['auto_open_form']:
            newFeat = self.samplesLayer.getFeature(featId)
            self.parentInstance.samples_form.open(newFeat)

    def getSamplesList(self):
        samples = []
        id = 1
        for feat in self.samplesLayer.getFeatures():
            samples.append({
                "id":id,
                "latLon":{
                    'lat':feat.geometry().asPoint().y(),
                    'lon':feat.geometry().asPoint().x(),
                }
            })

    def restoreTags(self,key):
        exp = QgsExpression('"type" = \'tag\' and "key" = \'%s\'' % key)
        tags = []
        for feat in self.samplesLayer.getFeatures(QgsFeatureRequest(exp)):
            if feat['cat']:
                color = self.parentInstance.sample_settings.settings['categories'][str(feat['cat'])]
            else:
                color = '#ffffff'

            tags.append({
                'id': str(feat['id']),
                'key': str(feat['key']),
                'note': str(feat['note']),
                'cat': str(feat['cat']),
                'color': color,
                'geometry': json.loads(feat['img_coords'])
            })
        return tags

    def editSample(self,type,key,id):
        exp = QgsExpression('"type" = \'%s\' and "key" = \'%s\' and "id" = \'%s\'' % (type,key,id))
        for feat in self.samplesLayer.getFeatures(QgsFeatureRequest(exp)):
            self.parentInstance.samples_form.open(feat)

    def moveMarker(self,key,id,sample_coords):
        exp = QgsExpression('"type" = \'marker\' and "key" = \'%s\' and "id" = \'%s\'' % (key,id))
        for feat in self.samplesLayer.getFeatures(QgsFeatureRequest(exp)):
            samplePoint = QgsPointXY(sample_coords[1], sample_coords[0])
            self.samplesLayer.startEditing()
            self.samplesLayer.changeGeometry(feat.id(),QgsGeometry.fromPointXY(samplePoint))
            self.samplesLayer.commitChanges()
            self.samplesLayer.triggerRepaint()

    def restoreMarkers(self):
        if self.parentInstance.sample_settings.settings['sample_source'] != 'memory':
            exp = QgsExpression('"type" = \'marker\'')
            markersDef = []
            for feat in self.samplesLayer.getFeatures(QgsFeatureRequest(exp)):
                if feat['cat']:
                    color = self.parentInstance.sample_settings.settings['categories'][str(feat['cat'])]
                else:
                    color = '#ffffff'
                markersDef.append({
                    'key': str(feat['key']),
                    'id': str(feat['id']),
                    'color': color,
                    'loc': {
                        'lon': feat.geometry().asPoint().x(),
                        'lat': feat.geometry().asPoint().y()
                    }
                })

            self.parentInstance.viewer.addMarkers(markersDef)
