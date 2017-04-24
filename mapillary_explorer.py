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
from qgis.PyQt.QtCore import QObject, QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtNetwork import QNetworkProxy

from qgis.core import (QgsExpressionContextUtils,
                       QgsNetworkAccessManager,
                       QgsProject,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsPoint,
                       QgsVectorLayer,)

#from qgis.utils import *
# Initialize Qt resources from file resources.py
#from .res import resources

# Import the code for the DockWidget
from .mapillary_explorer_dockwidget import go2mapillaryDockWidget
from .mapillary_viewer import mapillaryViewer
from .identifygeometry import IdentifyGeometry
from .geojson_request import geojson_request

#from .py_tiled_layer.tilelayer import TileLayer, TileLayerType
#from .py_tiled_layer.tiles import TileServiceInfo

import os.path
import json


class go2mapillary:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'go2mapillary_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&go2mapillary')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'go2mapillary')
        self.toolbar.setObjectName(u'go2mapillary')

        #print "** INITIALIZING go2mapillary"

        self.pluginIsActive = False
        self.dockwidget = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('go2mapillary', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir,'res','icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'go2mapillary'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        self.dockwidget = go2mapillaryDockWidget()
        self.dockwidget.webView.page().setNetworkAccessManager(QgsNetworkAccessManager.instance())
        self.dockwidget.webView.page().mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.dockwidget.webView.page().mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self.canvas.mapToolSet.connect(self.toggleViewer)
        self.viewer = mapillaryViewer(self.dockwidget.webView)
        self.viewer.messageArrived.connect(self.viewerConnection)
        QgsExpressionContextUtils.setGlobalVariable( "mapillaryCurrentKey","noKey")
        self.mapSelectionTool = None

    #--------------------------------------------------------------------------
        

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING go2mapillary"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD go2mapillary"
        self.removeCoverageLayer()
        self.removeLocationsLayer()
        try:
            self.canvas.extentsChanged.disconnect(self.mapChanged)
        except:
            pass


        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&go2mapillary'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #--------------------------------------------------------------------------

    def getCoverageLayer(self):
            service_info = TileServiceInfo("Mapillary coverage",u"Mapillary coverage", "http://d2cd86j8eqns9s.cloudfront.net/tiles/{z}/{x}/{y}.png")
            service_info.yOriginTop = 1
            #service_info.epsg_crs_id = 3857
            service_info.zmin = 0
            service_info.zmax = 21
            layer = TileLayer(self, service_info, True)
            self.coverageLayerId = layer.id()
            layer.setAttribution("Mapillary coverage \u00A9MAPILLARY")
            #layer.setAttributionUrl("")
            #QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            #toc_root = QgsProject.instance().layerTreeRoot()
            #toc_root.insertLayer(0, layer)
            return layer

    def removeCoverageLayer(self):
            try:
                QgsProject.instance().removeMapLayer(self.mapillaryCoverage.id())
                self.mapillaryCoverage = None
            except:
                pass

    def removeLocationsLayer(self):
            try:
                QgsProject.instance().removeMapLayer(self.mapillaryLocations.id())
                self.mapillaryLocations = None
            except:
                pass

    def toggleViewer(self,mapTool):
        print (("enabled:",self.viewer.isEnabled()))
        print (("CURRENT MAPTOOL:",mapTool))
        if mapTool != self.mapSelectionTool:
            self.viewer.disable()


    def viewerConnection(self, message):
        print (message)
        if message:
            #print tmpPOV
            if message["transport"] == "view":
                print (message)
                self.currentLocation = message
                try:
                    #set a variable to view selected mapillary layer feature as selected
                    QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", self.currentLocation['key'])
                    self.mapillaryLocations.triggerRepaint()
                except:
                    pass
            elif message["transport"] == "focusOn":
                print (("enabled MAPTOOL", self.mapSelectionTool))
                self.viewer.enable()
                self.canvas.setMapTool(self.mapSelectionTool)



    def transformToWGS84(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsSrc = crcMappaCorrente
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest)
        return xform.transform(pPoint) # forward transformation: src -> dest

    def transformToCurrentSRS(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsDest = crcMappaCorrente
        crsSrc = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest)
        return xform.transform(pPoint) # forward transformation: src -> dest

    def mapChanged(self):
        print (("ok",self.canvas.scale()))
        if self.canvas.scale() < 30000:
            self.removeCoverageLayer()
            extents = self.canvas.extent()
            bottomLeft = self.transformToWGS84(QgsPoint(extents.xMinimum(),extents.yMinimum()))
            topRight = self.transformToWGS84(QgsPoint(extents.xMaximum(),extents.yMaximum()))
            url = "http://api.mapillary.com/v1/im/search?min-lat=%s&max-lat=%s&min-lon=%s&max-lon=%s&max-results=500&geojson=true" \
                  % (bottomLeft.y(),topRight.y(),bottomLeft.x(),topRight.x())
            if not self.mapillaryLocations or not(self.mapillaryLocations.id() in QgsProject.instance().mapLayers().keys()):
                self.setupLayer(url)
                QgsProject.instance().addMapLayer(self.mapillaryLocations)
                print ("SETUP locations")
                #self.iface.legendInterface().setLayerExpanded(self.mapillaryLocations, False) no qgis3
            else:
                self.mapillaryLocations.triggerRepaint()
                self.setLayerStyle()


        '''
        else:
            self.removeLocationsLayer()
            if not self.mapillaryCoverage:
                self.mapillaryCoverage = self.getCoverageLayer()
                QgsProject.instance().addMapLayer(self.mapillaryCoverage)
        '''

    def setLayerStyle(self):
        if self.canvas.scale() < 2000:
            self.mapillaryLocations.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer0.qml"))
        else:
            self.mapillaryLocations.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer1.qml"))

    def setupLayer(self,url):
        #self.mapillaryLayer = QgsVectorLayer("http://api.mapillary.com/v1/im/search?min-lat=0&max-lat=0&min-lon=0&max-lon=0&max-results=200&geojson=true","Mapillary Images", "ogr")
        print (("URL:",url))
        if geojson_request.download(url):
            self.mapillaryLocations = QgsVectorLayer(os.path.join(os.path.dirname(__file__),'temp','requested.geojson'), "Mapillary Images", "ogr")
            self.mapillaryLocations.setCrs (QgsCoordinateReferenceSystem(4326))
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", "undefined")
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.mapillaryLocations)
            self.mapSelectionTool.geomIdentified.connect(self.changeMapillaryLocation)
            self.setLayerStyle()


    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING go2mapillary"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = go2mapillaryDockWidget()

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            #self.setupLayer('')
            self.mapillaryCoverage = None
            self.mapillaryLocations = None
            self.canvas.extentsChanged.connect(self.mapChanged)
            self.mapChanged()
            self.canvas.setMapTool(self.mapSelectionTool)

        else:
            # toggle show/hide the widget
            if self.dockwidget.isVisible():
                self.dockwidget.hide()
                self.pluginIsActive = False
                self.removeCoverageLayer()
                self.removeLocationsLayer()
                self.canvas.extentsChanged.disconnect(self.mapChanged)
            else:
                self.dockwidget.show()
                self.canvas.setMapTool(self.mapSelectionTool)
                self.canvas.extentsChanged.connect(self.mapChanged)
                self.mapChanged()

    def changeMapillaryLocation(self, feature):
        print (('ATTRS', feature.attributes()))
        print (('KEY', feature[4]))
        self.viewer.openLocation(feature['key'])
        #set a variable to view selected mapillary layer feature as selected
        QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", feature['key'])
        self.mapillaryLocations.triggerRepaint()

        
        
