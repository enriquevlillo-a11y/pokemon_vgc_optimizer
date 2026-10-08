from pathlib import Path


REGULACION_ACTIVA = "reg_m_c"

DIRECTORIO_PROYECTO = Path(__file__).resolve().parent
DIRECTORIO_DATOS = DIRECTORIO_PROYECTO / "data"


def ruta_regulacion():
    return DIRECTORIO_DATOS / "regulaciones" / f"{REGULACION_ACTIVA}.json"


def ruta_pokemon_permitidos():
    return DIRECTORIO_DATOS / REGULACION_ACTIVA / "pokemon_permitidos.json"


def ruta_pokemon_datos():
    return DIRECTORIO_DATOS / REGULACION_ACTIVA / "pokemon_datos.json"


def ruta_uso_pikalytics():
    return DIRECTORIO_DATOS / REGULACION_ACTIVA / "uso_pikalytics.json"


def ruta_uso_smogon():
    return DIRECTORIO_DATOS / REGULACION_ACTIVA / "uso_smogon.json"


def ruta_equipos_referencia():
    return DIRECTORIO_DATOS / "equipos_referencia.json"


DIRECTORIO_CACHE_SHOWDOWN = DIRECTORIO_DATOS / "cache_showdown"
DIRECTORIO_CACHE_SMOGON = DIRECTORIO_DATOS / "cache_smogon"
DIRECTORIO_REG_M_C = DIRECTORIO_DATOS / "reg_m_c"


def ruta_cache_showdown(nombre_archivo):
    """Devuelve la ruta de un archivo descargado de Pokémon Showdown."""
    return DIRECTORIO_CACHE_SHOWDOWN / nombre_archivo


def ruta_cache_smogon(nombre_archivo):
    """Devuelve la ruta de una estadística descargada de Smogon."""
    return DIRECTORIO_CACHE_SMOGON / nombre_archivo


def ruta_reg_m_c(nombre_archivo):
    """Devuelve la ruta de un archivo generado para Regulation M-C."""
    return DIRECTORIO_REG_M_C / nombre_archivo


def ruta_movimientos():
    return DIRECTORIO_DATOS / REGULACION_ACTIVA / "movimientos.json"


def ruta_nombres():
    return DIRECTORIO_DATOS / REGULACION_ACTIVA / "nombres.json"
