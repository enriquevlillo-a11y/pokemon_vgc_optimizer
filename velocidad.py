"""Estadísticas de Pokémon Champions a nivel 50, sin efectos de habilidades."""

from datos_uso import entrada_uso, mega_habitual


NATURALEZAS_RAPIDAS = {"Timid", "Jolly", "Hasty", "Naive"}
NATURALEZAS_LENTAS = {"Brave", "Quiet", "Relaxed", "Sassy"}


def calcular_stat(base, puntos=32, naturaleza=1.1, ps=False):
    """Trunca (base + puntos + 20) × naturaleza; PS = base + puntos + 75."""
    if not isinstance(puntos, int) or not 0 <= puntos <= 32:
        raise ValueError("Los puntos deben ser enteros entre 0 y 32")
    if naturaleza not in (0.9, 1.0, 1.1):
        raise ValueError("La naturaleza debe ser 0.9, 1.0 o 1.1")
    return base + puntos + 75 if ps else int((base + puntos + 20) * naturaleza)


def velocidad(nombre, datos, puntos=32, naturaleza=1.1, scarf=False, tailwind=False):
    """Calcula velocidad, truncando el stat y después el modificador Scarf."""
    stat = calcular_stat(datos[nombre]["stats"]["speed"], puntos, naturaleza)
    if scarf:
        stat = int(stat * 1.5)
    return stat * 2 if tailwind else stat


def _spread_habitual(nombre, uso_smogon):
    spreads = (entrada_uso(nombre, uso_smogon) or {}).get("spreads", {})
    if not spreads:
        return None
    spread = max(spreads, key=spreads.get)
    try:
        naturaleza, reparto = spread.split(":")
        puntos = [int(p) for p in reparto.split("/")]
    except (ValueError, AttributeError):
        return None
    if len(puntos) != 6 or any(not 0 <= p <= 32 for p in puntos):
        return None
    modificador = 1.1 if naturaleza in NATURALEZAS_RAPIDAS else 0.9 if naturaleza in NATURALEZAS_LENTAS else 1.0
    return puntos[-1], modificador


def velocidad_real(nombre, uso_smogon, datos):
    """Velocidad base con el spread más usado; None si falta un spread válido.

    No infiere Scarf ni habilidades a partir de distribuciones independientes.
    ``velocidades_reales`` añade la velocidad de la Mega habitual al resultado.
    """
    spread = _spread_habitual(nombre, uso_smogon)
    if spread is None or nombre not in datos:
        return None
    return velocidad(nombre, datos, puntos=spread[0], naturaleza=spread[1])


def velocidades_reales(nombre, uso_smogon, datos):
    """Devuelve velocidad de la especie y también de su Mega habitual (>50 %)."""
    resultado = {nombre: velocidad_real(nombre, uso_smogon, datos)}
    mega = mega_habitual(nombre, uso_smogon, datos)
    spread = _spread_habitual(nombre, uso_smogon)
    if mega:
        resultado[mega] = (
            velocidad(mega, datos, puntos=spread[0], naturaleza=spread[1])
            if spread else None
        )
    return resultado
