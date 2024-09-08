# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Z:\dev\go2mapillary\mapillary_explorer_dockwidget_base.ui'
#
# Created: Thu Jan 21 16:37:55 2016
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

class Ui_go2mapillaryDockWidgetBase(object):
    def setupUi(self, go2mapillaryDockWidgetBase):
        go2mapillaryDockWidgetBase.setObjectName(_fromUtf8("go2mapillaryDockWidgetBase"))
        go2mapillaryDockWidgetBase.resize(320, 260)
        self.dockWidgetContents = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dockWidgetContents.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents.setSizePolicy(sizePolicy)
        self.dockWidgetContents.setMinimumSize(QtCore.QSize(320, 240))
        self.dockWidgetContents.setMaximumSize(QtCore.QSize(320, 240))
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setMargin(0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.webView = QWebEngineView(self.dockWidgetContents)
        self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
        self.webView.setObjectName(_fromUtf8("webView"))
        self.gridLayout.addWidget(self.webView, 0, 0, 1, 1)
        go2mapillaryDockWidgetBase.setWidget(self.dockWidgetContents)

        self.retranslateUi(go2mapillaryDockWidgetBase)
        QtCore.QMetaObject.connectSlotsByName(go2mapillaryDockWidgetBase)

    def retranslateUi(self, go2mapillaryDockWidgetBase):
        go2mapillaryDockWidgetBase.setWindowTitle(_translate("go2mapillaryDockWidgetBase", "go2mapillary", None))

