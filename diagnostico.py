"""Debilidades del equipo y motivos para las recomendaciones que se muestran."""

from amenazas import _defensas, revisar_equipo
from datos_uso import entrada_uso, forma_variante, habilidades_de, movimientos_de
from motor_tipos import calcular_defensas
from roles import roles_de

TIPOS = {
    "normal": "normal", "fire": "fuego", "water": "agua", "electric": "eléctrico",
    "grass": "planta", "ice": "hielo", "fighting": "lucha", "poison": "veneno",
    "ground": "tierra", "flying": "volador", "psychic": "psíquico", "bug": "bicho",
    "rock": "roca", "ghost": "fantasma", "dragon": "dragón", "dark": "siniestro",
    "steel": "acero", "fairy": "hada",
}
CONTROLES = {
    "tailwind": "Tailwind", "trickroom": "Trick Room",
    "icywind": "Icy Wind", "electroweb": "Electroweb",
}


def _nombre(nombre, datos):
    return datos[nombre].get("nombre_showdown", nombre.replace("-", " ").title())


def _forma_miembro(nombre, datos, uso_smogon, variantes):
    # Coincide con revisar_equipo, incluido su comportamiento con datos antiguos.
    if (entrada_uso(nombre, uso_smogon) or {}).get("variantes"):
        return forma_variante(nombre, uso_smogon, datos, variantes.get(nombre))
    return nombre


def _diagnosticar(equipo, datos, uso_smogon, variantes, amenazas):
    roles = [roles_de(n, datos, uso_smogon, variantes.get(n)) for n in equipo]
    resultado = []

    def agregar(identificador, categoria, texto, gravedad):
        resultado.append({"id": identificador, "categoria": categoria,
                          "texto": texto, "gravedad": gravedad})

    if not any(r["fake_out"] for r in roles):
        agregar("sin_fake_out", "rol", "El equipo no tiene Fake Out.", "alta")
    if not any(r["control_velocidad"] for r in roles):
        debil = any(r["control_velocidad_debil"] for r in roles)
        agregar("sin_control_velocidad", "rol",
                "El equipo solo tiene control de velocidad débil (Icy Wind/Electroweb)."
                if debil else "El equipo no tiene control de velocidad.",
                "media" if debil else "alta")
    if not any(r["intimidate"] for r in roles):
        agregar("sin_intimidate", "rol", "El equipo no tiene Intimidate.", "media")
    if not any(r["ofensivo"] >= 120 for r in roles):
        agregar("sin_win_condition", "rol",
                "Falta una condición de victoria: ningún miembro tiene Ataque o Ataque Especial ≥ 120.",
                "alta")
    defensas = {
        n: _defensas(n, _forma_miembro(n, datos, uso_smogon, variantes),
                     datos, uso_smogon, variantes.get(n)) for n in equipo
    }
    for tipo in TIPOS:
        debiles = [n for n in equipo if defensas[n][tipo] > 1]
        if len(debiles) >= 3 and not any(d[tipo] < 1 for d in defensas.values()):
            agregar(f"tipo_{tipo}", "tipo",
                    f"El tipo {TIPOS[tipo]} golpea superefectivo a {', '.join(_nombre(n, datos) for n in debiles)}; "
                    "ningún miembro lo resiste ni es inmune.", "alta")
    for amenaza in amenazas:
        estado = amenaza["estado"]
        if estado == "cubierta":
            continue
        motivo = ("nadie le pega superefectivo" if estado == "sin respuesta"
                  else "débiles: " + ", ".join(_nombre(n, datos) for n in amenaza["debiles"]))
        agregar(f"amenaza_{amenaza['nombre']}", "amenaza",
                f"{_nombre(amenaza['forma'], datos)}: {estado}; {motivo}.",
                "alta" if estado == "sin respuesta" else "media")
    return sorted(resultado, key=lambda d: (0 if d["gravedad"] == "alta" else 1, d["id"]))


def debilidades_equipo(equipo, datos, uso_smogon, movimientos=None, variantes=None):
    """Diagnóstico estable; variantes conserva el mapa existente especie → forma."""
    variantes = variantes or {}
    amenazas = revisar_equipo(equipo, datos, uso_smogon, n=20,
                              movimientos=movimientos, variantes=variantes)
    return _diagnosticar(equipo, datos, uso_smogon, variantes, amenazas)


def explicar(equipo, candidato, datos, uso_smogon, movimientos=None, variantes=None):
    """Explica carencias que mejora el candidato; llamar solo para el top N.

    Reutiliza la revisión previa en el diagnóstico y compara los estados con el
    equipo ampliado. No considera cubierta una amenaza que sigue en riesgo.
    """
    variantes = variantes or {}
    antes = revisar_equipo(equipo, datos, uso_smogon, n=20,
                           movimientos=movimientos, variantes=variantes)
    despues = {a["nombre"]: a for a in revisar_equipo(
        list(equipo) + [candidato], datos, uso_smogon, n=20,
        movimientos=movimientos, variantes=variantes,
    )}
    debilidades = _diagnosticar(equipo, datos, uso_smogon, variantes, antes)
    variante = variantes.get(candidato)
    rol = roles_de(candidato, datos, uso_smogon, variante)
    ataques = movimientos_de(candidato, datos, uso_smogon, variante)
    forma = _forma_miembro(candidato, datos, uso_smogon, variantes)
    defensa = _defensas(candidato, forma, datos, uso_smogon, variante)
    tipos = " / ".join(TIPOS[t] for t in datos[forma]["tipos"])
    amenazas_antes = {a["nombre"]: a for a in antes}
    orden_estado = {"sin respuesta": 0, "en riesgo": 1, "cubierta": 2}
    resultado = []
    for debilidad in debilidades:
        identificador, texto = debilidad["id"], None
        if identificador == "sin_fake_out" and rol["fake_out"]:
            texto = "Aporta Fake Out."
        elif identificador == "sin_intimidate" and rol["intimidate"]:
            texto = "Aporta Intimidate para reducir el Ataque rival."
        elif identificador == "sin_win_condition" and rol["ofensivo"] >= 120:
            texto = f"Aporta una condición de victoria con una estadística ofensiva de {rol['ofensivo']}."
        elif identificador == "sin_control_velocidad":
            controles = [nombre for m, nombre in CONTROLES.items() if m in ataques]
            if rol["control_velocidad"]:
                texto = "Aporta control de velocidad con " + ", ".join(controles) + "."
            elif rol["control_velocidad_debil"] and debilidad["gravedad"] == "alta":
                texto = "Aporta control de velocidad débil con " + ", ".join(controles) + "; la carencia se reduce a gravedad media."
        elif debilidad["categoria"] == "tipo":
            tipo = identificador.removeprefix("tipo_")
            if defensa[tipo] < 1:
                verbo = "Es inmune a" if defensa[tipo] == 0 else "Resiste"
                origen = tipos
                if defensa[tipo] == 0 and calcular_defensas(datos[forma]["tipos"])[tipo] != 0:
                    origen = "habilidad: " + ", ".join(sorted(habilidades_de(candidato, datos, uso_smogon, variante)))
                texto = f"{verbo} {TIPOS[tipo]} ({origen})."
        elif debilidad["categoria"] == "amenaza":
            nombre = identificador.removeprefix("amenaza_")
            previa, nueva = amenazas_antes[nombre], despues[nombre]
            if orden_estado[nueva["estado"]] > orden_estado[previa["estado"]]:
                amenaza = _nombre(nueva["forma"], datos)
                ataques_efectivos = nueva["con"].get(candidato, [])
                texto = f"Deja a {amenaza} de '{previa['estado']}' a '{nueva['estado']}'"
                if ataques_efectivos:
                    texto += f": le pega superefectivo con {', '.join(ataques_efectivos)}"
                elif candidato in nueva["le_pegan"]:
                    texto += f": le pega superefectivo con sus tipos ({tipos})"
                texto += "."
        if texto:
            resultado.append({"id": identificador, "texto": texto})
    return resultado
