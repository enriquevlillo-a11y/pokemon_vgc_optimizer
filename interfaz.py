"""Transformaciones de presentación, independientes de Streamlit."""

from recomendador import es_candidato


def construir_filas_amenazas(amenazas):
    """Presenta primero las amenazas sin respuesta, después las de riesgo."""
    orden = {"sin respuesta": 0, "en riesgo": 1, "cubierta": 2}
    return [{
        "Amenaza": a["forma"],
        "Uso %": round(a["uso"], 2),
        "Le pegan": ", ".join(a["le_pegan"]) or "—",
        "Más rápidos": ", ".join(a["mas_rapidos"]) or "—",
        "Débiles": ", ".join(a["debiles"]) or "—",
        "Estado": a["estado"],
    } for a in sorted(amenazas, key=lambda a: (orden[a["estado"]], -a["uso"], a["nombre"]))]


def opciones_selector(datos, uso_smogon):
    """Devuelve pares ``(nombre, etiqueta)`` válidos, ordenados por uso."""
    uso = uso_smogon.get("pokemon", {}) if uso_smogon else {}
    nombres = [n for n, pokemon in datos.items() if es_candidato(n, pokemon, [])]
    nombres.sort(key=lambda n: (-uso.get(n, {}).get("uso", 0), n))
    return [(n, f"{n} ({uso.get(n, {}).get('uso', 0):.1f}%)") for n in nombres]


def construir_filas_recomendaciones(recomendaciones, uso_smogon, limite=10):
    """Convierte recomendaciones en filas listas para una tabla."""
    uso = uso_smogon.get("pokemon", {}) if uso_smogon else {}
    return [{
        "Pokémon": r["nombre"],
        "Tipos": " / ".join(r["tipos"]),
        "Aporta": r["aporta"],
        "Uso %": round(uso.get(r["nombre"], {}).get("uso", 0), 1),
        "Afinidad con el equipo": round(r["puntuacion"].get("companeros", 0), 2),
        "Total": round(r["puntuacion"]["total"], 2),
    } for r in recomendaciones[:limite]]


def frases_afinidad(candidato, equipo, uso_smogon):
    """Explica qué porcentaje de los equipos de cada miembro usa al candidato."""
    pokemon = uso_smogon.get("pokemon", {}) if uso_smogon else {}
    return [
        f"Lo llevan el {pokemon.get(miembro, {}).get('companeros', {}).get(candidato, 0):g} % "
        f"de los equipos con {miembro.title()}"
        for miembro in equipo
    ]
