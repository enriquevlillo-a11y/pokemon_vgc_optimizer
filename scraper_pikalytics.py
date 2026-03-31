import requests
import json
import re
from bs4 import BeautifulSoup

def scraper_pikalytics(formato="gen9vgc2026regf"):
    url = f"https://www.pikalytics.com/pokedex/{formato}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    respuesta = requests.get(url, headers=headers)
    soup = BeautifulSoup(respuesta.text, "html.parser")
    
    uso = {}
    
    # Cada Pokémon aparece como un enlace con su porcentaje
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if f"/pokedex/{formato}/" not in href:
            continue
        
        texto = enlace.get_text(separator=" ").strip()
        
        # Buscar porcentaje en el texto
        match = re.search(r"(\d+\.?\d*)%", texto)
        if not match:
            continue
            
        porcentaje = float(match.group(1))
        
        # Extraer nombre del Pokémon de la URL
        nombre = href.split(f"/pokedex/{formato}/")[-1]
        nombre = nombre.split("?")[0]
        nombre = nombre.replace("%20", "-").lower().strip()
        
        if nombre and porcentaje > 0:
            uso[nombre] = porcentaje
    
    return uso

# Primero instalar beautifulsoup4
# pip3 install beautifulsoup4

uso = scraper_pikalytics()
print(f"Pokémon encontrados: {len(uso)}")
for nombre, porcentaje in sorted(uso.items(), key=lambda x: -x[1])[:20]:
    print(f"  {nombre:<30} {porcentaje}%")

with open("data/uso_pikalytics.json", "w") as f:
    json.dump(uso, f, indent=2)

print("\n✅ Guardado en data/uso_pikalytics.json")