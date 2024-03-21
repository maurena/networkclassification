import math as m
from .base import baseEnrichment

class RatioLongitud(baseEnrichment):
    def __init__(self, junctions, channels, saga, debug=False):
        baseEnrichment.__init__(self, "Length Ratio", junctions, channels, saga, debug)

    def sortCriteria(self, canal):
        return canal[self.ORDER]

    #Función que devuelve el siguiente main stream concatenado a canal.
    def obtieneSiguienteStream(self, canal, canales):
        if len(canales) > 1:
            if canales[0][self.ORDER] > canales[1][self.ORDER]:
                return canales[0]
            else:
                mayores = [canales[0]]
                k = 1
                while canales[0][self.ORDER] == canales[k][self.ORDER]:
                    mayores.append(canales[k])
                    k = k + 1
                    if k >= len(canales):
                        break
            
                return self._calculaSegmentoPrincipal(mayores, canal)
        else:
            return canales[0]

    def run(self):
        # New version: The longest channel is selected as the main river, all other connected channels are
        # defined as tributaries.
        # If there is more than one outlet, the final ratio is the mean of all ratios

        # Extract outlets
        outlets = self._getOutlets()
        ratios = []
        #Buscamos las junctions que sean de tipo outlet para ir recorriendo los
        #main streams correspondientes.
        for outlet in outlets:
            # Test if cancel is pushed (or sent by a message)
            if self.isCanceled():
                return False
                
            # Calculate network associated to an outlet
            network = self._calculateConnectedNetwork(outlet[self.NODE_ID])

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
            
            # Determine length of the rest of segments
            other_length = 0
            for path in paths['networks']:
                filtered = [i for i in path if i not in max_path]
                other_length += sum([f[self.LENGTH] for f in filtered])

            # Determine ratios    
            ratios.append(other_length / max_length)

        #Puesto que nuestra cuenca puede tener varios canales inconexos, mostramos
        #por pantalla los ratios de cada canal inconexo.
        if self.debug:
            map(lambda i: print("RATIO: " + i), ratios)

        #return outlets, ratios
        if len(ratios) == 0:
            self.value = 0 # No ratios
            return True
        else:
            self.value = sum(ratios) / len(ratios)
            return True

