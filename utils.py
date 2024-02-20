# -*- coding: utf-8 -*-
"""
/***************************************************************************
    utils.py
    Utilities to access/create/manipulate QgsVectorLayers

        begin                : 2021-09-17
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Ramón Cruz Blanco / Manuel A. Ureña Cámara
        email                : rcb00029@red.ujaen.es / maurena@ujaen.es
 ***************************************************************************/
"""
from qgis.core import QgsVectorLayer, QgsFeature, QgsWkbTypes

def createMemoryLayer(layer, n, listOfAttributes):
    """
        Create a layer with the same definition of a base layer
        Parameters:
            layer: QgsVectorLayer
            n: Name of the new layer
            listOfAttributes: List of Fields 
        Return:
            QgsVectorLayer empty layer with the same structure of the proposed
    """
    tipo = QgsWkbTypes.displayString(layer.dataProvider().wkbType())
    mem_layer = QgsVectorLayer("%s?crs=%s"%(tipo, layer.crs().authid()), n, "memory")

    mem_layer_data = mem_layer.dataProvider()
    attr = layer.dataProvider().fields().toList()
    attr.extend(listOfAttributes)
    mem_layer_data.addAttributes(attr)
    mem_layer.updateFields()

    return mem_layer

def createMemoryLayerOneEntity(layer, n, e):
    """
        Create a layer with the same definition of a base layer with one feature
        Parameters:
            layer: QgsVectorLayer
            n: Name of the layer
            e: Feature to insert
        Return:
            QgsVectorLayer with one feature with the same structure of the proposed
    """
    tipo = QgsWkbTypes.displayString(layer.dataProvider().wkbType())
    mem_layer = QgsVectorLayer("%s?crs=%s"%(tipo, layer.crs().authid()), n, "memory")

    mem_layer_data = mem_layer.dataProvider()
    attr = layer.dataProvider().fields().toList()
    mem_layer_data.addAttributes(attr)
    mem_layer.updateFields()
    mem_layer_data.addFeature(e)
    mem_layer.updateExtents()
    mem_layer.flushBuffer()

    return mem_layer


def addFeature(layer, geom, attr):
    """
        Add a feature to an existent layer
        Parameters:
            layer: QgsVectorLayer
            geom: Geometry to add
            attr: List of attribute values
        Return:
            QgsVectorLayer empty layer with the same structure of the proposed
    """
    pr = layer.dataProvider()
    f = QgsFeature()
    f.setGeometry(geom)
    f.setAttributes(attr)
    pr.addFeatures([f])
    layer.updateExtents()
    layer.flushBuffer()

def cloneLayer(layer, listOfAttributes):
    """
        Duplicate existent layer adding new attributes
        Parameters:
            layer: QgsVectorLayer
            listOfAttributes: List of Fields 
        Return:
            QgsVectorLayer duplicated including new fields
    """
    feats = [feat for feat in layer.getFeatures()]
    
    mem_layer = QgsVectorLayer("%s?crs=%s"%(layer.storageType(), layer.sourceCrs().postgisSrid()), "duplicated_layer", "memory")

    mem_layer_data = mem_layer.dataProvider()
    attr = layer.dataProvider().fields().toList()
    mem_layer_data.addAttributes(attr.append(listOfAttributes))
    mem_layer.updateFields()
    mem_layer_data.addFeatures(feats)

    return mem_layer_data

#
# Create a buffered version of a feature
#
def bufferFeature(f, d):
    g = f.geometry()
    bg = g.buffer(d, 32)

    nf = QgsFeature(f.fields())
    nf.setGeometry(bg)

    return nf