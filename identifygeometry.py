#-----------------------------------------------------------
#
# Plain Geometry Editor is a QGIS plugin to edit geometries
# using plain text editors (WKT, WKB)
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPixmap, QCursor
from qgis.core import QgsVectorLayer, QgsFeature
from qgis.gui import QgsMapToolIdentify

#from cursor import Cursor


class IdentifyGeometry(QgsMapToolIdentify):

    geomIdentified = pyqtSignal(QgsFeature)

    def __init__(self, canvas, targetLayer):
        self.canvas = canvas
        self.targetLayer = targetLayer
        QgsMapToolIdentify.__init__(self, canvas)
        self.setCursor(QCursor())

    def canvasReleaseEvent(self, mouseEvent):
        #results = self.identify(mouseEvent.x(), mouseEvent.y(), self.LayerSelection,[self.targetLayer],self.AllLayers)
        try:
            results = self.identify(mouseEvent.x(), mouseEvent.y(), self.LayerSelection,[self.targetLayer],self.AllLayers)
        except:
            results = []
        if len(results) > 0:
            print (results[0].mFeature.attributes())
            self.geomIdentified.emit(QgsFeature(results[0].mFeature))

