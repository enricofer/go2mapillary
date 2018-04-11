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
from .mapillary_coverage import mapillary_coverage, LAYER_LEVELS
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
        #QgsExpressionContextUtils.setGlobalVariable( "mapillaryCurrentKey","noKey")
        QgsExpressionContextUtils.removeGlobalVariable("mapillaryCurrentKey")
        self.mapSelectionTool = None
        self.coverage = mapillary_coverage(self.iface)
        self.last_overview = None
        self.last_sequences = None
        self.last_images = None
        self.lastEnabledLevels = []


    #--------------------------------------------------------------------------



    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD go2mapillary"

        self.removeOverviewLayer()
        self.removeSequencesLayer()
        self.removeImagesLayer()

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
        self.dockwidget.hide()

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
            QgsProject.instance().removeMapLayer(self.coverage.overviewLayer.id())
        except:
            pass
        self.iface.mapCanvas().refresh()

    def removeSequencesLayer(self):
        try:
            QgsProject.instance().removeMapLayer(self.self.coverage.sequencesLayer.id())
        except:
            pass
        self.iface.mapCanvas().refresh()

    def removeImagesLayer(self):
        try:
            QgsProject.instance().removeMapLayer(self.coverage.imagesLayer.id().id())
        except:
            pass
        self.iface.mapCanvas().refresh()

    def toggleViewer(self,mapTool):
        print (("enabled:",self.viewer.isEnabled()))
        print (("CURRENT MAPTOOL:",mapTool))
        if mapTool != self.mapSelectionTool:
            self.viewer.disable()

    def viewerConnection(self, message):
        print ("viewerConnection",message)
        if message:
            #print tmpPOV
            if message["transport"] == "view":
                self.currentLocation = message
                QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", self.currentLocation['key'])
                try:
                    #set a variable to view selected mapillary layer feature as selected
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
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint) # forward transformation: src -> dest

    def transformToCurrentSRS(self, pPoint):
        # transformation from the current SRS to WGS84
        crcMappaCorrente = self.iface.mapCanvas().mapSettings().destinationCrs() # get current crs
        crsDest = crcMappaCorrente
        crsSrc = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        return xform.transform(pPoint) # forward transformation: src -> dest

    def mapChanged(self):
        print("mapChanged")
        self.canvas.mapCanvasRefreshed.connect(self.mapRefreshed)

    def mapRefreshed(self):
        print("mapRefreshed")
        try:
            self.canvas.mapCanvasRefreshed.disconnect(self.mapRefreshed)
        except:
            pass

        overview, sequences, images = self.coverage.update_coverage()

        print ("levels",overview, sequences, images)


        enabledLevels = self.coverage.getActiveLevels()

        disabledLevels = list(set(LAYER_LEVELS) - set(enabledLevels))

        print ("alllevels",LAYER_LEVELS)
        print ("enabledlevels",enabledLevels)
        print ("disabledLayers",disabledLevels)
        print ("lastenabledlevels",self.lastEnabledLevels)

        for level,layer in enabledLevels.items():
            print ("processing ",level)
            QgsExpressionContextUtils.setLayerVariable(layer, "mapillaryCurrentKey", "undefined")
            if not (level == 'sequences' and 'images' in enabledLevels.keys()):
                self.mapSelectionTool = IdentifyGeometry(self.canvas, layer)
                self.mapSelectionTool.geomIdentified.connect(getattr(self,'changeMapillary_'+level))
            enabledLevels[level].triggerRepaint()

        self.lastEnabledLevels = enabledLevels

    '''
        for level in LAYER_LEVELS:
            levelLayer = getattr(self.coverage,level+'Layer')
            if locals()[level]:
                print (level,"levelLayer",levelLayer)
                if locals()[level] and not getattr(self,'last_'+level):
                    QgsExpressionContextUtils.setLayerVariable(levelLayer, "mapillaryCurrentKey","undefined")
                    if self.canvas.scale() < 1000:
                        suff = '1'
                    else:
                        suff = '0'
                    levelLayer.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillary_%s.qml" % level+suff))
                    QgsProject.instance().addMapLayer(levelLayer)
                    QgsProject.instance().layerTreeRoot().findLayer(levelLayer.id()).setExpanded(False)
                    setattr(self, 'last_' + level, True)

                if not locals()[level] and getattr(self,'last_'+level):
                    QgsProject.instance().removeMapLayer(levelLayer.id())

                if locals()[level]:
                    self.mapSelectionTool = IdentifyGeometry(self.canvas, levelLayer)
                    self.mapSelectionTool.geomIdentified.connect(getattr(self,'changeMapillary_'+level))
                    self.coverage.levelLayer.triggerRepaint()

    
        if overview:
            if self.last_overview != overview:
                QgsExpressionContextUtils.setLayerVariable(self.mapillaryOverview, "mapillaryCurrentKey", "undefined")
                self.mapillaryOverview.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer3.qml"))
                QgsProject.instance().addMapLayer(self.mapillaryOverview)
                QgsProject.instance().layerTreeRoot().findLayer(self.mapillaryOverview.id()).setExpanded(False)
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.coverage.overviewLayer)
            self.mapSelectionTool.geomIdentified.connect(self.changeMapillaryOverview)
            self.coverage.overviewLayer.triggerRepaint()
        else:
            try:
                QgsProject.instance().removeMapLayer(self.coverage.overviewLayer.id())
            except:
                pass

        if sequences:
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.coverage.sequencesLayer)
            self.mapSelectionTool.geomIdentified.connect(self.changeMapillarySequence)
            self.mapillaryCoverage.triggerRepaint()
        else:
            try:
                QgsProject.instance().removeMapLayer(self.coverage.sequencesLayer.id())
            except:
                pass

        if images:
            self.mapSelectionTool = IdentifyGeometry(self.canvas, self.coverage.imagesLayer)
            self.mapSelectionTool.geomIdentified.connect(self.self.coverage.imagesLayer)
            if self.canvas.scale() < 1000:
                self.coverage.imagesLayer.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer0.qml"))
            else:
                self.coverage.imagesLayer.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer1.qml"))
            self.mapillaryLocations.triggerRepaint()
        else:
            try:
                QgsProject.instance().removeMapLayer(self.coverage.imagesLayer.id())
            except:
                pass

        self.iface.mapCanvas().refreshAllLayers()

    def setupOverviewLayer(self):
        self.mapillaryOverview = self.coverage.get_overview_layer()
        print ("setup overview 1",self.mapillaryOverview,)
        if self.mapillaryOverview:
            print ("setup overview 2")
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryOverview, "mapillaryCurrentKey", "undefined")
            self.mapillaryOverview.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer3.qml"))
            QgsProject.instance().addMapLayer(self.mapillaryOverview)
            QgsProject.instance().layerTreeRoot().findLayer(self.mapillaryOverview.id()).setExpanded(False)

    def setupCoverageLayer(self):
        self.mapillaryCoverage = self.coverage.get_coverage_layer()
        print ("setup coverage 1",self.mapillaryCoverage,)
        if self.mapillaryCoverage:
            print ("setup coverage")
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryCoverage, "mapillaryCurrentKey", "undefined")
            self.mapillaryCoverage.loadNamedStyle(os.path.join(self.plugin_dir, "res", "mapillaryLayer2.qml"))
            QgsProject.instance().addMapLayer(self.mapillaryCoverage)
            QgsProject.instance().layerTreeRoot().findLayer(self.mapillaryCoverage.id()).setExpanded(False)

    def setupLocationsLayer(self):
        self.mapillaryLocations = self.coverage.get_images_layer()
        print ("setup locations 1",self.mapillaryLocations,)
        if self.mapillaryLocations:
            print ("setup locations")
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryLocations, "mapillaryCurrentKey", "undefined")
            QgsExpressionContextUtils.setLayerVariable(self.mapillaryCoverage, "mapillaryCurrentKey", "undefined")
            QgsProject.instance().addMapLayer(self.mapillaryLocations)
            QgsProject.instance().layerTreeRoot().findLayer(self.mapillaryLocations.id()).setExpanded(False)
    '''

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            #self.setupLayer('')
            self.canvas.extentsChanged.connect(self.mapChanged)
            self.mapRefreshed()
            self.canvas.setMapTool(self.mapSelectionTool)

        else:
            # toggle show/hide the widget
            if self.dockwidget.isVisible():
                self.dockwidget.hide()
                self.pluginIsActive = False
                self.removeOverviewLayer()
                self.removeSequencesLayer()
                self.removeImagesLayer()
                self.canvas.extentsChanged.disconnect(self.mapChanged)
            else:
                self.dockwidget.show()
                self.canvas.setMapTool(self.mapSelectionTool)
                self.canvas.extentsChanged.connect(self.mapChanged)
                self.mapRefreshed()

    def changeMapillary_images(self, feature):
        print("changeMapillary_images")
        self.viewer.openLocation(feature['key'])
        QgsExpressionContextUtils.setLayerVariable(self.coverage.imagesLayer, "mapillaryCurrentKey", feature['key'])
        QgsExpressionContextUtils.setLayerVariable(self.coverage.sequencesLayer, "mapillaryCurrentKey", feature['skey'])
        self.mapillaryLocations.triggerRepaint()
        self.mapillaryCoverage.triggerRepaint()

    def changeMapillary_sequences(self, feature):
        print("changeMapillary_sequences")
        self.viewer.openLocation(feature['ikey'])
        QgsExpressionContextUtils.setLayerVariable(self.coverage.sequencesLayer, "mapillaryCurrentKey", feature['key'])
        self.mapillaryCoverage.triggerRepaint()

    def changeMapillary_overview(self, feature):
        print("changeMapillary_overview")
        self.viewer.openLocation(feature['ikey'])
        QgsExpressionContextUtils.setLayerVariable(self.coverage.overviewLayer, "mapillaryCurrentKey", feature['key'])
        self.mapillaryOverview.triggerRepaint()

        
        
