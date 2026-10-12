"""Lectura de equipos Showdown sin depender de poke-env."""

import re

from calculo import _especie

ETIQUETAS = {"HP": "hp", "Atk": "attack", "Def": "defense", "SpA": "special-attack",
             "SpD": "special-defense", "Spe": "speed"}


def leer_equipo(texto, datos):
    """Texto Showdown -> {id base: set del repo sin convertir}, en orden.

    Conserva los puntos Champions (no los convierte a EVs). Admite CRLF,
    líneas vacías con espacios, apodos y el sufijo de género de Showdown.
    """
    equipo = {}
    if not texto.strip():
        return equipo
    for bloque in re.split(r"\n\s*\n", texto.strip().replace("\r\n", "\n")):
        lineas = [linea.strip() for linea in bloque.splitlines()]
        especie, _, objeto = lineas[0].partition(" @ ")
        especie = re.sub(r" \([MF]\)$", "", especie)
        apodo = re.search(r"\(([^()]+)\)$", especie)
        if apodo:
            especie = apodo[1]
        entrada = {"nombre": _especie(especie.strip(), datos), "objeto": objeto.strip(),
                   "movimientos": [], "puntos": {}}
        for linea in lineas[1:]:
            if linea.startswith("Ability: "):
                entrada["habilidad"] = linea[9:]
            elif linea.startswith("EVs: "):
                for reparto in linea[5:].split(" / "):
                    cantidad, stat = reparto.split()
                    entrada["puntos"][ETIQUETAS[stat]] = int(cantidad)
            elif linea.endswith(" Nature"):
                entrada["naturaleza"] = linea[:-7]
            elif linea.startswith("- "):
                entrada["movimientos"].append(linea[2:])
        equipo[entrada["nombre"]] = entrada
    return equipo
