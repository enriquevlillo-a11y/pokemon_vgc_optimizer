"""Puntuación por roles, sinergia, uso y defensa de tipos."""

from antisinergias import antisinergias
from datos_uso import uso_agregado
from motor_tipos import calcular_defensas
from recomendador_tipos import calcular_debilidades_equipo, puntuar_candidato
from roles import roles_de


PESOS = {
    "fake": 3,
    "velocidad": 3,
    "apoyo": 0.5,
    "intimidate": 2,
    "anti_intimidate": 1.5,
    "ofensivo": 1.0,
    "mega": 1.0,
    "tipos": 0.3,
    "companeros": 8,
    "uso": 0.5,
}


def _entrada_uso(nombre, uso_smogon):
    if not uso_smogon:
        return None
    pokemon = uso_smogon.get("pokemon", uso_smogon)
    entrada = pokemon.get(nombre)
    return entrada if isinstance(entrada, dict) else None


def _puntuacion_companeros(equipo, candidato, uso_smogon):
    if not equipo or not uso_smogon:
        return 0
    afinidades = []
    for miembro in equipo:
        entrada_miembro = _entrada_uso(miembro, uso_smogon)
        afinidades.append(
            entrada_miembro.get("companeros", {}).get(candidato, 0) / 100 * 10
            if entrada_miembro else 0
        )
    return PESOS["companeros"] * sum(afinidades) / len(afinidades)


def puntuar(equipo, candidato, datos, uso_smogon=None, aplicar_antisinergias=True):
    """Desglosa la puntuación de ``candidato`` para completar ``equipo``."""
    uso_smogon = uso_agregado(uso_smogon)
    roles_equipo = [roles_de(nombre, datos, uso_smogon) for nombre in equipo]
    rol = roles_de(candidato, datos, uso_smogon)
    componentes = {}
    usuarios_fake = sum(r["fake_out"] for r in roles_equipo)
    factor_fake = 1 if usuarios_fake == 0 else 0.5 if usuarios_fake == 1 else 0
    componentes["fake"] = PESOS["fake"] * factor_fake if rol["fake_out"] else 0
    if rol["control_velocidad_debil"] and not rol["control_velocidad"]:
        componentes["velocidad"] = 0.3 * PESOS["velocidad"]
    elif rol["control_velocidad"]:
        componentes["velocidad"] = PESOS["velocidad"] * (0.3 if any(r["control_velocidad"] for r in roles_equipo) else 1)
    else:
        componentes["velocidad"] = 0
    componentes["apoyo"] = PESOS["apoyo"] * min(rol["apoyo"], 2)
    componentes["intimidate"] = PESOS["intimidate"] if rol["intimidate"] else 0
    componentes["anti_intimidate"] = PESOS["anti_intimidate"] if rol["anti_intimidate"] else 0
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
    componentes["companeros"] = _puntuacion_companeros(equipo, candidato, uso_smogon)
    componentes["uso"] = PESOS["uso"] * entrada.get("uso", 0) / 10 if entrada else 0
    if aplicar_antisinergias:
        avisos, penalizacion = antisinergias(equipo, candidato, datos, uso_smogon)
        if "Psychic Terrain bloquea su Fake Out" in avisos:
            componentes["fake"] = 0
        componentes["antisinergia"] = -penalizacion
    componentes["total"] = sum(componentes.values())
    return componentes
