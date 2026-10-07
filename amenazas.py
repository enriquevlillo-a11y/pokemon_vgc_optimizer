"""Lista de comprobación del meta basada en tipos y velocidades."""

import json

from config import ruta_pokemon_datos
from datos_uso import mega_habitual
from motor_tipos import calcular_defensas
from velocidad import velocidad, velocidades_reales


def amenazas_del_meta(uso_smogon, n=20, datos=None):
    """Las n especies con mayor uso y los tipos de su Mega habitual, si procede.

    Los datos de especies se cargan desde config.py si no se proporcionan.
    """
    if datos is None:
        datos = json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))
    pokemon = (uso_smogon or {}).get("pokemon", uso_smogon or {})
    ordenadas = sorted(pokemon, key=lambda nombre: (-pokemon[nombre].get("uso", 0), nombre))
    resultado = []
    for nombre in ordenadas[:max(0, n)]:
        forma = mega_habitual(nombre, uso_smogon, datos) or nombre
        resultado.append({
            "nombre": nombre,
            "uso": pokemon[nombre].get("uso", 0),
            "tipos": datos[forma]["tipos"],
            "forma": forma,
        })
    return resultado


def _estado(le_pegan, debiles):
    if not le_pegan:
        return "sin respuesta"
    return "en riesgo" if len(debiles) >= 3 else "cubierta"


def revisar_equipo(equipo, datos, uso_smogon, n=20):
    """Aproximación por tipos propios, sin cálculo de daño ni cobertura de moves.

    Compara la velocidad máxima de cada miembro (32 puntos, naturaleza favorable,
    sin Scarf/Tailwind) con el spread más usado de la amenaza, o su máximo cuando
    falta. Para amenazas que megaevolucionan >50 %, usa su Mega habitual.
    """
    defensas = {nombre: calcular_defensas(datos[nombre]["tipos"]) for nombre in equipo}
    velocidades = {nombre: velocidad(nombre, datos) for nombre in equipo}
    resultado = []
    for amenaza in amenazas_del_meta(uso_smogon, n, datos):
        defensa = calcular_defensas(amenaza["tipos"])
        le_pegan = [nombre for nombre in equipo if any(defensa[tipo] > 1 for tipo in datos[nombre]["tipos"])]
        debiles = [nombre for nombre in equipo if any(defensas[nombre][tipo] > 1 for tipo in amenaza["tipos"])]
        forma = amenaza["forma"]
        real = velocidades_reales(amenaza["nombre"], uso_smogon, datos).get(forma)
        referencia = real if real is not None else velocidad(forma, datos)
        mas_rapidos = [nombre for nombre in equipo if velocidades[nombre] > referencia]
        resultado.append({
            **amenaza,
            "le_pegan": le_pegan,
            "debiles": debiles,
            "mas_rapidos": mas_rapidos,
            "estado": _estado(le_pegan, debiles),
        })
    return resultado
