"""Detección de roles relevantes para construir equipos de VGC."""

# Estas listas viven juntas y a la vista para poder ajustar el criterio a mano.
MOVIMIENTOS_FAKE_OUT = {"fakeout"}
MOVIMIENTOS_VELOCIDAD = {"tailwind", "trickroom"}
MOVIMIENTOS_VELOCIDAD_DEBIL = {"icywind", "electroweb"}
MOVIMIENTOS_APOYO = {
    "followme", "ragepowder", "helpinghand", "partingshot", "wideguard",
    "spore", "sleeppowder",
}
HABILIDADES_APOYO = {
    "lightning-rod", "storm-drain", "grassy-surge", "psychic-surge",
    "electric-surge", "misty-surge", "drought", "drizzle", "sand-stream",
    "snow-warning",
}


def _sin_guiones(texto):
    return texto.replace("-", "")


def _habilidades(datos_pokemon):
    return {
        _sin_guiones(habilidad.get("nombre", "") if isinstance(habilidad, dict) else habilidad)
        for habilidad in datos_pokemon.get("habilidades", [])
    }


def _ofensivo(datos_pokemon):
    stats = datos_pokemon.get("stats", {})
    return max(stats.get("attack", 0), stats.get("special-attack", 0))


def roles_de(nombre, datos):
    """Devuelve los roles de una especie base, incluyendo su potencial Mega."""
    pokemon = datos[nombre]
    movimientos = set(pokemon.get("movimientos", []))
    habilidades = _habilidades(pokemon)
    megas = [
        entrada for entrada in datos.values()
        if entrada.get("es_mega") and entrada.get("especie_base") == nombre
    ]
    apoyo_habilidades = {_sin_guiones(h) for h in HABILIDADES_APOYO}
    return {
        "fake_out": bool(movimientos & MOVIMIENTOS_FAKE_OUT),
        "control_velocidad": bool(movimientos & MOVIMIENTOS_VELOCIDAD),
        "control_velocidad_debil": bool(movimientos & MOVIMIENTOS_VELOCIDAD_DEBIL),
        "intimidate": "intimidate" in habilidades,
        "apoyo": len(movimientos & MOVIMIENTOS_APOYO)
        + len(habilidades & apoyo_habilidades),
        "ofensivo": max([_ofensivo(pokemon)] + [_ofensivo(mega) for mega in megas]),
        "tiene_mega": bool(megas),
    }
