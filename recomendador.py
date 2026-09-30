import json
from motor_tipos import calcular_defensas, TODOS_LOS_TIPOS

def calcular_debilidades_equipo(equipo_defensas):
    debilidades = {}
    for tipo in TODOS_LOS_TIPOS:
        cuenta = sum(1 for d in equipo_defensas.values() if d[tipo] >= 2)
        if cuenta > 0:
            debilidades[tipo] = cuenta
    return debilidades

def puntuar_candidato(defensas_candidato, debilidades_equipo):
    puntuacion = 0
    for tipo, cuenta in debilidades_equipo.items():
        valor = defensas_candidato[tipo]
        peso = cuenta
        if valor == 0:
            puntuacion += 3 * peso
        elif valor <= 0.5:
            puntuacion += 1 * peso
        elif valor >= 2:
            puntuacion -= 1 * peso
    return puntuacion

def recomendar(equipo_nombres, top_n=10):
    with open("data/pokemon_datos.json", "r") as f:
        todos = json.load(f)

    with open("data/uso_pikalytics.json", "r") as f:
        uso = json.load(f)

    # Calcular defensas del equipo actual
    equipo_defensas = {}
    for nombre in equipo_nombres:
        if nombre in todos:
            equipo_defensas[nombre] = calcular_defensas(todos[nombre]["tipos"])

    debilidades = calcular_debilidades_equipo(equipo_defensas)

    print("\nDebilidades del equipo:")
    for tipo, cuenta in sorted(debilidades.items(), key=lambda x: -x[1]):
        print(f"  {tipo}: {cuenta} Pokémon débiles")

    # Puntuar candidatos
    candidatos = []
    for nombre, datos in todos.items():
        if nombre in equipo_nombres:
            continue

        defensas = calcular_defensas(datos["tipos"])
        puntuacion_tipos = puntuar_candidato(defensas, debilidades)

        # Factor de viabilidad — uso real en el meta (0 si no aparece)
        uso_real = uso.get(nombre, 0)

        # Puntuación final: combinamos cobertura y viabilidad
        # Normalizamos el uso a escala 0-5 para que sea comparable
        factor_uso = (uso_real / 100) * 20
        puntuacion_final = puntuacion_tipos + factor_uso

        candidatos.append((nombre, puntuacion_final, puntuacion_tipos, uso_real, datos["tipos"]))

    candidatos.sort(key=lambda x: -x[1])

    print(f"\nTop {top_n} recomendaciones:")
    print(f"{'='*65}")
    print(f"{'Pokémon':<25} {'Tipos':<20} {'Cobertura':>9} {'Uso%':>6} {'Total':>6}")
    print(f"{'='*65}")
    for nombre, total, cobertura, uso_real, tipos in candidatos[:top_n]:
        tipos_str = " / ".join(tipos)
        print(f"{nombre:<25} {tipos_str:<20} {cobertura:>9.1f} {uso_real:>5.1f}% {total:>6.2f}")

    return candidatos[:top_n]

equipo = ["garchomp", "incineroar", "flutter-mane", "raging-bolt", "amoonguss"]
recomendar(equipo)
# Debug temporal
with open("data/uso_pikalytics.json", "r") as f:
    uso = json.load(f)

with open("data/pokemon_datos.json", "r") as f:
    todos = json.load(f)

# ¿Cómo se llaman en cada archivo?
print("\nNombres en uso_pikalytics (top 10):")
for nombre in list(uso.keys())[:10]:
    print(f"  '{nombre}'")

print("\nNombres en pokemon_datos (muestra):")
for nombre in ["incineroar", "flutter-mane", "raging-bolt", "urshifu-rapid-strike"]:
    en_uso = nombre in uso
    en_datos = nombre in todos
    print(f"  '{nombre}' → uso: {en_uso}, datos: {en_datos}")