"""Consultas pequeñas a los datos de uso y a la Mega habitual."""


def entrada_uso(nombre, uso_smogon):
    """Acepta el documento de Smogon o su diccionario de especies."""
    pokemon = (uso_smogon or {}).get("pokemon", uso_smogon or {})
    entrada = pokemon.get(nombre)
    return entrada if isinstance(entrada, dict) else None


def mega_habitual(nombre, uso_smogon, datos):
    """Elige la Mega más usada si la suma de megaevoluciones supera el 50 %."""
    megas = (entrada_uso(nombre, uso_smogon) or {}).get("megas", {})
    if not megas or sum(megas.values()) <= 50:
        return None
    mega = max(megas, key=megas.get)
    return mega if mega in datos else None


def normalizar(nombre):
    """Unifica los identificadores de Showdown y los nombres con guiones."""
    return nombre.lower().replace("-", "").replace(" ", "")


def habilidades_de(nombre, datos, uso_smogon=None):
    """Habilidades con uso >=50 %, o habilidades disponibles sin Smogon."""
    entrada = entrada_uso(nombre, uso_smogon)
    if entrada is not None:
        return {normalizar(h) for h, uso in entrada.get("habilidades", {}).items() if uso >= 50}
    return {
        normalizar(h["nombre"] if isinstance(h, dict) else h)
        for h in datos[nombre].get("habilidades", [])
    }


def movimientos_de(nombre, datos, uso_smogon=None):
    """Movimientos con uso >=20 %, o learnset completo sin Smogon."""
    entrada = entrada_uso(nombre, uso_smogon)
    if entrada is not None:
        return {normalizar(m) for m, uso in entrada.get("movimientos", {}).items() if uso >= 20}
    return {normalizar(m) for m in datos[nombre].get("movimientos", [])}
