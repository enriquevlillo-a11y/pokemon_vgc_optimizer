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
HABILIDADES_CLIMA_TERRENO = {
    "drought", "drizzle", "sand-stream", "snow-warning", "grassy-surge",
    "psychic-surge", "electric-surge", "misty-surge",
}
HABILIDADES_ANTI_INTIMIDATE = {
    "defiant", "competitive", "clear-body", "inner-focus", "oblivious",
    "own-tempo", "scrappy", "guard-dog", "mirror-armor",
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


def _entrada_uso(nombre, uso_smogon):
    if not uso_smogon:
        return None
    pokemon = uso_smogon.get("pokemon", uso_smogon)
    entrada = pokemon.get(nombre)
    return entrada if isinstance(entrada, dict) else None


def roles_de(nombre, datos, uso_smogon=None):
    """Devuelve roles de uso real si existe Smogon, o del learnset si no."""
    pokemon = datos[nombre]
    entrada_uso = _entrada_uso(nombre, uso_smogon)
    if entrada_uso is not None:
        movimientos = {
            _sin_guiones(movimiento) for movimiento, porcentaje
            in entrada_uso.get("movimientos", {}).items() if porcentaje >= 20
        }
        habilidades = {
            _sin_guiones(habilidad) for habilidad, porcentaje
            in entrada_uso.get("habilidades", {}).items() if porcentaje >= 50
        }
        fuente = "uso real"
    else:
        movimientos = set(pokemon.get("movimientos", []))
        habilidades = _habilidades(pokemon)
        fuente = "learnset"
    megas = [
        entrada for entrada in datos.values()
        if entrada.get("es_mega") and entrada.get("especie_base") == nombre
    ]
    apoyo_habilidades = {_sin_guiones(h) for h in HABILIDADES_APOYO}
    return {
        "fake_out": bool(movimientos & MOVIMIENTOS_FAKE_OUT),
        "control_velocidad": bool(movimientos & MOVIMIENTOS_VELOCIDAD),
        "control_velocidad_debil": bool(movimientos & MOVIMIENTOS_VELOCIDAD_DEBIL),
        "redireccion": bool(movimientos & {"followme", "ragepowder"}),
        "intimidate": "intimidate" in habilidades,
        "anti_intimidate": bool(habilidades & {_sin_guiones(h) for h in HABILIDADES_ANTI_INTIMIDATE}),
        "apoyo": len(movimientos & MOVIMIENTOS_APOYO)
        + len(habilidades & apoyo_habilidades),
        "ofensivo": max([_ofensivo(pokemon)] + [_ofensivo(mega) for mega in megas]),
        "ofensivo_base": _ofensivo(pokemon),
        "pone_clima_terreno": bool(
            habilidades & {_sin_guiones(h) for h in HABILIDADES_CLIMA_TERRENO}
        ),
        "tiene_mega": bool(megas),
        "fuente": fuente,
    }
