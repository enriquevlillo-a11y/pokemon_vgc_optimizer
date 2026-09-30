from pathlib import Path


REGULACION_ACTIVA = "reg_g"

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
