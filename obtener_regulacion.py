import requests
import json

def cargar_regulacion(path):
    with open(path, "r") as f:
        return json.load(f)

def obtener_pokemon_pokedex(pokedex_id):
    url = f"https://pokeapi.co/api/v2/pokedex/{pokedex_id}"
    respuesta = requests.get(url)
    datos = respuesta.json()
    return [entrada["pokemon_species"]["name"] for entrada in datos["pokemon_entries"]]

def obtener_lista_regulacion(path_regulacion):
    regulacion = cargar_regulacion(path_regulacion)
    print(f"Cargando regulación: {regulacion['nombre']}")

    ids_pokedex = [27, 28, 29]
    todos = set()
    for pid in ids_pokedex:
        lista = obtener_pokemon_pokedex(pid)
        print(f"  Pokédex {pid}: {len(lista)} Pokémon")
        todos.update(lista)

    # Añadir restringidos (vienen de HOME, no están en los Pokédex)
    restringidos = set(regulacion["restringidos"])
    todos.update(restringidos)

    print(f"Total con restringidos: {len(todos)}")

    # Los míticos no están en ningún Pokédex de SV ni en restringidos
    # así que no hace falta filtrarlos — simplemente no aparecen
    permitidos = sorted(todos)

    print(f"\n✅ Total Pokémon permitidos en {regulacion['nombre']}: {len(permitidos)}")
    print(f"   De los cuales {len(restringidos)} son restringidos (máx {regulacion['max_restringidos']} por equipo)")

    return permitidos

lista = obtener_lista_regulacion("data/regulaciones/reg_g.json")

with open("data/pokemon_reg_g.json", "w") as f:
    json.dump(lista, f, indent=2)

print(f"💾 Lista guardada en data/pokemon_reg_g.json")