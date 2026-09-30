import json
from config import ruta_pokemon_datos, ruta_uso_pikalytics, ruta_uso_smogon
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


def cargar_uso():
    """Carga la mejor fuente de uso disponible sin impedir la recomendación."""
    ruta_smogon = ruta_uso_smogon()
    if ruta_smogon.exists():
        with open(ruta_smogon, "r", encoding="utf-8") as archivo:
            return {
                nombre: datos["uso"]
                for nombre, datos in json.load(archivo).get("pokemon", {}).items()
            }

    ruta_pikalytics = ruta_uso_pikalytics()
    if ruta_pikalytics.exists():
        with open(ruta_pikalytics, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    print(
        "⚠️  No se encontró uso_smogon.json ni uso_pikalytics.json; "
        "se usará uso 0 para todos."
    )
    return {}

def recomendar(equipo_nombres, top_n=10):
    with open(ruta_pokemon_datos(), "r") as f:
        todos = json.load(f)

    uso = cargar_uso()

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

def main():
    equipo = ["garchomp", "incineroar", "flutter-mane", "raging-bolt", "amoonguss"]
    recomendar(equipo)


if __name__ == "__main__":
    main()
