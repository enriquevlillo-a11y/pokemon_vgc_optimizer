import requests
import json
import time
import os
# Correcciones de nombres para formas especiales
CORRECCIONES = {
    "aegislash": "aegislash-shield",
    "basculin": "basculin-red-striped",
    "darmanitan": "darmanitan-standard",
    "eiscue": "eiscue-ice",
    "gourgeist": "gourgeist-average",
    "indeedee": "indeedee-male",
    "lycanroc": "lycanroc-midday",
    "meowstic": "meowstic-male",
    "mimikyu": "mimikyu-disguised",
    "morpeko": "morpeko-full-belly",
    "necrozma-dawn-wings": "necrozma-dawn-wings",
    "necrozma-dusk-mane": "necrozma-dusk-mane",
    "pumpkaboo": "pumpkaboo-average",
    "toxtricity": "toxtricity-amped",
    "urshifu": "urshifu-single-strike",
    "wishiwashi": "wishiwashi-solo",
    "frillish": "frillish-male",
    "jellicent": "jellicent-male",
    "necrozma-dusk-mane": "necrozma-dusk",
    "necrozma-dawn-wings": "necrozma-dawn",
}
def obtener_pokemon(nombre):
    # Aplicar corrección si existe
    nombre_api = CORRECCIONES.get(nombre, nombre)
    
    url = f"https://pokeapi.co/api/v2/pokemon/{nombre_api}"
    respuesta = requests.get(url)
    
    if respuesta.status_code != 200:
        print(f"  ⚠️  No encontrado: {nombre} (intentado como {nombre_api})")
        return None
    
    datos = respuesta.json()

    movimientos_sv = []
    for movimiento in datos["moves"]:
        versiones = [v["version_group"]["name"] for v in movimiento["version_group_details"]]
        if "scarlet-violet" in versiones:
            movimientos_sv.append(movimiento["move"]["name"])

    return {
        "nombre": nombre,  # guardamos el nombre original, no el de la API
        "nombre_api": nombre_api,
        "tipos": [t["type"]["name"] for t in datos["types"]],
        "stats": {s["stat"]["name"]: s["base_stat"] for s in datos["stats"]},
        "habilidades": [
            {"nombre": a["ability"]["name"], "es_oculta": a["is_hidden"]}
            for a in datos["abilities"]
        ],
        "movimientos": movimientos_sv,
        "sprite": datos["sprites"]["other"]["official-artwork"]["front_default"],
        "peso": datos["weight"]
    }

def descargar_todos(path_lista, path_salida):
    # Cargar lista de Pokémon
    with open(path_lista, "r") as f:
        lista = json.load(f)

    # Si ya existe un archivo de salida, cargar lo que ya tenemos
    if os.path.exists(path_salida):
        with open(path_salida, "r") as f:
            resultado = json.load(f)
        print(f"Reanudando descarga — ya tenemos {len(resultado)} Pokémon")
    else:
        resultado = {}

    pendientes = [p for p in lista if p not in resultado]
    print(f"Pokémon pendientes: {len(pendientes)}")

    for i, nombre in enumerate(pendientes):
        print(f"[{i+1}/{len(pendientes)}] Descargando {nombre}...")
        datos = obtener_pokemon(nombre)
        
        if datos:
            resultado[nombre] = datos
        
        # Guardar progreso cada 50 Pokémon
        if (i + 1) % 50 == 0:
            with open(path_salida, "w") as f:
                json.dump(resultado, f, indent=2)
            print(f"  💾 Progreso guardado ({len(resultado)} Pokémon)")
        
        # Pausa para no saturar la API
        time.sleep(0.3)

    # Guardado final
    with open(path_salida, "w") as f:
        json.dump(resultado, f, indent=2)
    
    print(f"\n✅ Descarga completada — {len(resultado)} Pokémon guardados en {path_salida}")

descargar_todos("data/pokemon_reg_g.json", "data/pokemon_datos.json")