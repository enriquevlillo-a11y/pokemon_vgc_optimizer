"""Puntuación pura del bot C1b, sin objetos de poke-env ni servidor."""


def valor_golpe(rango, ps_frac, precision=1.0):
    """Daño medio limitado a PS restantes + 0,6 × probabilidad lineal de KO.

    Rango y PS son fracciones de los PS máximos. La precisión multiplica
    todo el valor; se conserva la aproximación del prototipo C1b.
    """
    lo, hi = rango
    media = (lo + hi) / 2
    if lo >= ps_frac:
        p_ko = 1.0
    elif hi < ps_frac:
        p_ko = 0.0
    else:
        p_ko = (hi - ps_frac) / (hi - lo)
    return precision * (min(media, ps_frac) + 0.6 * p_ko)


def combinar(golpes1, golpes2):
    """Suma rangos por objetivo antes de valorar KO, como en el prototipo.

    Cada diccionario contiene objetivo: ((mínimo, máximo), PS, precisión).
    Cada rango se pondera por precisión; el bonus de KO se cuenta una vez.
    """
    total = 0.0
    for objetivo in set(golpes1) | set(golpes2):
        partes = [g[objetivo] for g in (golpes1, golpes2) if objetivo in g]
        ps = partes[0][1]
        lo = sum(p[0][0] * p[2] for p in partes)
        hi = sum(p[0][1] * p[2] for p in partes)
        total += valor_golpe((lo, hi), ps)
    return total


def velocidad_efectiva(stat, boost=0, *, paralizado=False, tailwind=False, scarf=False):
    """Aplica boosts, Scarf ×1,5, Tailwind ×2 y parálisis ×0,5 al stat natural.

    Boost b usa (2+b)/2 si b >= 0, o 2/(2-b) si b < 0. Se trunca tras
    boosts y Scarf y tras parálisis, con un mínimo de 1. El stat de entrada
    ya incluye naturaleza y puntos Champions, calculados con velocidad.py.
    No infiere habilidades ni activa Trick Room: este invierte el orden,
    no la estadística de velocidad.
    """
    if not -6 <= boost <= 6:
        raise ValueError("El boost de velocidad debe estar entre -6 y +6")
    resultado = int(stat * ((2 + boost) / 2 if boost >= 0 else 2 / (2 - boost)))
    if scarf:
        resultado = int(resultado * 1.5)
    if tailwind:
        resultado *= 2
    if paralizado:
        resultado //= 2
    return max(1, resultado)


def valorar_control_velocidad(movimiento, propias, rivales, *, trick_room=False, tailwind=False):
    """Valora control con las velocidades efectivas de los activos vivos.

    Para cada par propio-rival: +1 si somos más lentos, -1 si más rápidos,
    0 en empate. B = suma / número de pares. Trick Room vale 0,6 × B;
    Tailwind vale 0,55 × max(0, B). Mantiene los máximos del prototipo.
    Trick Room ya activo vale 0 (repetirlo lo anularía); Tailwind vale 0
    si ya está en nuestro lado o hay Trick Room. Sin pares, vale 0.
    """
    if movimiento not in ("trickroom", "tailwind"):
        raise ValueError("El movimiento debe ser trickroom o tailwind")
    if trick_room or (movimiento == "tailwind" and tailwind):
        return 0.0
    pares = [(p, r) for p in propias for r in rivales]
    if not pares:
        return 0.0
    balance = sum((p < r) - (p > r) for p, r in pares) / len(pares)
    return 0.6 * balance if movimiento == "trickroom" else 0.55 * max(0, balance)
