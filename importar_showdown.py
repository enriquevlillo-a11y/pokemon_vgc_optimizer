"""Importa los Pokémon legales de Regulation M-C desde Pokémon Showdown."""

import argparse
import json
import re
import unicodedata
from pathlib import Path

import json5
import requests

from config import ruta_cache_showdown, ruta_reg_m_c


URL_BASE = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/"
ARCHIVOS_SHOWDOWN = {
    "pokedex": "data/pokedex.ts",
    "formats_data": "data/mods/champions/formats-data.ts",
    "learnsets": "data/mods/champions/learnsets.ts",
}


def descargar_archivos(actualizar=False):
    """Descarga las fuentes que no estén en caché y devuelve sus rutas."""
    rutas = {}
    for clave, ruta_remota in ARCHIVOS_SHOWDOWN.items():
        destino = ruta_cache_showdown(Path(ruta_remota).name)
        rutas[clave] = destino
        if destino.exists() and not actualizar:
            print(f"Usando caché: {destino}")
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        print(f"Descargando {ruta_remota}...")
        respuesta = requests.get(URL_BASE + ruta_remota, timeout=30)
        respuesta.raise_for_status()
        destino.write_bytes(respuesta.content)
    return rutas


def leer_typescript(ruta):
    """Convierte una constante TypeScript de Showdown en un objeto Python."""
    texto = Path(ruta).read_text(encoding="utf-8")
    texto = re.sub(
        r"^export const \w+[^=]*=\s*", "", texto, count=1, flags=re.M
    )
    texto = re.sub(r"([{,]\s*)(\d+):", r'\1"\2":', texto)
    texto = re.sub(r";\s*$", "", texto.strip())
    return json5.loads(texto)


def normalizar_nombre(nombre):
    """Normaliza los nombres visibles como los identificadores del proyecto."""
    nombre = unicodedata.normalize("NFKD", nombre.lower())
    nombre = "".join(
        caracter for caracter in nombre if not unicodedata.combining(caracter)
    )
    nombre = re.sub(r"\s+", "-", nombre)
    nombre = re.sub(r"[^a-z0-9-]", "", nombre)
    return re.sub(r"-+", "-", nombre).strip("-")


def normalizar_id(nombre):
    """Crea un id al estilo Showdown para buscar especies relacionadas."""
    return normalizar_nombre(nombre).replace("-", "")


def _movimientos_para(showdown_id, especie, learnsets):
    battle_only = especie.get("battleOnly")
    if isinstance(battle_only, list):
        battle_only = battle_only[0] if battle_only else None

    candidatos = (
        showdown_id,
        battle_only,
        especie.get("changesFrom"),
        especie.get("baseSpecies"),
    )
    for candidato in candidatos:
        if not candidato:
            continue
        entrada = learnsets.get(normalizar_id(candidato))
        if entrada and "learnset" in entrada:
            return sorted(entrada["learnset"].keys())

    print(f"⚠️  Sin learnset para {especie.get('name', showdown_id)}")
    return []


def generar_datos(pokedex, formats_data, learnsets):
    """Construye la lista y el diccionario con el esquema usado por el proyecto."""
    resultado = {}
    for showdown_id, formato in formats_data.items():
        especie = pokedex.get(showdown_id)
        if not especie:
            print(f"⚠️  {showdown_id} no aparece en pokedex.ts")
            continue
        if formato.get("tier") == "Illegal" or formato.get("isNonstandard"):
            continue
        tags = especie.get("tags", [])
        if "Mythical" in tags or "Restricted Legendary" in tags:
            continue

        nombre = normalizar_nombre(especie["name"])
        habilidades = [
            {
                "nombre": normalizar_nombre(habilidad),
                "es_oculta": str(posicion) == "H",
            }
            for posicion, habilidad in especie.get("abilities", {}).items()
        ]
        stats_origen = especie["baseStats"]
        stats = {
            "hp": stats_origen["hp"],
            "attack": stats_origen["atk"],
            "defense": stats_origen["def"],
            "special-attack": stats_origen["spa"],
            "special-defense": stats_origen["spd"],
            "speed": stats_origen["spe"],
        }
        resultado[nombre] = {
            "nombre": nombre,
            "tipos": [tipo.lower() for tipo in especie["types"]],
            "stats": stats,
            "habilidades": habilidades,
            "movimientos": _movimientos_para(showdown_id, especie, learnsets),
            "peso": especie["weightkg"],
            "showdown_id": showdown_id,
            "especie_base": normalizar_nombre(
                especie.get("baseSpecies", especie["name"])
            ),
            "es_mega": especie.get("forme", "").startswith("Mega")
            or nombre.endswith("-mega")
            or "-mega-" in nombre,
            "objeto_mega": especie.get("requiredItem"),
        }

    resultado = dict(sorted(resultado.items()))
    return list(resultado), resultado


def guardar_datos(permitidos, datos):
    """Escribe los dos archivos de Regulation M-C."""
    for nombre, contenido in (
        ("pokemon_permitidos.json", permitidos),
        ("pokemon_datos.json", datos),
    ):
        ruta = ruta_reg_m_c(nombre)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Generado: {ruta}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actualizar", action="store_true", help="vuelve a descargar la caché"
    )
    args = parser.parse_args()
    rutas = descargar_archivos(args.actualizar)
    permitidos, datos = generar_datos(
        leer_typescript(rutas["pokedex"]),
        leer_typescript(rutas["formats_data"]),
        leer_typescript(rutas["learnsets"]),
    )
    guardar_datos(permitidos, datos)


if __name__ == "__main__":
    main()
