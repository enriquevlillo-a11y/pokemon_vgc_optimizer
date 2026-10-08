"""Descarga y transforma las estadisticas mensuales de uso de Smogon."""

import argparse
import json
import re

from config import ruta_cache_smogon, ruta_pokemon_datos, ruta_regulacion, ruta_uso_smogon
from importar_showdown import normalizar_nombre


URL_BASE = "https://www.smogon.com/stats/{mes}/chaos/{formato}-{rating}.json"
EQUIVALENCIAS_BASE = {"floette": "floette-eternal", "meowstic-f": "meowstic"}
SUFIJO_MEGA = re.compile(r"-mega(?:-[xy z])?$".replace(" ", ""))


def nombre_base(nombre):
    """Normaliza una forma de Smogon y devuelve la especie que la agrupa."""
    normalizado = normalizar_nombre(nombre)
    base = SUFIJO_MEGA.sub("", normalizado)
    return EQUIVALENCIAS_BASE.get(base, base)


def descargar_estadisticas(mes, rating, formato):
    """Descarga una estadistica y conserva una copia exacta en cache."""
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


def _sumar_bloque(destino, valores, normalizar_claves=True):
    for nombre, valor in valores.items():
        if not nombre.strip():
            continue
        clave = nombre_base(nombre) if normalizar_claves else nombre
        destino[clave] = destino.get(clave, 0) + float(valor)


def _porcentajes(valores, peso, limite=None, minimo=0):
    """Convierte recuentos al porcentaje del peso proporcionado."""
    if peso <= 0:
        return {}
    resultado = [
        (nombre, float(valor) / peso * 100)
        for nombre, valor in valores.items()
        if float(valor) / peso * 100 >= minimo
    ]
    resultado.sort(key=lambda elemento: (-elemento[1], elemento[0]))
    if limite is not None:
        resultado = resultado[:limite]
    return dict(resultado)


def _variante(datos):
    """Resume cada entrada sin mezclar formas y con su propio peso."""
    peso = sum(float(valor) for valor in datos.get("Abilities", {}).values())
    resultado = {"uso": float(datos.get("usage", 0)) * 100}
    for origen, destino, limite, minimo in (
        ("Abilities", "habilidades", None, 1), ("Items", "objetos", 10, 0),
        ("Moves", "movimientos", 20, 5), ("Spreads", "spreads", 15, 0),
    ):
        valores = {}
        for clave, valor in datos.get(origen, {}).items():
            if clave.strip():
                clave = clave if origen == "Spreads" else normalizar_nombre(clave)
                valores[clave] = valores.get(clave, 0) + float(valor)
        resultado[destino] = _porcentajes(valores, peso, limite=limite, minimo=minimo)
    return resultado


def transformar_estadisticas(estadisticas, mes, rating, formato=None):
    """Agrupa formas Mega y adapta el JSON chaos al esquema del proyecto."""
    acumulados = {}
    for nombre_smogon, datos in estadisticas.get("data", {}).items():
        base = nombre_base(nombre_smogon)
        entrada = acumulados.setdefault(base, {
            "Raw count": 0.0, "usage": 0.0, "megas_raw": {}, "variantes": {},
            "Abilities": {}, "Items": {}, "Moves": {}, "Teammates": {}, "Spreads": {},
        })
        entrada["Raw count"] += float(datos.get("Raw count", 0))
        entrada["usage"] += float(datos.get("usage", 0))
        normalizado = normalizar_nombre(nombre_smogon)
        entrada["variantes"][normalizado] = _variante(datos)
        if SUFIJO_MEGA.search(normalizado):
            entrada["megas_raw"][normalizado] = (
                entrada["megas_raw"].get(normalizado, 0) + float(datos.get("Raw count", 0))
            )
        for bloque in ("Abilities", "Items", "Moves", "Teammates", "Spreads"):
            _sumar_bloque(
                entrada[bloque], datos.get(bloque, {}), normalizar_claves=bloque != "Spreads"
            )

    pokemon = {}
    for nombre, datos in acumulados.items():
        uso = datos["usage"] * 100
        if uso < 0.5:
            continue
        peso = sum(datos["Abilities"].values())
        raw = datos["Raw count"]
        pokemon[nombre] = {
            "uso": uso,
            "recuento": raw,
            "megas": _porcentajes(datos["megas_raw"], raw),
            "habilidades": _porcentajes(datos["Abilities"], peso, 10),
            "objetos": _porcentajes(datos["Items"], peso, 10),
            "movimientos": _porcentajes(datos["Moves"], peso, minimo=5),
            "companeros": _porcentajes(datos["Teammates"], peso, 20),
            "spreads": _porcentajes(datos["Spreads"], peso, 5),
            "variantes": datos["variantes"],
        }

    return {
        "info": {
            "mes": mes, "rating": rating, "formato": formato,
            "combates": estadisticas.get("info", {}).get("number of battles", 0),
        },
        "pokemon": pokemon,
    }


def nombres_desconocidos(estadisticas, pokemon_datos):
    """Devuelve nombres originales cuya especie base no existe localmente."""
    return sorted(nombre for nombre in estadisticas.get("data", {}) if nombre_base(nombre) not in pokemon_datos)


def validar_mes(valor):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", valor):
        raise argparse.ArgumentTypeError("el mes debe tener el formato AAAA-MM")
    return valor


def elegir_formato(regulacion, formato=None):
    """Prioriza la opción explícita, el formato Smogon y el de Showdown."""
    return formato or regulacion.get("formato_smogon") or regulacion["formato_showdown"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mes", required=True, type=validar_mes)
    parser.add_argument("--rating", type=int, default=1760)
    parser.add_argument("--archivo", help="JSON local que usar en vez de descargar")
    parser.add_argument("--formato", help="sobrescribe formato_showdown")
    args = parser.parse_args()

    regulacion = json.loads(ruta_regulacion().read_text(encoding="utf-8"))
    formato = elegir_formato(regulacion, args.formato)
    estadisticas = (
        json.loads(open(args.archivo, encoding="utf-8").read())
        if args.archivo else descargar_estadisticas(args.mes, args.rating, formato)
    )
    resultado = transformar_estadisticas(estadisticas, args.mes, args.rating, formato)
    ruta_salida = ruta_uso_smogon()
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nTop 20 por uso:")
    for nombre, datos in sorted(resultado["pokemon"].items(), key=lambda e: -e[1]["uso"])[:20]:
        print(f"  {nombre:<30} {datos['uso']:.2f}%")
    pokemon_datos = json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))
    desconocidos = nombres_desconocidos(estadisticas, pokemon_datos)
    print("\nNombres de Smogon ausentes en pokemon_datos.json:")
    print("\n".join(f"  {nombre}" for nombre in desconocidos) if desconocidos else "  Ninguno")
    print(f"\n✅ Guardado en {ruta_salida}")


if __name__ == "__main__":
    main()
