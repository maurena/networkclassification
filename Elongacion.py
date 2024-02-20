
import math as m
from .base import baseEnrichment
from qgis.core import QgsGeometry

class Elongacion(baseEnrichment):
    def __init__(self, junctions, channels, debug=False):
        baseEnrichment.__init__(self, "Elongation", junctions, channels, debug)

        #Constante que nos dice cuál es la máxima diferencia que puede haber entre
        #dos ángulos a la hora de calcula la dirección de flujo para que consideremos
        #a la longitud del stream en vez de a dicha dirección.
        self.LIMITE_ANGULOS = 3
    
    #Función que nos devuelve la orientación de una recta dados dos puntos.
    def _orientacion(self, puntoA, puntoB):
        return None if puntoB.x() == puntoA.x() else (puntoB.y() - puntoA.y()) / (puntoB.x() - puntoA.x())

    #Devuelve el ángulo entre dos líneas dadas por sus puntos.
    def _anguloDosLineas(self, puntoA1, puntoB1, puntoA2, puntoB2):
        m1 = self._orientacion(puntoA1, puntoB1)
        m2 = self._orientacion(puntoA2, puntoB2)
        
        #Vamos a usar la fórmula tan(alfa) = |(m2 - m1) / (1 + m2m1)|
        #para calcular el ángulo de las dos rectas
        return None if (m1 is None) or (m2 is None) else m.atan(abs((m2 - m1) / (1 + m2 * m1)))

    
    #Función que calcula la elongación dado el AABB. El cálculo con respecto
    #al MBR y al Convex Hull no se realiza por el momento.
    def run(self):
        #Lo que vamos a hacer es obtener la geometría de cada canal entero,
        #con su main stream y sus afluentes, de manera que podamos calcular el
        #AABB de dicho canal. Para ello, recorremos las junctions y nos paramos
        #en cada outlet, para poder recorrer el main stream y sus afluentes 
        #desde dicho outlet.
        outlets, elongaciones = self._getOutlets(), []
        for outlet in outlets:
            # Test if cancel is pushed (or sent by a message)
            if self.isCanceled():
                return False
                
            # Calculate network associated to an outlet
            network = self._calculateConnectedNetwork(outlet[self.NODE_ID])
            if len(network['network']) == 0:
                # No network determined
                print ('No network from', outlet[self.NODE_ID])
                continue

            # Create a Geometry Collection to determine Minimum Oriented Bounding Box
            red = QgsGeometry(network['network'][0].geometry())
            for s in network['network']:
                red = red.combine(s.geometry())
            aabb = red.orientedMinimumBoundingBox()
            vertices = list(aabb[0].vertices())

            # Determine the longest pathways as the general orientation of the network
            paths = self._calculateStreamWays(outlet[self.NODE_ID], network)
            if len(paths['springs']) == 0:
                continue # Error, this outlet has no network?
            max_length, max_path = 0, None
            for path in paths['networks']:
                length = sum([f[self.LENGTH] for f in path])
                if length > max_length:
                    max_length = length
                    max_path = path
            if max_length == 0:
                # Error, this path has no max distance? We ignore it
                continue

            # Get the spring
            spring = list(filter(lambda i: i[self.TYPE] == self.SPRING, [self._findNode(n) for n in self._getNodesFromSegments(max_path)]))[0]
            # Define the line from spring to outlet
            voutlet, vspring = list(outlet.geometry().vertices())[0], list(spring.geometry().vertices())[0]
            channel = self._orientacion(voutlet, vspring)

            # Define the lines of the oriented rectangle
            mbr1, mbr2 = self._orientacion(vertices[1], vertices[0]), self._orientacion(vertices[2], vertices[1])
            if mbr1 is None or mbr2 is None:
                # No orientation
                continue

            # Define the two distances of the oriented rectangles
            d1, d2 = vertices[0].distance(vertices[1]), vertices[1].distance(vertices[2])
            
            # Define the difference (if distances are greater than 0)
            if (d1 == 0) or (d2 == 0):
                # One segment channel, not useful
                continue
            else:
                if abs(channel - mbr1) < abs(channel - mbr2):
                    elongaciones.append(d1 / d2)
                else:
                    elongaciones.append(d2 / d1)
                if self.debug:
                    print("RATIO (Outlet: " + str(outlet[self.NODE_ID]) + "): " + str(elongaciones[-1]))
               
        # Return the mean of the ratios of all outlets inside watershed (if there are more than one)
        if len(elongaciones) == 0:
            self.value = 0
            return True
        else:
            self.value = 0 if len(elongaciones) == 0 else sum(elongaciones) / len(elongaciones)
            return True
