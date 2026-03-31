# Tabla de efectividad de tipos
# TABLA[atacante][defensor] = multiplicador
TABLA_TIPOS = {
    "normal":   {"rock": 0.5, "ghost": 0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
    "water":    {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5, "bug": 0.5, "rock": 2, "dragon": 0.5, "steel": 0.5},
    "ice":      {"water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2, "dragon": 2, "steel": 0.5},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2, "ghost": 0, "dark": 2, "steel": 2, "fairy": 0.5},
    "poison":   {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground":   {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
    "flying":   {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2, "fighting": 0.5, "flying": 0.5, "psychic": 2, "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
    "rock":     {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
    "ghost":    {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon":   {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark":     {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy":    {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5},
}

TODOS_LOS_TIPOS = list(TABLA_TIPOS.keys())

def calcular_defensas(tipos):
    """
    Dado una lista de tipos de un Pokémon,
    devuelve un diccionario con el multiplicador de cada tipo atacante.
    """
    resultado = {}

    for atacante in TODOS_LOS_TIPOS:
        multiplicador = 1.0
        for defensor in tipos:
            modificador = TABLA_TIPOS[atacante].get(defensor, 1)
            multiplicador *= modificador
        resultado[atacante] = multiplicador

    return resultado

def analizar_pokemon(nombre, tipos):
    defensas = calcular_defensas(tipos)

    debilidades_x4 = [t for t, v in defensas.items() if v == 4]
    debilidades_x2 = [t for t, v in defensas.items() if v == 2]
    resistencias_x2 = [t for t, v in defensas.items() if v == 0.5]
    resistencias_x4 = [t for t, v in defensas.items() if v == 0.25]
    inmunidades     = [t for t, v in defensas.items() if v == 0]

    print(f"\n{'='*40}")
    print(f"  {nombre.upper()} ({' / '.join(tipos)})")
    print(f"{'='*40}")
    if debilidades_x4:
        print(f"❌ x4:  {', '.join(debilidades_x4)}")
    if debilidades_x2:
        print(f"⚠️  x2:  {', '.join(debilidades_x2)}")
    if resistencias_x2:
        print(f"✅ x0.5: {', '.join(resistencias_x2)}")
    if resistencias_x4:
        print(f"💪 x0.25:{', '.join(resistencias_x4)}")
    if inmunidades:
        print(f"🚫 x0:  {', '.join(inmunidades)}")

    return defensas

# Prueba con Garchomp
analizar_pokemon("garchomp", ["dragon", "ground"])
import json

def analizar_equipo(nombres_equipo):
    """
    Dado una lista de nombres de Pokémon,
    muestra el análisis de tipos de cada uno
    y un resumen de amenazas del equipo completo.
    """
    with open("data/pokemon_datos.json", "r") as f:
        todos = json.load(f)

    print("\n" + "="*40)
    print("  ANÁLISIS DE EQUIPO")
    print("="*40)

    equipo_defensas = {}

    for nombre in nombres_equipo:
        if nombre not in todos:
            print(f"⚠️  {nombre} no encontrado en la base de datos")
            continue
        
        pokemon = todos[nombre]
        defensas = analizar_pokemon(nombre, pokemon["tipos"])
        equipo_defensas[nombre] = defensas

    # Resumen: ¿qué tipos amenazan a TODO el equipo?
    print(f"\n{'='*40}")
    print("  AMENAZAS AL EQUIPO COMPLETO")
    print("="*40)

    for tipo in TODOS_LOS_TIPOS:
        cuenta = sum(1 for d in equipo_defensas.values() if d[tipo] >= 2)
        if cuenta >= 3:
            print(f"⚠️  {tipo}: amenaza a {cuenta}/{len(nombres_equipo)} Pokémon")

# Prueba con un equipo de ejemplo
equipo = ["garchomp", "incineroar", "flutter-mane", "raging-bolt", "urshifu", "amoonguss"]
analizar_equipo(equipo)