import requests
import json

def obtener_pokemon(nombre):
    url = f"https://pokeapi.co/api/v2/pokemon/{nombre}"
    respuesta = requests.get(url)
    datos = respuesta.json()

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
        "movimientos": [m["move"]["name"] for m in datos["moves"]],
        "sprite": datos["sprites"]["other"]["official-artwork"]["front_default"],
        "peso": datos["weight"]
    }

    return pokemon

garchomp = obtener_pokemon("garchomp")
print(json.dumps(garchomp, indent=2))