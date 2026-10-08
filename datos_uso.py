"""Consultas pequeñas a los datos de uso y a la Mega habitual."""


def entrada_uso(nombre, uso_smogon):
    """Acepta el documento de Smogon o su diccionario de especies."""
    pokemon = (uso_smogon or {}).get("pokemon", uso_smogon or {})
    entrada = pokemon.get(nombre)
    return entrada if isinstance(entrada, dict) else None


def seleccionar_variante(nombre, uso_smogon, variante=None):
    """Resuelve una forma explícita o la de mayor uso; None para datos antiguos."""
    variantes = (entrada_uso(nombre, uso_smogon) or {}).get("variantes", {})
    if not variantes:
        return None
    if variante is not None:
        if variante not in variantes:
            raise ValueError(f"Variante desconocida para {nombre}: {variante}")
        return variante
    return min(variantes, key=lambda forma: (-variantes[forma].get("uso", 0), forma))


def entrada_variante(nombre, uso_smogon, variante=None):
    """Datos de una sola forma, o la entrada agregada en el esquema antiguo."""
    entrada = entrada_uso(nombre, uso_smogon)
    forma = seleccionar_variante(nombre, uso_smogon, variante)
    return entrada["variantes"][forma] if forma is not None else entrada


def forma_variante(nombre, uso_smogon, datos, variante=None):
    """Forma para tipos y stats; conserva la Mega habitual del esquema antiguo."""
    forma = seleccionar_variante(nombre, uso_smogon, variante)
    if forma is not None:
        return forma if forma in datos else nombre
    return mega_habitual(nombre, uso_smogon, datos) or nombre


def uso_agregado(uso_smogon):
    """Vista histórica del recomendador, sin modificar el documento original."""
    if not uso_smogon:
        return uso_smogon
    pokemon = uso_smogon.get("pokemon", uso_smogon)
    if not any(isinstance(e, dict) and e.get("variantes") for e in pokemon.values()):
        return uso_smogon
    agregados = {n: {k: v for k, v in e.items() if k != "variantes"}
                 if isinstance(e, dict) else e for n, e in pokemon.items()}
    return {**uso_smogon, "pokemon": agregados} if "pokemon" in uso_smogon else agregados


def mega_habitual(nombre, uso_smogon, datos):
    """Elige la Mega más usada si la suma de megaevoluciones supera el 50 %."""
    megas = (entrada_uso(nombre, uso_smogon) or {}).get("megas", {})
    if not megas or sum(megas.values()) <= 50:
        return None
    mega = max(megas, key=megas.get)
    return mega if mega in datos else None


def normalizar(nombre):
    """Unifica los identificadores de Showdown y los nombres con guiones."""
    return nombre.lower().replace("-", "").replace(" ", "")


def habilidades_de(nombre, datos, uso_smogon=None, variante=None):
    """Habilidades con uso >=50 %, o habilidades disponibles sin Smogon."""
    entrada = entrada_variante(nombre, uso_smogon, variante)
    if entrada is not None:
        return {normalizar(h) for h, uso in entrada.get("habilidades", {}).items() if uso >= 50}
    return {
        normalizar(h["nombre"] if isinstance(h, dict) else h)
        for h in datos[nombre].get("habilidades", [])
    }


def movimientos_de(nombre, datos, uso_smogon=None, variante=None):
    """Movimientos con uso >=20 %, o learnset completo sin Smogon."""
    entrada = entrada_variante(nombre, uso_smogon, variante)
    if entrada is not None:
        return {normalizar(m) for m, uso in entrada.get("movimientos", {}).items() if uso >= 20}
    return {normalizar(m) for m in datos[nombre].get("movimientos", [])}
