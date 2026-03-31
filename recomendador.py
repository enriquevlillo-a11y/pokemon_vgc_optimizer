import json
from motor_tipos import calcular_defensas, TODOS_LOS_TIPOS

def calcular_debilidades_equipo(equipo_defensas):
    """
    Devuelve un diccionario tipo -> número de Pokémon del equipo
    que son débiles a ese tipo (x2 o más).
    """
    debilidades = {}
    for tipo in TODOS_LOS_TIPOS:
        cuenta = sum(1 for d in equipo_defensas.values() if d[tipo] >= 2)
        if cuenta > 0:
            debilidades[tipo] = cuenta
    return debilidades

def puntuar_candidato(defensas_candidato, debilidades_equipo):
    """
    Puntúa qué tan bien un candidato cubre las debilidades del equipo.
    """
    puntuacion = 0

    for tipo, cuenta in debilidades_equipo.items():
        valor = defensas_candidato[tipo]
        peso = cuenta  # más puntos si cubre una debilidad más compartida

        if valor == 0:       # inmune
            puntuacion += 3 * peso
        elif valor <= 0.5:   # resiste
            puntuacion += 1 * peso
        elif valor >= 2:     # comparte la debilidad
            puntuacion -= 1 * peso

    return puntuacion

def recomendar(equipo_nombres, top_n=10):
    with open("data/pokemon_datos.json", "r") as f:
        todos = json.load(f)

    # Calcular defensas del equipo actual
    equipo_defensas = {}
    for nombre in equipo_nombres:
        if nombre in todos:
            equipo_defensas[nombre] = calcular_defensas(todos[nombre]["tipos"])

    # Calcular debilidades del equipo
    debilidades = calcular_debilidades_equipo(equipo_defensas)

    print("\nDebilidades del equipo:")
    for tipo, cuenta in sorted(debilidades.items(), key=lambda x: -x[1]):
        print(f"  {tipo}: {cuenta} Pokémon débiles")

    # Puntuar todos los candidatos
    candidatos = []
    for nombre, datos in todos.items():
        if nombre in equipo_nombres:
            continue  # no recomendar los que ya están en el equipo

        defensas = calcular_defensas(datos["tipos"])
        puntuacion = puntuar_candidato(defensas, debilidades)
        candidatos.append((nombre, puntuacion, datos["tipos"]))

    # Ordenar por puntuación
    candidatos.sort(key=lambda x: -x[1])

    print(f"\nTop {top_n} recomendaciones para completar el equipo:")
    print(f"{'='*45}")
    for nombre, puntuacion, tipos in candidatos[:top_n]:
        tipos_str = " / ".join(tipos)
        print(f"  {nombre:<25} ({tipos_str:<20}) puntos: {puntuacion}")

    return candidatos[:top_n]

# Prueba: equipo de 5, ¿quién debería ser el 6º?
equipo = ["garchomp", "incineroar", "flutter-mane", "raging-bolt", "amoonguss"]
recomendar(equipo)