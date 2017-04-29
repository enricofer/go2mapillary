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
from qgis.PyQt.QtWidgets import QAction, QDockWidget
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtNetwork import QNetworkProxy

from qgis.core import (QgsExpressionContextUtils,
                       QgsNetworkAccessManager,
                       QgsProject,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsPoint,
                       QgsVectorLayer,
                       QgsRasterLayer,
                       QgsDataSourceUri,)

#from qgis.utils import *
# Initialize Qt resources from file resources.py
#from .res import resources

# Import the code for the DockWidget
from .mapillary_explorer_dockwidget import go2mapillaryDockWidget
from .mapillary_viewer import mapillaryViewer
from .mapillary_coverage import mapillary_coverage
from .identifygeometry import IdentifyGeometry
from .geojson_request import geojson_request

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

        self.dlg = go2mapillaryDockWidget()

        self.dockwidget=QDockWidget("go2mapillary" , self.iface.mainWindow() )
        self.dockwidget.setObjectName("go2mapillary")
        self.dockwidget.setWidget(self.dlg)
        self.dlg.webView.page().setNetworkAccessManager(QgsNetworkAccessManager.instance())
        self.dlg.webView.page().mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.dlg.webView.page().mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self.canvas.mapToolSet.connect(self.toggleViewer)
        self.viewer = mapillaryViewer(self.dlg.webView)
        self.viewer.messageArrived.connect(self.viewerConnection)
        QgsExpressionContextUtils.setGlobalVariable( "mapillaryCurrentKey","noKey")
        self.mapSelectionTool = None
        self.coverage = mapillary_coverage(self.iface)
        self.mapillaryOverview = None
        self.mapillaryCoverage = None
        self.mapillaryLocations = None

    #--------------------------------------------------------------------------



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
        XYZuri = QgsDataSourceUri()
        XYZuri.setParam("type", "xyz")
        XYZuri.setParam('url', 'http://d2cd86j8eqns9s.cloudfront.net/tiles/{z}/{x}/{y}.png')
        XYZuri.setParam("zmin", "0")
        XYZuri.setParam("zmax", "15")
        layer = QgsRasterLayer(str(XYZuri.encodedUri()), 'Mapillary coverage', 'wms')
        self.coverageLayerId = layer.id()
        print (self.coverageLayerId)
        return layer
        '''
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
        '''

    def removeOverviewLayer(self):
        try:
            QgsProject.instance().removeMapLayer(self.mapillaryOverview.id())
            self.mapillaryOverview = None
        except:
            pass
        self.iface.mapCanvas().refresh()

    def removeCoverageLayer(self):
        try:
            QgsProject.instance().removeMapLayer(self.mapillaryCoverage.id())
            self.mapillaryCoverage = None
        except:
            pass
        self.iface.mapCanvas().refresh()

    def removeLocationsLayer(self):
        try:
            QgsProject.instance().removeMapLayer(self.mapillaryLocations.id())
            self.mapillaryLocations = None
        except:
            pass
        self.iface.mapCanvas().refresh()

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
        self.canvas.mapCanvasRefreshed.connect(self.mapRefreshed)

    def mapRefreshed(self):
        try:
            self.canvas.mapCanvasRefreshed.disconnect(self.mapRefreshed)
        except:
            pass
        self.coverage.update_coverage()
        if not self.mapillaryOverview:
            self.setupOverviewLayer()
        if not self.mapillaryCoverage:
            self.setupCoverageLayer()
        if not self.mapillaryLocations:
            self.setupLocationsLayer()
        self.setLayerStyle()
        self.iface.mapCanvas().refreshAllLayers()

    def setLayerStyle(self):
        if self.mapillaryOverview:
            if self.coverage.has_overview():
                self.mapillaryOverview.triggerRepaint()
            else:
                self.removeOverviewLayer()
        if self.mapillaryCoverage:
            if self.coverage.has_coverage():
                self.mapillaryCoverage.triggerRepaint()
            else:
                self.removeCoverageLayer()
        if self.mapillaryLocations:
            if self.coverage.has_images():
                if self.canvas.scale() < 1000:
                    self.mapillaryLocations.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer0.qml"))
                else:
                    self.mapillaryLocations.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer1.qml"))
                self.mapillaryLocations.triggerRepaint()
            else:
                self.removeLocationsLayer()

    def setupOverviewLayer(self):
        self.mapillaryOverview = self.coverage.get_overview_layer()
        if self.mapillaryOverview:
            print ("setup overview")
            self.mapillaryOverview.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer3.qml"))
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.mapillaryOverview)
            self.mapSelectionTool.geomIdentified.connect(self.changeMapillaryLocation)
            QgsProject.instance().addMapLayer(self.mapillaryOverview)

    def setupCoverageLayer(self):
        self.mapillaryCoverage = self.coverage.get_coverage_layer()
        if self.mapillaryCoverage:
            print ("setup coverage")
            self.mapillaryCoverage.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer2.qml"))
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.mapillaryCoverage)
            self.mapSelectionTool.geomIdentified.connect(self.changeMapillaryLocation)
            QgsProject.instance().addMapLayer(self.mapillaryCoverage)

    def setupLocationsLayer(self):
        self.mapillaryLocations = self.coverage.get_images_layer()
        if self.mapillaryLocations:
            print ("setup locations")
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", "undefined")
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.mapillaryLocations)
            self.mapSelectionTool.geomIdentified.connect(self.changeMapillaryLocation)
            QgsProject.instance().addMapLayer(self.mapillaryLocations)


    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING go2mapillary"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            #if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
            #    self.dockwidget = go2mapillaryDockWidget()

            # connect to provide cleanup on closing of dockwidget
            #self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            #self.setupLayer('')
            self.mapillaryOverview = None
            self.mapillaryCoverage = None
            self.mapillaryLocations = None
            self.canvas.extentsChanged.connect(self.mapChanged)
            self.mapRefreshed()
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
                self.mapRefreshed()

    def changeMapillaryLocation(self, feature):
        #print (('ATTRS', feature.attributes()))
        #print (('KEY', feature[4]))
        if self.mapillaryLocations:
            self.viewer.openLocation(feature['key'])
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", feature['key'])
            self.mapillaryLocations.triggerRepaint()
        elif self.mapillaryCoverage:
            self.viewer.openLocation(feature['ikey'])
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryCoverage, "mapillaryCurrentKey", feature['ikey'])
            self.mapillaryCoverage.triggerRepaint()
        else:
            self.viewer.openLocation(feature['ikey'])
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryOverview, "mapillaryCurrentKey", feature['ikey'])
            self.mapillaryOverview.triggerRepaint()

        
        
