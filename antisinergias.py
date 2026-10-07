"""Avisos de prioridad bloqueada y conflictos de campos o climas en VGC."""

from datos_uso import habilidades_de, mega_habitual, movimientos_de


CAMPOS = {"psychicsurge", "grassysurge", "electricsurge", "mistysurge"}
CLIMAS = {"drought", "drizzle", "sandstream", "snowwarning"}
# Prioridades ofensivas; Protect, Helping Hand y otras prioridades de apoyo
# no quedan bloqueadas por Psychic Terrain.
MOVIMIENTOS_PRIORIDAD = {
    "accelerock", "aquajet", "bulletpunch", "extremespeed",
    "feint", "firstimpression", "grassyglide", "iceshard", "jetpunch",
    "machpunch", "quickattack", "shadowsneak", "suckerpunch",
    "thunderclap", "vacuumwave", "watershuriken",
}


def _habilidades_efectivas(nombre, datos, uso_smogon):
    habilidades = habilidades_de(nombre, datos, uso_smogon)
    mega = mega_habitual(nombre, uso_smogon, datos)
    if mega:
        habilidades |= habilidades_de(mega, datos)
    return habilidades


def _avisos_prioridad(nombre, movimientos, candidato):
    avisos = []
    if "fakeout" in movimientos:
        avisos.append("Psychic Terrain bloquea su Fake Out" if nombre == candidato else f"Psychic Terrain bloquea el Fake Out de {nombre}")
    if movimientos & MOVIMIENTOS_PRIORIDAD:
        destino = "sus movimientos de prioridad" if nombre == candidato else f"los movimientos de prioridad de {nombre}"
        avisos.append(f"Psychic Terrain bloquea {destino}")
    return avisos


def _conflicto(habilidades, otras, conjunto):
    return any(a != b for a in habilidades & conjunto for b in otras & conjunto)


def antisinergias(equipo, candidato, datos, uso_smogon=None):
    """Devuelve (avisos, penalización positiva) al añadir un candidato.

    Usa habilidades >=50 % y movimientos >=20 % si existe entrada Smogon;
    sin ella, usa habilidades disponibles y learnset. Incluye habilidades de
    la Mega habitual si la especie megaevoluciona en más del 50 % de equipos.
    Psychic Terrain se aproxima como bloqueo contra objetivos en el suelo.
    Cada compañero con campo distinto penaliza 4; con clima distinto, 2.
    """
    habilidades = _habilidades_efectivas(candidato, datos, uso_smogon)
    movimientos = movimientos_de(candidato, datos, uso_smogon)
    avisos, penalizacion = [], 0
    for miembro in equipo:
        otras = _habilidades_efectivas(miembro, datos, uso_smogon)
        if "psychicsurge" in otras:
            avisos.extend(_avisos_prioridad(candidato, movimientos, candidato))
        if "psychicsurge" in habilidades:
            avisos.extend(_avisos_prioridad(miembro, movimientos_de(miembro, datos, uso_smogon), candidato))
        if _conflicto(habilidades, otras, CAMPOS):
            penalizacion += 4
            avisos.append(f"sustituye el campo de {miembro}")
        if _conflicto(habilidades, otras, CLIMAS):
            penalizacion += 2
            avisos.append(f"sustituye el clima de {miembro}")
    return list(dict.fromkeys(avisos)), penalizacion
