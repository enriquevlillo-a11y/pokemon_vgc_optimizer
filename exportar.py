"""Exportación de sets en el formato de Pokémon Showdown Champions."""

from importar_showdown import normalizar_id

STATS_SHOWDOWN = {"hp": "HP", "attack": "Atk", "defense": "Def",
                  "special-attack": "SpA", "special-defense": "SpD", "speed": "Spe"}


def a_showdown(sets, datos, nombres):
    """Exporta los puntos Champions sin convertirlos a EVs tradicionales."""
    def visible(categoria, identificador):
        return nombres.get(categoria, {}).get(normalizar_id(identificador), identificador)

    bloques = []
    for entrada in sets:
        nombre = entrada["nombre"]
        especie = datos[nombre].get("nombre_showdown")
        if not especie:
            raise ValueError(f"Falta nombre_showdown para {nombre}; ejecuta importar_showdown.py")
        cabecera = especie
        if entrada.get("objeto"):
            cabecera += " @ " + visible("objetos", entrada["objeto"])
        lineas = [cabecera]
        if entrada.get("habilidad"):
            lineas.append("Ability: " + visible("habilidades", entrada["habilidad"]))
        lineas.append("Level: 50")
        puntos = entrada.get("puntos", {})
        evs = [f"{puntos[stat]} {etiqueta}" for stat, etiqueta in STATS_SHOWDOWN.items() if puntos.get(stat, 0)]
        if evs:
            lineas.append("EVs: " + " / ".join(evs))
        if entrada.get("naturaleza"):
            lineas.append(entrada["naturaleza"] + " Nature")
        lineas.extend("- " + visible("movimientos", movimiento) for movimiento in entrada["movimientos"])
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques)
