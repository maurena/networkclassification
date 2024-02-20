
import math as m
from .base import baseEnrichment

class Angularidad(baseEnrichment):
    def __init__(self, junctions, channels, debug=False):
        baseEnrichment.__init__(self, "Angularity", junctions, channels, debug)

    def sortCriteria(self, p_segment):
        return p_segment[1][self.ORDER]

    # Execute Angularity calculation
    def run(self):
        #Primero, obtenemos los QgsFeature
        featuresJunctions = list(self.junctions.getFeatures())
        featuresChannels = list(self.channels.getFeatures())
    
        Angulos = []
        # Test if there is only one or two channels (angularity is impossible)
        if len(featuresJunctions) < 3:
            self.value = 0
            return True

        #A continuación, vamos a recorrer las junctions y los
        #canales, de forma que obtenemos los puntos p2, p3,...
        #necesarios para obtener la angularidad de la junction i.
        #Una vez los obtenemos, vamos a ir caso por caso, de forma 
        #que el primero es cuando en la junction solo entran dos
        #streams, el segundo será cuando entran más pero podemos
        #obtener el principal a partir del orden de Strahler y
        #el tercero es cuando se necesita de la dirección de flujo
        #y de la longitud.
        l = 0
        for p1 in featuresJunctions:
            # Test if cancel is pushed (or sent by a message)
            if self.isCanceled():
                return False
                
            #Comprobamos que es una junction y no un outlet o un spring.
            if p1[self.TYPE] == self.JUNCTION:
                #Buscamos los nodos from de los streams que acaban en la junction i,
                #de forma que puntos_segments son los nodos junto con su stream
                #asociado.
                puntos_segments = []
                for channel in featuresChannels:
                    nodo = self._findNode(channel[self.NODE_A])
                    if p1[self.NODE_ID] == channel[self.NODE_B]:
                        puntos_segments.append([nodo, channel])
                #Si solo hay dos streams, sencillamente se calcula el ángulo entre
                #ellos tal y como se indica en el paper.
                if(len(puntos_segments) == 2):
                    if self.debug:
                        print("INTERSECCIÓN DE 2 SEGMENTOS")
                        print("ID Nodo Junction: " + str(p1[self.NODE_ID]))
                        for j in puntos_segments:
                            print("ID Nodo: " + str(j[0][self.NODE_ID]))
                    a = p1.geometry().asPoint().distance(puntos_segments[0][0].geometry().asPoint())
                    b = p1.geometry().asPoint().distance(puntos_segments[1][0].geometry().asPoint())
                    c = puntos_segments[1][0].geometry().asPoint().distance(puntos_segments[0][0].geometry().asPoint())
                    angulo = m.acos((m.pow(a, 2) + m.pow(b, 2) - m.pow(c, 2)) / (2 * a * b))
                    if self.debug:
                        print("Angulo: " + str(m.degrees(angulo)))
                        print("")
                    Angulos.append(angulo)
            
                #Si hay más, comprobamos los otros casos.
                elif(len(puntos_segments) > 2):
                    if self.debug:
                        print("INTERSECCIÓN DE MÁS DE 2 SEGMENTOS")
                    #Ordenamos el vector de nodos y segmentos según el orden de Strahler.
                    puntos_segments.sort(reverse=True, key=self.sortCriteria)
                    #Si hay un único segmento con el mayor orden, calculamos los ángulos
                    #entre este y los demás streams.
                    if puntos_segments[0][1][self.ORDER] > puntos_segments[1][1][self.ORDER]:
                        p2 = puntos_segments[0][0]
                        for j in range(len(puntos_segments)):
                            p3 = puntos_segments[j][0]
                            if(p3[self.NODE_ID] != p2[self.NODE_ID]):
                                angulo = self._calculateTriangle(p1, p2, p3)
                                if self.debug:
                                    print(str(m.degrees(angulo)))
                                Angulos.append(angulo)
                    #Si hay varios segmentos con el mismo orden máximo, se calcula el
                    #segmento principal.
                    else:
                        mayores = [puntos_segments[0]]
                        k = 1
                        while (k < len(puntos_segments)) and (puntos_segments[0][1][self.ORDER] == puntos_segments[k][1][self.ORDER]):
                            mayores.append(puntos_segments[k])
                            k = k + 1
                        low_stream = self._findStream(mayores[0][1][self.NODE_A])
                        main_stream = self._calculaSegmentoPrincipal(mayores, low_stream)
                        if main_stream == None:
                            Angulos.append(0)
                        else:
                            p2 = self._findNode(main_stream[1][self.NODE_A])
                            #Una vez lo tenemos, calculamos ángulos con los otros streams
                            for j in range(len(puntos_segments)):
                                p3 = puntos_segments[j][0]
                                if(p3[self.NODE_ID] != p2[self.NODE_ID]):
                                    angulo = self._calculateTriangle(p1, p2, p3)
                                    if self.debug:
                                        print(str(m.degrees(angulo)))
                                    Angulos.append(angulo)
        # Devolvemos angularidad
        if len(Angulos) == 0:
            self.value = 0
            return True
        else:
            self.value = m.degrees(sum(Angulos) / len(Angulos))
            return True
