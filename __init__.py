# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go2mapillary
                                 A QGIS plugin
 mapillary explorer
                             -------------------
        begin                : 2016-01-21
        copyright            : (C) 2016 by enrico ferreguti
        email                : enricofer@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load go2mapillary class from file go2mapillary.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .mapillary_explorer import go2mapillary
    return go2mapillary(iface)
