# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ClasificacionRedes
                                 A QGIS plugin
 Este plugin clasifica las redes hídricas por medio de una etapa de enriquecimiento y otra de lógica difusa.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-09-17
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Ramón Cruz Blanco
        email                : rcb00029@red.ujaen.es
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
from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
from PyQt5 import QtCore, QtGui, QtWidgets
# Import the code for the dialog
from .clasificacion_redes_dialog import ClasificacionRedesDialog
import os.path
from qgis.core import QgsLayerTreeGroup, QgsProcessingContext, QgsProcessingFeedback

class ClasificacionRedes:
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
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        self.locale_path = os.path.join(
            self.plugin_dir,
            'i18n')

        if os.path.exists(self.locale_path):
            self.translator = QTranslator()
            locale_path = os.path.join(self.locale_path, 'ClasificacionRedes_' + locale + '.qm')
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Clasificación de redes hídricas')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        # Read context and feedback
        self.context = QgsProcessingContext()
        self.feedback = QgsProcessingFeedback()

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
        return QCoreApplication.translate('ClasificacionRedes', message)


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
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/clasificacion_redes/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Clasificación de redes hídricas'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Clasificación de redes hídricas'),
                action)
            self.iface.removeToolBarIcon(action)

    # Función recursiva para buscar capas en el árbol del proyecto.
    def get_group_layers(self, group):
        print('- group: ' + group.name())
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                # Recursive call to get nested groups
                self.get_group_layers(child)
            else:
                self.dlg.comboBox.addItems([child.name()])

    def run(self):
        """Run method that performs all the real work"""
        

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
        #     # Select language
        #     languages = ("Espanol", "English")
        #     language, ok = QtWidgets.QInputDialog.getItem(None, "Languages", "List of languages", languages, 0, False)
        #     if ok and (language == "English"):
        #         self.locale_path = os.path.join(self.locale_path, 'ClasificacionRedes_ingles.qm')
        #         self.translator.load(self.locale_path)
        #     if language != "Espanol":
        #         QCoreApplication.installTranslator(self.translator)
            # Start dialog
            self.dlg = ClasificacionRedesDialog(self.context, self.feedback)
      
        # Fill combos with layers
        self.dlg.refreshLayers()    

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            pass