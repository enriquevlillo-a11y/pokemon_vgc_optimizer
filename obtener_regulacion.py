import requests
import json

def obtener_lista_paldea():
    """Obtiene todos los Pokémon del Pokédex de Scarlet/Violet desde PokéAPI"""
    
    # El Pokédex de Paldea tiene ID 27 en PokéAPI
    url = "https://pokeapi.co/api/v2/pokedex/27"
    respuesta = requests.get(url)
    datos = respuesta.json()
    
    pokemon_list = [entrada["pokemon_species"]["name"] for entrada in datos["pokemon_entries"]]
    
    print(f"Pokémon encontrados en el Pokédex de Paldea: {len(pokemon_list)}")
    print("Primeros 10:", pokemon_list[:10])
    
    return pokemon_list

lista = obtener_lista_paldea()