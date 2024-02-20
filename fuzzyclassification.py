import numpy as np
from functools import reduce
# try:
#     # Import external versión of skfuzzy
#     import skfuzzy as fuzz
#     from skfuzzy import control as ctrl
# except:
#     import subprocess
#     try:
#         # Install from the network (from SmartMap Plugin)
#         library_version = 'scikit-learn==0.24.2'
#         print('Installing scikit-learn')
#         subprocess.check_call(["python", '-m', 'pip', 'install', '--user', library_version]) #install pkg 
#         print('Scikit-learn installed with sucess. version: ' + library_version)
#     except:
#         # Install from ZIP
#         pass

# New versión with builtin scikit-fuzzy (0.42)
from .skfuzzy import membership
from .skfuzzy.fuzzymath import interp_membership
from .skfuzzy.defuzzify import defuzz

# Clase que abstrae toda la parte de clasificación con lógica borrosa.
# Vamos a usar las cuatro características que nos indica el paper para
# realizar la clasificación.
class fuzzyclass:
    def __init__(self, angularidad, sinuosidad, ratioLongitud, elongacion, debug=False):
        # Las variables de entrada, o antecedentes en terminología de lógica
        # borrosa.
        self.angularidad = angularidad #alfa
        self.sinuosidad = sinuosidad #beta
        self.ratioLongitud = ratioLongitud #gamma
        self.elongacion = elongacion #delta

        # Debug mode
        self.debug = debug
        
        # Los outputs, o consecuentes en terminología de lógica borrosa.
        # Se tratan de porcentajes de coincidencia de la red con una de estas
        # tipologías.
        self.dendritica = 0
        self.paralela = 0
        self.trellis = 0
        self.rectangular = 0
        
        # Universos de los antecedentes, esto es, los dominios de los valores
        # que pueden coger.
        self.universo_alfa = np.arange(0, 180.1, 0.1)
        self.universo_beta = np.arange(0, 1.0001, 0.0001)
        self.universo_gamma = np.arange(0, 3.0001, 0.0001)
        self.universo_delta = np.arange(0, 4.0001, 0.0001)
        
        # Universo de la salida, que es (0, 4)
        self.universo_output = np.arange(0, 4.0001, 0.0001)
        
        # Parámetros para las funciones de membresía.
        # Para la función z(alfa; a, b) para alfa IS Very Acute (en grados)
        self.a_VERY_ACUTE = 30
        self.b_VERY_ACUTE = 60
        
        # Para la función z(alfa; a, b) para alfa IS Acute  (en grados)
        self.a_ACUTE = 45
        self.b_ACUTE = 90
        
        # Para la función g(alfa; sigma, m) para alfa IS Right (en grados)
        self.sigma_RIGHT = 10
        self.media_RIGHT = 90
        
        # Parámetros para la función s(beta; a, b) para beta IS Bended
        self.a_BENDED = 0
        self.b_BENDED = 1
        
        # Parámetros para la función z(gamma; a, b) para gamma IS Short
        self.a_SHORT = 0
        self.b_SHORT = 1
        
        # Parámetros para la función s(gamma; a, b) para gamma IS Long
        self.a_LONG = 0
        self.b_LONG = 1
        
        # Parámetros para la función z(delta; a, b) para delta IS Broad
        self.a_BROAD = 1
        self.b_BROAD = 3
        
        # Parámetros para la función s(delta; a, b) para delta IS Elongated
        self.a_ELONGATED = 1
        self.b_ELONGATED = 3

    def clasificacionBorrosa(self):
        # Establecemos las funciones de membresía para cada uno de los términos
        # de los conjuntos difusos y para las salidas.
        alfa_very_acute = membership.zmf(self.universo_alfa, self.a_VERY_ACUTE, self.b_VERY_ACUTE)
        alfa_acute = membership.zmf(self.universo_alfa, self.a_ACUTE, self.b_ACUTE)
        alfa_right = membership.gaussmf(self.universo_alfa, self.media_RIGHT, self.sigma_RIGHT)
        
        beta_bended = membership.smf(self.universo_beta, self.a_BENDED, self.b_BENDED)
        
        gamma_short = membership.zmf(self.universo_gamma, self.a_SHORT, self.b_SHORT)
        gamma_long = membership.smf(self.universo_gamma, self.a_LONG, self.b_LONG)
        
        delta_broad = membership.zmf(self.universo_delta, self.a_BROAD, self.b_BROAD)
        delta_elongated = membership.smf(self.universo_delta, self.a_ELONGATED, self.b_ELONGATED)
        
        # base 
        base = {
            'dendritic': membership.trimf(self.universo_output, [0, 0.5, 1]),
            'parallel': membership.trimf(self.universo_output, [1, 1.5, 2]),
            'trellis': membership.trimf(self.universo_output, [2, 2.5, 3]),
            'rectangular': membership.trimf(self.universo_output, [3, 3.5, 4])
        }
        
        # Calculamos la membresía para cada una de las entradas que le suplimos.
        alfa_very_acute_degree = interp_membership(self.universo_alfa, alfa_very_acute, self.angularidad)
        alfa_acute_degree = interp_membership(self.universo_alfa, alfa_acute, self.angularidad)
        alfa_right_degree = interp_membership(self.universo_alfa, alfa_right, self.angularidad)
        
        beta_bended_degree = interp_membership(self.universo_beta, beta_bended, self.sinuosidad)
        
        gamma_short_degree = interp_membership(self.universo_gamma, gamma_short, self.ratioLongitud)
        gamma_long_degree = interp_membership(self.universo_gamma, gamma_long, self.ratioLongitud)
        
        delta_broad_degree = interp_membership(self.universo_delta, delta_broad, self.elongacion)
        delta_elongated_degree = interp_membership(self.universo_delta, delta_elongated, self.elongacion)
        
        # Reglas de la lógica difusa.
        rules = {
            # IF (alfa IS acute) AND (delta IS broad) THEN pattern is dendritic
            'dendritic': np.fmin(alfa_acute_degree, delta_broad_degree),

            # IF (alfa IS very acute) AND NOT (beta IS bended) AND (gamma IS long) AND (delta IS elongated) THEN pattern IS parallel
            'parallel': np.fmin(np.fmin(alfa_very_acute_degree, 1 - beta_bended_degree), np.fmin(gamma_long_degree, delta_elongated_degree)),
        
            # IF (alfa IS right) AND NOT (beta IS bended) AND (gamma IS short) AND (delta IS elongated) THEN pattern IS trellis
            'trellis': np.fmin(np.fmin(alfa_right_degree, 1 - beta_bended_degree), np.fmin(gamma_short_degree, delta_elongated_degree)),
        
            # IF (alfa IS right) AND (beta IS bended) THEN pattern IS rectangular
            'rectangular': np.fmin(alfa_right_degree, beta_bended_degree)
        }
        
        # Fase de inferencia. Realizamos un truncamiento (min) a la función de membresía de los consecuentes,
        # a la altura de el valor obtenido en cada una de las reglas difusas, de forma que obtenemos como
        # resultado un conjunto difuso truncado.
        activation = {k: np.fmin(v, base[k]) for (k,v) in rules.items()}
        maxactivation = {k: max(v) for (k,v) in activation.items()}
        
        # Fase de agregación. Con una función max, obtenemos un conjunto difuso resultado de agregar los
        # conjuntos obtenidos de la anterior fase.
        aggregationMax = max(maxactivation, key=maxactivation.get)

        if self.debug:
            # Fase de agregación. Con una función max, obtenemos un conjunto difuso resultado de agregar los
            # conjuntos obtenidos de la anterior fase.
            aggregation = reduce(lambda a, b: np.fmax(a, b), activation, activation['dendritic'])
            # Defuzzification
            pattern_centroid = defuzz(self.universo_output, aggregation, 'centroid')
            pattern_bisector = defuzz(self.universo_output, aggregation, 'bisector')
            pattern_mom = defuzz(self.universo_output, aggregation, "mom")
            pattern_som = defuzz(self.universo_output, aggregation, "som")
            pattern_lom = defuzz(self.universo_output, aggregation, "lom")

            # Print results
            print(pattern_centroid)
            print(pattern_bisector)
            print(pattern_mom)
            print(pattern_som)
            print(pattern_lom)
        # Remember to convert maxactivation to base float type of Python (actually is a numpy type)
        return [aggregationMax, {k: float(v) for (k,v) in maxactivation.items()}]
        
# Test
if __name__ == "__main__":
    difusa = fuzzyclass(81.14, 0.0149, 0.74, 3.17)
    difusa.clasificacionBorrosa()