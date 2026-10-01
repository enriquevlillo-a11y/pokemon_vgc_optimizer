"""Descarga y transforma las estadísticas mensuales de uso de Smogon."""

import argparse
import json
import re

from config import (
    ruta_cache_smogon,
    ruta_pokemon_datos,
    ruta_regulacion,
    ruta_uso_smogon,
)
from importar_showdown import normalizar_nombre


URL_BASE = "https://www.smogon.com/stats/{mes}/chaos/{formato}-{rating}.json"
BLOQUES = {
    "Abilities": ("habilidades", 10, 1),
    "Items": ("objetos", 10, 1),
    "Moves": ("movimientos", 10, 4),
    "Teammates": ("companeros", 10, 1),
    "Spreads": ("spreads", 5, 1),
}


def descargar_estadisticas(mes, rating, formato):
    """Descarga una estadística y conserva una copia exacta en caché."""
    import requests

    nombre_archivo = f"{mes}-{formato}-{rating}.json"
    ruta_cache = ruta_cache_smogon(nombre_archivo)
    url = URL_BASE.format(mes=mes, formato=formato, rating=rating)
    print(f"Descargando {url}...")
    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()
    ruta_cache.parent.mkdir(parents=True, exist_ok=True)
    ruta_cache.write_bytes(respuesta.content)
    return json.loads(respuesta.content)


def _porcentajes(valores, limite, multiplicador=1, normalizar_claves=True):
    """Convierte recuentos ponderados en porcentajes y conserva el top indicado."""
    valores = {nombre: valor for nombre, valor in valores.items() if nombre.strip()}
    total = sum(float(valor) for valor in valores.values())
    if total <= 0:
        return {}
    ordenados = sorted(valores.items(), key=lambda elemento: -float(elemento[1]))
    resultado = {}
    for nombre, valor in ordenados[:limite]:
        clave = normalizar_nombre(nombre) if normalizar_claves else nombre
        resultado[clave] = float(valor) / total * 100 * multiplicador
    return resultado


def transformar_estadisticas(estadisticas, mes, rating):
    """Adapta el JSON chaos de Smogon al esquema usado por el proyecto."""
    pokemon = {}
    for nombre_smogon, datos in estadisticas.get("data", {}).items():
        uso = float(datos.get("usage", 0)) * 100
        if uso < 0.5:
            continue

        entrada = {"uso": uso}
        for bloque_smogon, (bloque_salida, limite, multiplicador) in BLOQUES.items():
            # Los spreads contienen una naturaleza y cifras separadas por signos;
            # se conserva esa etiqueta, mientras el resto usa ids del proyecto.
            entrada[bloque_salida] = _porcentajes(
                datos.get(bloque_smogon, {}),
                limite,
                multiplicador,
                normalizar_claves=bloque_smogon != "Spreads",
            )
        pokemon[normalizar_nombre(nombre_smogon)] = entrada

    return {
        "info": {
            "mes": mes,
            "rating": rating,
            "combates": estadisticas.get("info", {}).get("number of battles", 0),
        },
        "pokemon": pokemon,
    }


def nombres_desconocidos(estadisticas, pokemon_datos):
    """Devuelve los nombres originales de Smogon ausentes en los datos locales."""
    return sorted(
        nombre
        for nombre in estadisticas.get("data", {})
        if normalizar_nombre(nombre) not in pokemon_datos
    )


def validar_mes(valor):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", valor):
        raise argparse.ArgumentTypeError("el mes debe tener el formato AAAA-MM")
    return valor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mes", required=True, type=validar_mes)
    parser.add_argument("--rating", type=int, default=1760)
    args = parser.parse_args()

    with open(ruta_regulacion(), "r", encoding="utf-8") as archivo:
        regulacion = json.load(archivo)
    formato = regulacion["formato_showdown"]
    estadisticas = descargar_estadisticas(args.mes, args.rating, formato)
    resultado = transformar_estadisticas(estadisticas, args.mes, args.rating)

    ruta_salida = ruta_uso_smogon()
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("\nTop 20 por uso:")
    top = sorted(resultado["pokemon"].items(), key=lambda elemento: -elemento[1]["uso"])
    for nombre, datos in top[:20]:
        print(f"  {nombre:<30} {datos['uso']:.2f}%")

    with open(ruta_pokemon_datos(), "r", encoding="utf-8") as archivo:
        pokemon_datos = json.load(archivo)
    desconocidos = nombres_desconocidos(estadisticas, pokemon_datos)
    print("\nNombres de Smogon ausentes en pokemon_datos.json:")
    if desconocidos:
        for nombre in desconocidos:
            print(f"  {nombre}")
    else:
        print("  Ninguno")
    print(f"\n✅ Guardado en {ruta_salida}")


if __name__ == "__main__":
    main()
