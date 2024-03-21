from .base import baseEnrichment

class Sinusoidad(baseEnrichment):
    def __init__(self, junctions, channels, saga, debug=False):
        baseEnrichment.__init__(self, "Sinuosity", junctions, channels, saga, debug)
        
        #Constante que nos dice cuál es la máxima diferencia que puede haber entre
        #dos ángulos a la hora de calcula la dirección de flujo para que consideremos
        #a la longitud del stream en vez de a dicha dirección.
        self.LIMITE_SINUOSIDAD = 1.5

    def run(self):
        featuresChannels = list(self.channels.getFeatures())
        #Número de segmentos sinuosos.
        nSinuosos = 0   
        for i in range(len(featuresChannels)):
            # # Test if cancel is pushed (or sent by a message)
            if self.isCanceled():
                return False
                
            nodo_A = self._findNode(featuresChannels[i][self.NODE_A])
            nodo_B = self._findNode(featuresChannels[i][self.NODE_B])
            if nodo_A is None or nodo_B is None:
                # One or two of the nodes are not defined in Channels?
                print("NODE_A", featuresChannels[i][self.NODE_A])
                print("NODE_B", featuresChannels[i][self.NODE_B])
                continue

            dist = nodo_A.geometry().asPoint().distance(nodo_B.geometry().asPoint())
            length = featuresChannels[i].geometry().length()
            ratio = length / dist
        
            if(ratio >= self.LIMITE_SINUOSIDAD):
                nSinuosos = nSinuosos + 1
            
        self.value = 0 if len(featuresChannels) == 0 else nSinuosos / len(featuresChannels)
        return True
