import requests
import json

def obtener_pokemon(nombre):
    url = f"https://pokeapi.co/api/v2/pokemon/{nombre}"
    respuesta = requests.get(url)
    datos = respuesta.json()

    # Filtramos solo movimientos aprendibles en Scarlet/Violet
    movimientos_sv = []
    for movimiento in datos["moves"]:
        versiones = [v["version_group"]["name"] for v in movimiento["version_group_details"]]
        if "scarlet-violet" in versiones:
            movimientos_sv.append(movimiento["move"]["name"])

    pokemon = {
        "nombre": datos["name"],
        "tipos": [t["type"]["name"] for t in datos["types"]],
        "stats": {s["stat"]["name"]: s["base_stat"] for s in datos["stats"]},
        "habilidades": [
            {
                "nombre": a["ability"]["name"],
                "es_oculta": a["is_hidden"]
            }
            for a in datos["abilities"]
        ],
        "movimientos": movimientos_sv,
        "sprite": datos["sprites"]["other"]["official-artwork"]["front_default"],
        "peso": datos["weight"]
    }

    return pokemon

garchomp = obtener_pokemon("garchomp")
print(json.dumps(garchomp, indent=2))
print(f"\nTotal movimientos: {len(garchomp['movimientos'])}")