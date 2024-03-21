# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ClasificacionRedesDialog
                                 A QGIS plugin
 Este plugin clasifica las redes hídricas por medio de una etapa de enriquecimiento y otra de lógica difusa.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-09-17
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Ramón Cruz Blanco / Manuel A. Ureña Cámara
        email                : rcb00029@red.ujaen.es / maurena@ujaen.es
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

import os, functools

from qgis.PyQt import uic, QtWidgets
from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem

# Imports for the processing of data
from qgis import processing
from qgis.core import QgsProject, QgsProviderRegistry
from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer, QgsVectorLayer, QgsField, QgsRasterLayer, QgsWkbTypes

# General libraries to easy QGIS Processes
from . import utils

# Classes created foreach new attribute of enrichment
from .Elongacion import Elongacion
from .Sinusoidad import Sinusoidad
from .RatioLongitud import RatioLongitud
from .Angularidad import Angularidad
from .Fractal import Fractal

# Classes created for classification
from . import fuzzyclassification

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'clasificacion_redes_dialog_base.ui'))

global SAGAVERSION


class ClasificacionRedesDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ClasificacionRedesDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.calcChannels.clicked.connect(self.calculateChannels)
        self.calcEnrichment.clicked.connect(self.calculateEnrichment)
        self.calcFuzzy.clicked.connect(self.calculateFuzzy)
        self.checkIndividual.clicked.connect(self.individual)
        # self.comboClassifiedWatersheds.currentIndexChanged.connect(self.fillCWFields)
        # self.checkConfidence.clicked.connect(self.confidence)

    # Refresh comboboxes
    def refreshLayers(self):
        # Clear combos
        self.comboDEM.clear()
        self.comboChannels.clear()
        self.comboWatersheds.clear()
        self.comboJunctions.clear()
        self.comboWatershedsEn.clear()
        # self.comboClassifiedWatersheds.clear()

        # Para introducir en el comboBox todas las capas del proyecto.
        root = QgsProject.instance().layerTreeRoot()
        # Select layers by type QgsVectorLayer, QgsRasterLayer
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                # It is a group?
                group = child.findLayers()
                for e in group:
                    if isinstance(e.layer(), QgsVectorLayer):
                        self.comboChannels.addItems([e.name()])
                        self.comboWatersheds.addItems([e.name()])
                        self.comboJunctions.addItems([e.name()])
                        self.comboWatershedsEn.addItems([e.name()])
                        # self.comboClassifiedWatersheds.addItems([e.name()])
                    else:
                        # We suppose Raster Layer for DEM
                        self.comboDEM.addItems([e.name()])
            elif isinstance(child, QgsLayerTreeLayer):
                if isinstance(child.layer(), QgsVectorLayer):
                    self.comboChannels.addItems([child.name()])
                    self.comboWatersheds.addItems([child.name()])
                    self.comboJunctions.addItems([child.name()])
                    self.comboWatershedsEn.addItems([child.name()])
                    # self.comboClassifiedWatersheds.addItems([child.name()])
                else:
                    # We suppose Raster Layer for DEM
                    self.comboDEM.addItems([child.name()])
    
    # Enable/Disable per watershed calculation
    def individual(self):
        self.comboWatersheds.setEnabled(self.checkIndividual.isChecked())

    # Enable/Disable confidence for training
    def confidence(self):
        self.comboCWConfidenceField.setEnabled(self.checkConfidence.isChecked())

    # Fill fields for the classified layer
    def fillCWFields(self):
        # Fill combos
        self.comboCWclassField.clear()
        self.comboCWConfidenceField.clear()
        CWLayer = QgsProject.instance().mapLayersByName(self.comboClassifiedWatersheds.currentText())[0]
        fieldlist = [i.name() for i in CWLayer.fields().toList()]
        self.comboCWclassField.addItems(fieldlist)
        self.comboCWConfidenceField.addItems(fieldlist)

        # Fill table
        self.fieldsCWUsed.clearContents()
        j = 0
        for i in fieldlist:
            self.fieldsCWUsed.insertRow(j)
            self.fieldsCWUsed.setItem(j, 0, QTableWidgetItem(i, QVariant.Char))
            it_3 = QTableWidgetItem()
            it_3.setFlags(it_3.flags() | Qt.ItemIsUserCheckable)
            it_3.setCheckState(Qt.Unchecked)
            self.fieldsCWUsed.setItem(j, 1, it_3)
            it_4 = QTableWidgetItem()
            it_4.setFlags(it_3.flags() | Qt.ItemIsUserCheckable)
            it_4.setCheckState(Qt.Unchecked)
            self.fieldsCWUsed.setItem(j, 2, it_4)
            #self.fieldsCWUsed.setItem(j, 1, QTableWidgetItem(False, QVariant.Bool))
                
    # Functions to execute de different parts of the execution (tabs)
    # Calculate channels using SAGA Algorithms
    def calculateChannels(self):
        global SAGAVERSION # Variable para determinar la versión de SAGA

        # Obtenemos los parámetros que se han pasado por medio de la interfaz.
        slope = self.doubleSpinBox.value()
        umbral = self.spinBox.value()
        #DEMIndex = self.dlg.comboBox.currentIndex()
        DEMName = self.comboDEM.currentText()
        
        # Fill sinks previous to determine channels and junctions
        paramsFill = {'ELEV': DEMName, 'MINSLOPE': slope,'FILLED':'TEMPORARY_OUTPUT','FDIR':'TEMPORARY_OUTPUT','WSHED':'TEMPORARY_OUTPUT'}
        try:
            # Prueba con SAGA 7
            resultsFill = processing.run('saga:fillsinkswangliu', paramsFill)
            SAGAVERSION = 'saga'
        except:
            try:
                resultsFill = processing.run('sagang:fillsinkswangliu', paramsFill)
                SAGAVERSION = 'sagang'
            except:
                print("Error, SAGA no está instalado")  
                SAGAVERSION = None
                return
            
        filled_DEM = resultsFill['FILLED']

        # Determine channels and junctions
        # Layers are inserted into the project by default
        paramsChannels = {'DEM': filled_DEM, 'THRESHOLD': umbral, 
            'DIRECTION':'TEMPORARY_OUTPUT',
            'CONNECTION':'TEMPORARY_OUTPUT',
            'ORDER':'TEMPORARY_OUTPUT',
            'BASIN':'TEMPORARY_OUTPUT',
            'SEGMENTS':'TEMPORARY_OUTPUT',
            'BASINS':'TEMPORARY_OUTPUT',
            'NODES':'TEMPORARY_OUTPUT'}
        try:
            resultsChannels = processing.run('saga:channelnetworkanddrainagebasins', paramsChannels)
        except:
            try:
                resultsChannels = processing.run('sagang:channelnetworkanddrainagebasins', paramsChannels)
            except:
                print("Error, SAGA no está instalado") 
                return

        # Add temporal layers to project
        QgsProject.instance().addMapLayer(QgsRasterLayer(filled_DEM, 'Filled' + DEMName))
        QgsProject.instance().addMapLayer(QgsVectorLayer(resultsChannels['SEGMENTS'], 'Channels' + DEMName))
        QgsProject.instance().addMapLayer(QgsVectorLayer(resultsChannels['NODES'], 'Junctions' + DEMName))
        QgsProject.instance().addMapLayer(QgsVectorLayer(resultsChannels['BASINS'], 'Basins' + DEMName)) # Basins is the vector layer and Basin is the raster layer

        # Refresh combos to include new calculated layers
        self.refreshLayers()
    
    # Add new attributes for enrichment
    def calculateEnrichment(self):
        global SAGAVERSION # Variable para determinar la versión de SAGA
        # Buscamos las capas resultado del algoritmo de procesamiento anterior.
        layer_channels = QgsProject.instance().mapLayersByName(self.comboChannels.currentText())[0]
        # Test if layer has linestring
        if layer_channels.geometryType() != 1:
            QMessageBox.information(None, "Error", "La capa de canales no es de geometría lineal.")
            return
        layer_junctions = QgsProject.instance().mapLayersByName(self.comboJunctions.currentText())[0]
        if layer_junctions.geometryType() != 0:
            QMessageBox.information(None, "Error", "La capa de canales no es de geometría puntual.")
            return
        
        # Two options. Complete watershed (data is showed in the textEdit), per watershed (create a new layer)
        if self.checkIndividual.isChecked():
            # Per watershed
            layer_watersheds = QgsProject.instance().mapLayersByName(self.comboWatersheds.currentText())[0]
        else:
            # One watershed
            # Create convex-hull of channels to calculate only one value
            layer_watersheds = processing.run('qgis:minimumboundinggeometry',{'INPUT': layer_channels, 'TYPE': 3, 'OUTPUT': 'TEMPORARY_OUTPUT'} )['OUTPUT']
        
        if layer_watersheds.geometryType() != 2:
            QMessageBox.information(None, "Error", "La capa de cuencas no es de geometría poligonal.")
            return
        # List of enrichment attributes
        listOfAttributes = [
            {'name':'Angularity', 'check': self.checkBoxAngularidad.checkState(), 'clase': Angularidad},
            {'name':'RatioLength', 'check': self.checkBoxRatioLong.checkState(), 'clase': RatioLongitud},
            {'name':'Sinuosity', 'check': self.checkBoxSinuosidad.checkState(), 'clase': Sinusoidad}, 
            {'name':'Elongation', 'check': self.checkBoxElongacion.checkState(), 'clase': Elongacion},
            {'name':'FractalD', 'check': self.checkBoxFractal.checkState(), 'clase': Fractal}
        ]
        print(listOfAttributes)
        # Test if we have to calculate something
        if not functools.reduce(lambda a, b: a or b, [i['check'] for i in listOfAttributes], False):
            QMessageBox.information(None, "Error", "No se ha seleccionado ningún atributo a enriquecer")
            return

        # Create a temporal memory layer as a copy of the watershed layer
        # adding the adecuate attributes based on the checked elements.
        temp = utils.createMemoryLayer(layer_watersheds, 'enriched', [
            QgsField(name=i['name'], type=QVariant.Double, len=15, prec=7) for i in listOfAttributes if i['check'] == Qt.CheckState.Checked])
        # Iterate over all entities
        ent = layer_watersheds.getFeatures()
        for i in ent:
            # Create a memory layer for the selected feature
            buffered_i = utils.bufferFeature(i, 0.1)
            selected = utils.createMemoryLayerOneEntity(layer_watersheds, 'temporal', buffered_i)
            # Extract channels and junctions inside the entity
            channelsInWatershed = processing.run('qgis:clip',{'INPUT': layer_channels, 'OVERLAY': selected, 'OUTPUT': 'TEMPORARY_OUTPUT'} )['OUTPUT']
            junctionsInWatershed = processing.run('qgis:clip',{'INPUT': layer_junctions, 'OVERLAY': selected, 'OUTPUT': 'TEMPORARY_OUTPUT'} )['OUTPUT']
            # Convert to monopart (extraction creates a multipart)
            channelsInWatershedM = processing.run('native:multiparttosingleparts', {'INPUT': channelsInWatershed, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            junctionsInWatershedM = processing.run('native:multiparttosingleparts', {'INPUT': junctionsInWatershed, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            # Calculate for each element in list of attributes
            res = []
            for j in listOfAttributes:
                # Test if we want to calculate this attribute
                if (j['check'] == Qt.CheckState.Checked):
                    # Test if we have defined the class to calculate de enrichment and
                    if (j['clase'] is None):
                        res.extend([None]) # To keep the order of the attributes we insert a Null data
                    else:
                        try:
                            clase = j['clase'](junctionsInWatershedM, channelsInWatershedM, SAGAVERSION)
                            print(clase)
                            res.extend([clase.getValue()])
                        except:
                            print("Error calculando", j[clase.SEGMENT_ID])

            # Insert new geometry
            attrs = i.attributes()
            attrs.extend(res)
            utils.addFeature(temp, i.geometry(), attrs)
        
        # Add layer to QGIS Project
        QgsProject.instance().addMapLayer(temp)

        # Refresh combos
        self.refreshLayers()

    def calculateFuzzy(self):
        # Apply Fuzzy calculation following:
        # Ling Zhang & Eric Guilbert (2013) Automatic drainage pattern recognition in river networks,
        # International Journal of Geographical Information Science, 27:12, 2319-2342, DOI: 10.1080/13658816.2013.802794
        # Read layer from project
        layer_watersheds = QgsProject.instance().mapLayersByName(self.comboWatershedsEn.currentText())[0]
        # Test if there are enough attributes
        fields = layer_watersheds.fields().names()
        if not ('Angularity' in fields) or not ('Elongation' in fields) or not ('RatioLength' in fields) or not ('Sinuosity' in fields):
            QMessageBox.information(None, "Error", "Campos insuficientes en la capa")
            return
            
        # Create layer to store information
        temp = utils.createMemoryLayer(layer_watersheds, 'fuzzy', 
            [QgsField(name='fuzzyclass', type=QVariant.String, len=25),
            QgsField(name='dendritic', type=QVariant.Double,len=15, prec=4),
            QgsField(name='parallel', type=QVariant.Double,len=15, prec=4),
            QgsField(name='trellis', type=QVariant.Double,len=15, prec=4),
            QgsField(name='rectangular', type=QVariant.Double,len=15, prec=4)
            ])
        # Iterate over all entities
        for i in layer_watersheds.getFeatures():
            # Create class to fuzzy classification
            fuzzy = fuzzyclassification.fuzzyclass(i['Angularity'], i['Sinuosity'], i['RatioLength'], i['Elongation'])
            # Calculate and insert entity
            attr=i.attributes()
            res = fuzzy.clasificacionBorrosa()
            attr.extend([res[0], res[1]['dendritic'], res[1]['parallel'], res[1]['trellis'], res[1]['rectangular']])
            utils.addFeature(temp, i.geometry(), attr)
        
        # Add layer to QGIS Project
        QgsProject.instance().addMapLayer(temp)

        # Refresh combos
        self.refreshLayers()



#
# Sklearn algorithm for classification:
#   - Naive Bayes: Using categorical naive bayes (our results are categories): https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.CategoricalNB.html#sklearn.naive_bayes.CategoricalNB
#                  Parameters required: Alpha: Smoothing parameters (default=1.0)
#   - Neural Network: MultiLayer Perceptron: https://scikit-learn.org/stable/modules/neural_networks_supervised.html
#                  Parameters required: Array of hidden layers, e.g.: (5,2).
#                                       There are different approaches to define the hidden layer, but following this proposal: https://stats.stackexchange.com/questions/181/how-to-choose-the-number-of-hidden-layers-and-nodes-in-a-feedforward-neural-netw
#                                       we will define the hidden layer as the mean of input layer and output layer
#