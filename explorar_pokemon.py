import requests

def obtener_pokemon(nombre):
    url = f"https://pokeapi.co/api/v2/pokemon/{nombre}"
    respuesta = requests.get(url)
    datos = respuesta.json()

    print(f"Nombre: {datos['name']}")
    print(f"Tipos: {[t['type']['name'] for t in datos['types']]}")
    print(f"HP: {datos['stats'][0]['base_stat']}")
    print(f"Ataque: {datos['stats'][1]['base_stat']}")
    print(f"Defensa: {datos['stats'][2]['base_stat']}")
    print(f"Ataque Esp: {datos['stats'][3]['base_stat']}")
    print(f"Defensa Esp: {datos['stats'][4]['base_stat']}")
    print(f"Velocidad: {datos['stats'][5]['base_stat']}")

obtener_pokemon("garchomp")