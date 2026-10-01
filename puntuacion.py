"""Puntuación por roles, sinergia, uso y defensa de tipos."""

from motor_tipos import calcular_defensas
from recomendador_tipos import calcular_debilidades_equipo, puntuar_candidato
from roles import roles_de


PESOS = {
    "fake": 3,
    "velocidad": 3,
    "apoyo": 0.5,
    "intimidate": 2,
    "ofensivo": 1.0,
    "mega": 1.0,
    "tipos": 0.3,
    "companeros": 2.0,
    "uso": 0.5,
}


def _entrada_uso(nombre, uso_smogon):
    if not uso_smogon:
        return None
    pokemon = uso_smogon.get("pokemon", uso_smogon)
    entrada = pokemon.get(nombre)
    return entrada if isinstance(entrada, dict) else None


def _puntuacion_companeros(equipo, entrada):
    if not equipo or not entrada:
        return 0
    companeros = entrada.get("companeros", {})
    return PESOS["companeros"] * sum(companeros.get(n, 0) for n in equipo) / len(equipo) / 10


def puntuar(equipo, candidato, datos, uso_smogon=None):
    """Desglosa la puntuación de ``candidato`` para completar ``equipo``."""
    roles_equipo = [roles_de(nombre, datos) for nombre in equipo]
    rol = roles_de(candidato, datos)
    componentes = {}
    componentes["fake"] = PESOS["fake"] * (0.5 if any(r["fake_out"] for r in roles_equipo) else 1) if rol["fake_out"] else 0
    if rol["control_velocidad_debil"] and not rol["control_velocidad"]:
        componentes["velocidad"] = 0.3 * PESOS["velocidad"]
    elif rol["control_velocidad"]:
        componentes["velocidad"] = PESOS["velocidad"] * (0.3 if any(r["control_velocidad"] for r in roles_equipo) else 1)
    else:
        componentes["velocidad"] = 0
    componentes["apoyo"] = PESOS["apoyo"] * min(rol["apoyo"], 2)
    componentes["intimidate"] = PESOS["intimidate"] if rol["intimidate"] else 0
    ofensivo = PESOS["ofensivo"] * max(0, rol["ofensivo"] - 100) / 30
    if sum(r["ofensivo"] >= 120 for r in roles_equipo) >= 2:
        ofensivo /= 2
    componentes["ofensivo"] = ofensivo
    componentes["mega"] = PESOS["mega"] if rol["tiene_mega"] and sum(r["tiene_mega"] for r in roles_equipo) < 2 else 0
    defensas = {n: calcular_defensas(datos[n]["tipos"]) for n in equipo}
    componentes["tipos"] = PESOS["tipos"] * puntuar_candidato(
        calcular_defensas(datos[candidato]["tipos"]),
        calcular_debilidades_equipo(defensas),
    )
    entrada = _entrada_uso(candidato, uso_smogon)
    componentes["companeros"] = _puntuacion_companeros(equipo, entrada)
    componentes["uso"] = PESOS["uso"] * entrada.get("uso", 0) / 10 if entrada else 0
    componentes["total"] = sum(componentes.values())
    return componentes
