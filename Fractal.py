
import math
from .base import baseEnrichment
import processing
from qgis.core import QgsRectangle, QgsPointXY

# We estimated fractal dimensions following the formula of cubes indicated in:
# "A Fractal Description of Fluvial Networks in Chile: a Geography not as Crazy as Thought"
# doi: https://doi.org/10.20944/preprints202112.0471.v1
# Df=lim(s->0)(log(N(s))/log(1/s))
# where:
#  s is the length of the box (equivalent to original ruler)
#  N(s) is the number of boxes that covers the streams
class Fractal(baseEnrichment):
    def __init__(self, junctions, channels, debug=False):
        # Init baseEnrichemnt
        baseEnrichment.__init__(self, "Fractal Calculation", junctions, channels, debug)

        # Crear el MRE de las cuencas o de los junctions: Channels
        layer_watersheds = processing.run('qgis:minimumboundinggeometry',{'INPUT': channels, 'TYPE': 3, 'OUTPUT': 'TEMPORARY_OUTPUT'} )['OUTPUT']
        ent = layer_watersheds.getFeatures()

        # QgsGeometry of the basin.
        self.basin = ent.geometry()
        # Number of boxes that divide the basin.
        self.numBoxes = 0
        # Array of the boxes on the actual level.
        self.actualBoxes = []
        # Array of the boxes on the next level. 
        self.nextBoxes = []

        # Previous fractal dimension, for stopping the recursive process when
        # the actual fractal dimension minus the previous one is less than an epsilon.
        self.prevFractalDim = 0
        self.epsilon = 0.1
        # Lenght of the side of the boxes.
        self.s = 0

        self.exception = None
        # Init the rest of data
        self.junctions = junctions
        self.channels = channels
        self.debug = debug

    # Function that checks if the box passed as parameter is partial or completely inside the basin.
    def checkBox(self, box):
        xMin = box.xMinimum
        xMax = box.xMaximum
        yMin = box.yMinimum
        yMax = box.yMaximum

        if self.polyBasin.pointDistanceToBoundary(xMin, yMin) >= 0:
            return True
        if self.polyBasin.pointDistanceToBoundary(xMin, yMax) >= 0:
            return True
        if self.polyBasin.pointDistanceToBoundary(xMax, yMax) >= 0:
            return True
        if self.polyBasin.pointDistanceToBoundary(xMax, yMin) >= 0:
            return True

        return False


    # Function that divides the parameter box into four parts and checks if each part is inside the basin.
    # If that happens, the number of boxes gets bigger and we add the box for the next processing.
    def divideBox(self, box):
        xMin = box.xMinimum
        xMax = box.xMaximum
        yMin = box.yMinimum
        yMax = box.yMaximum

        center = box.center()
        xCenter = center.x()
        yCenter = center.y()

        child_1 = QgsRectangle(xMin, yCenter, xCenter, yMax)
        child_2 = QgsRectangle(xCenter, yCenter, xMax, yMax)
        child_3 = QgsRectangle(xMin, yMin, xCenter, yCenter)
        child_4 = QgsRectangle(xCenter, yMin, xMax, yCenter)

        if self.checkBox(child_1):
            self.numBoxes = self.numBoxes + 1
            self.nextBoxes.append(child_1)
        if self.checkBox(child_2):
            self.numBoxes = self.numBoxes + 1
            self.nextBoxes.append(child_2)
        if self.checkBox(child_3):
            self.numBoxes = self.numBoxes + 1
            self.nextBoxes.append(child_3)
        if self.checkBox(child_4):
            self.numBoxes = self.numBoxes + 1
            self.nextBoxes.append(child_4)

    # Function that takes an arbitrary QgsRectangle and returns a "equivalent" square.
    # Basically, when we calculate the bounding box of the basin, is very likely that we will
    # obtain a rectangle, but we need a square because of the definition of the fracal dimension. 
    def convertToSquare(rectangle):
        xMin = rectangle.xMinimum
        xMax = rectangle.xMaximum
        yMin = rectangle.yMinimum
        yMax = rectangle.yMaximum

        point_1 = QgsPointXY(xMin, yMin)
        point_2 = QgsPointXY(xMin, yMax)
        point_3 = QgsPointXY(xMax, yMin)

        # We check what side is larger. 
        a = point_1.distance(point_2)
        b = point_1.distance(point_3)

        # If a > b, then we calculate the new (xMin, yMin) and (xMax, yMax) with trigonometry as follows.
        # The same goes for a < b.
        if a > b:
            l = (a / 2) / math.tan((45 * math.pi) / 180)
            d = l - b / 2
            xMin = xMin - d
            xMax = xMax + d
        if a < b:
            l = (b / 2) / math.tan((45 * math.pi) / 180)
            d = l - a / 2
            yMin = yMin - d
            yMax = yMax + d

        square = QgsRectangle(xMin, yMin, xMax, yMax)
        return square

    # Function that updates the arrays of boxes, in a way in which we "move" to the next level of "the boxes tree".
    def updateBoxes(self):
        self.actualBoxes.clear()
        self.actualBoxes.extend(self.nextBoxes)
        self.nextBoxes.clear()

    # The idea of the process is that we will take the bounding box of the basin and we will transform it into
    # a square, so we will divide the square into four other squares and we will calculate de fractal dimension 
    # each time until the fractal dimension and a previous one are suficiently close so we can say that it
    # has converged.
    def run(self):
        boundingBox = self.basin.boundingBox()
        boundingSquare = self.convertToSquare(boundingBox)

        self.numBoxes = 1
        self.s = abs(boundingSquare.xMaximum - boundingSquare.xMinimum)
        self.actualBoxes.append(boundingSquare)

        self.value = (math.log10(self.numBoxes)) / (math.log10(1 / self.s)) 
        self.prevFractalDim = self.value

        self.numBoxes = 0
        self.divideBox(boundingSquare)
        self.updateBoxes()

        self.value = (math.log10(self.numBoxes)) / (math.log10(1 / self.s)) 

        while(abs(self.value - self.prevFractalDim) > self.epsilon):
            # Test if cancel is pushed (or sent by a message)
            if self.isCanceled():
                return False

            self.s = abs(self.actualBoxes[0].xMaximum - self.actualBoxes[0].xMinimum)
            self.prevFractalDim = self.value
            self.numBoxes = 0

            for box in self.actualBoxes:
                self.divideBox(box)

            self.updateBoxes()
            self.value = (math.log10(self.numBoxes)) / (math.log10(1 / self.s)) 

        return True

    
