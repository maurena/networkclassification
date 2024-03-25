#
# Base class for general calculations of enrichement angularity, elongation, ...
#
import math as m
from functools import reduce
from PyQt5.QtWidgets import QMessageBox
from qgis.core import Qgis, QgsTask, QgsMessageLog

class baseEnrichment(QgsTask):
    # Constructor
    def __init__(self, description, junctions, channels, saga, debug=False):
        # Data
        self.junctions = junctions
        self.channels = channels
        self.debug = debug
        # Name of fields
        # Unique ID of each segment of all streams
        self.SEGMENT_ID = "SEGMENT_ID"
        #Orden de Strahler del stream
        self.ORDER = "ORDER"
        #ID del nodo
        if saga =='saga':
            self.NODE_ID = "NODE_ID"
        else:
            self.NODE_ID = "ID"

        #Nodo from del stream
        self.NODE_A = "NODE_A"
        #Nodo to del stream
        self.NODE_B = "NODE_B"
        #Longitud del stream
        self.LENGTH = "LENGTH"
        #Tipo de nodo (junction/outlet/spring)
        self.TYPE = "TYPE"
        #Uno de los tipos que puede tomar el nodo
        self.JUNCTION = "Junction"
        self.OUTLET = "Outlet"
        self.SPRING = "Spring"

        #Constante que nos dice cuál es la máxima diferencia que puede haber entre
        #dos ángulos a la hora de calcula la dirección de flujo para que consideremos
        #a la longitud del stream en vez de a dicha dirección.
        self.LIMITE_ANGULOS = 3

        # Create indexes
        self._createIndexes()

        # Init QgsTask
        super().__init__(description, QgsTask.CanCancel)

        self.value = None # Value is none for non-calculated 

    # Create the indexes
    def _createIndexes(self):
        self.junctionsIndexes = {}
        self.channelsIndexesA, self.channelsIndexesB, self.channelsIndexesAB, self.channelsIds = {}, {}, {}, {}
        for i in self.junctions.getFeatures():
            self.junctionsIndexes[i[self.NODE_ID]] = i
        for i in self.channels.getFeatures():
            self.channelsIndexesA[i[self.NODE_A]] = i
            self.channelsIndexesB[i[self.NODE_B]] = i
            self.channelsIds[i[self.SEGMENT_ID]] = i
            if i[self.NODE_A] in self.channelsIndexesAB.keys():
                self.channelsIndexesAB[i[self.NODE_A]].append(i)
            else:
                self.channelsIndexesAB[i[self.NODE_A]] = [i]
            if i[self.NODE_B] in self.channelsIndexesAB.keys():
                self.channelsIndexesAB[i[self.NODE_B]].append(i)
            else:
                self.channelsIndexesAB[i[self.NODE_B]] = [i]

    # Search node in junctions
    def _findNode(self, idNodo):
        return self.junctionsIndexes[idNodo] if idNodo in self.junctionsIndexes.keys() else None

    # Search node in streams    
    def _findStream(self, nodo_a):
        return self.channelsIndexesA[nodo_a] if nodo_a in self.channelsIndexesA.keys() else None

    # Search node B in streams
    def _findStreamB(self, nodo_b):
        return self.channelsIndexesB[nodo_b] if nodo_b in self.channelsIndexesB.keys() else None
    
    # Search all nodes in streams
    def _findStreamAB(self, nodo_id):
        return self.channelsIndexesAB[nodo_id] if nodo_id in self.channelsIndexesAB.keys() else []
    
    # Segment by id
    def _findStreamById(self, id):
        return self.channelsIds[id] if id in self.channelsIds.keys() else None

    # Calculate angle C of triangle (with origin in p1)
    def _calculateTriangle(self, p1, p2, p3):
        a = p1.geometry().asPoint().distance(p2.geometry().asPoint())
        b = p1.geometry().asPoint().distance(p3.geometry().asPoint())
        c = p2.geometry().asPoint().distance(p3.geometry().asPoint())
        
        # Test if triangle is plane
        return 0 if a * b == 0 else m.acos((m.pow(a, 2) + m.pow(b, 2) - m.pow(c, 2)) / (2 * a * b))

    # Get nodes from a list of segments
    # s: List of segments
    def _getNodesFromSegments(self, s):
        nodesA, nodesB = set(i[self.NODE_A] for i in s), set(i[self.NODE_B] for i in s)
        return nodesA.union(nodesB)

    # Filter all junctions only to obtain outlets
    def _getOutlets(self):
        return list(filter(lambda i: i[self.TYPE] == self.OUTLET, list(self.junctions.getFeatures())))

    #Función que devuelve el stream principal según la dirección de flujo
    #y, de no poderse de esta forma, según la longitud.
    def _calculaSegmentoPrincipal(self, mayores, low_stream):
        p1 = self._findNode(low_stream[self.NODE_A])
        p3 = self._findNode(low_stream[self.NODE_B])
        
        # Create list of angles and lengths
        angulos = []
        for i in mayores:
            p2 = self._findNode(i[1][self.NODE_A]) # For angularity
            #p2 = self._findNode(i[self.NODE_A])
            angulo = self._calculateTriangle(p1,p2,p3)
            try:
                angulos.append({'angulo':angulo, 'dif': abs(180 - angulo), 'long': i[1][self.LENGTH], 'feature': i})
            except:
                QgsMessageLog.logMessage(
                    message=f"Angulos: %s" % mayores,
                    level=Qgis.Info,
                )
                return None # Error
        # Filter by min angle
        anguloMin = min([i['angulo'] for i in angulos])
        angulosMin = list(filter(lambda x: x['dif'] == anguloMin, angulos))
        # Determine if more than 2 angles
        if len(angulosMin) > 2:
            # Filter by distance
            distMax = max([i['long'] for i in angulosMin])
            distf = list(filter(lambda x: x['long'] == distMax, angulosMin))
            if len(distf) > 0:
                return distf[0]['feature'] # If there are more than 2 segments with the same length we use the first
            else:
                return None # Error, there is no distances??
        else:
            if len(angulosMin) == 1:
                return angulosMin['feature']
            else:
                return None # Error, no angles

    

    # Calculate network of an outlet. This version is based on increasing the number of nodes and channels in each iteration
    def _calculateConnectedNetwork(self, outlet):
        # Determine first channel (if there is one)
        channel = self._findStreamAB(outlet)
        if (channel is None) or (len(channel) == 0):
            return {'outlet': outlet, 'network': [], 'springs': [outlet]}

        # Create iteration
        oldnet = []
        net = [channel[0]]
        while (len(net) > len(oldnet)):
            oldnet = net
            # Obtain nodes
            nodes = self._getNodesFromSegments(net)
            # Create the set of QgsFeatures segments (no duplicate allowed)
            net = set()
            for i in list(nodes):
                candidates = self._findStreamAB(i)
                net = net.union(candidates)
            # Recreate a list of QgsFeatures
            net = list(net)

        # Determine all springs
        nodes = self._getNodesFromSegments(net)
        nodesFeatures = [self._findNode(i) for i in list(nodes)]
        springs = [j[self.NODE_ID] for j in nodesFeatures if j[self.TYPE] == self.SPRING]
       
        return {'outlet': outlet, 'network': net, 'springs': springs}

    # Calculate all paths from springs to outlet
    def _calculateStreamWays(self, outlet, network = None):
        # First we separate the network tree from all other segments (if it is not provided)
        if network is None:
            network = self._calculateConnectedNetwork(outlet)
        if self.debug:
            QgsMessageLog.logMessage(
                message=f"Outlet: %s\nSprings: %s\nSegments: %s" % (outlet, ";".join(map(str, network['springs'])), ";".join([str(i[self.SEGMENT_ID]) for i in network['network']])),
                level=Qgis.Info,
            )
        # Test if there is network
        if len(network['springs']) == 0:
            return {'outlet': outlet, 'networks': [], 'springs': []}

        # Follow the river from the outlet
        # the final number of paths is equal to the springs
        unordered_network = [i for i in network['network']]
        list_channels = list(filter(lambda i: (i[self.NODE_A] == outlet) or (i[self.NODE_B] == outlet), unordered_network))
        if len(list_channels) == 0:
            # There is no channels
            return {'outlet': outlet, 'networks': [], 'springs': []}

        starting_channel = list_channels[0]
        # Remove starting channel
        unordered_network.remove(starting_channel)
        inprogress = [[starting_channel]]
        ordered_network = []
        while len(unordered_network) > 0:
            # Print out info
            if self.debug:
                QgsMessageLog.logMessage(
                    message=f"progress: [%d / %d / %d]"%(len(unordered_network),len(inprogress), len(ordered_network)),
                    level=Qgis.Info
                )
            # Extract a channel
            test_path = inprogress.pop(0)
            nodes = self._getNodesFromSegments(test_path)
            # Find all connected segments unordered
            connected_segments = [i for i in unordered_network if (i[self.NODE_A] in nodes) or (i[self.NODE_B] in nodes)]
            # Remove found segments from unordered
            unordered_network = [i for i in unordered_network if i not in connected_segments]
            # Clone base path (test_channel) common to all connected segments
            for i in connected_segments:
                cloned = test_path[:]
                cloned.append(i)
                inprogress.append(cloned)

            # If a path has a spring then pass to ordered_network
            for i in inprogress:
                nodes = self._getNodesFromSegments(i)
                nodesF = [self._findNode(j) for j in nodes]
                test_spring = reduce(lambda a, b: a or b, map(lambda a: a[self.TYPE] == self.SPRING, nodesF), False)
                if test_spring:
                    ordered_network.append(i)
            
            # Clear inprogress
            inprogress = [i for i in inprogress if i not in ordered_network]
        # Print out info
        if self.debug:
            for i in ordered_network:
                QgsMessageLog.logMessage(
                    message=f'Ordered network: %s' %(";".join([str(j[self.SEGMENT_ID]) for j in i])),
                    level=Qgis.Info
                )
        # Obtain springs
        springs = []
        for i in ordered_network:
            nodes = self._getNodesFromSegments(i)
            nodesF = [self._findNode(j) for j in nodes]
            nodesSpring = [j for j in nodesF if j[self.TYPE] == self.SPRING]
            for j in nodesSpring:
                if not (j[self.NODE_ID] in springs):
                    springs.append(j[self.NODE_ID])

        return {'outlet': outlet, 'networks': ordered_network, 'springs': springs}

    #
    # QgsTask functions
    #
    def getValue(self):
        if self.value is None:
            self.run()
        return self.value

    def finished(self, result):
        """Postprocessing after the run() method."""
        if self.isCanceled():
            # if it was canceled by the user
            QgsMessageLog.logMessage(
                message=f"Canceled task.",
                level=Qgis.Warning,
            )
            return
        elif not result:
            # if there was an error
            QMessageBox.critical(
                iface.mainWindow(),
                "Computation error",
            )
            return

        QgsMessageLog.logMessage(
            message = f"Success computing the {0}. This {0} is {self.value}",
            level=Qgis.Success,
        )

    def cancel(self):
        # Send message to superclass
        super.cancel()