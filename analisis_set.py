"""Velocidad y duelos de un set Champions frente a las especies más usadas."""

import json

import config
from amenazas import amenazas_del_meta
from calculo import Calculadora, set_a_calculo
from importar_showdown import normalizar_id
from sets import set_probable
from velocidad import NATURALEZAS_LENTAS, NATURALEZAS_RAPIDAS, velocidad, velocidades_reales


def forma_del_set(entrada, datos):
    """Aplica la piedra del set, conservando las especies Mega explícitas."""
    nombre = entrada["nombre"]
    if datos[nombre].get("es_mega"):
        return nombre
    objeto = normalizar_id(entrada.get("objeto") or "")
    return next((forma for forma, ficha in datos.items()
                 if ficha.get("es_mega") and ficha.get("especie_base") == nombre
                 and objeto and normalizar_id(ficha.get("objeto_mega") or "") == objeto), nombre)


def velocidad_set(entrada, datos, *, puntos=None, tailwind=False):
    """Velocidad con naturaleza, piedra y Scarf; sin efectos de habilidades."""
    naturaleza = entrada.get("naturaleza")
    modificador = (1.1 if naturaleza in NATURALEZAS_RAPIDAS else
                   0.9 if naturaleza in NATURALEZAS_LENTAS else 1.0)
    return velocidad(
        forma_del_set(entrada, datos), datos,
        puntos=entrada.get("puntos", {}).get("speed", 0) if puntos is None else puntos,
        naturaleza=modificador, scarf=normalizar_id(entrada.get("objeto") or "") == "choicescarf",
        tailwind=tailwind,
    )


def puntos_para_superar(entrada, datos, objetivo, *, tailwind=False, trick_room=False):
    """Diferencia firmada respecto a Spe actual; None si es imposible.

    En normal/Tailwind, busca el mínimo Spe que supera estrictamente el objetivo:
    positivo = faltan puntos, negativo = sobran. En Trick Room busca el máximo
    Spe que queda estrictamente por debajo: negativo = hay que quitar puntos,
    positivo = margen para añadirlos. Un empate nunca gana. Los cortes permiten
    redistribuir los otros stats y solo están limitados por 0–32 Spe.
    """
    candidatos = range(32, -1, -1) if trick_room else range(33)
    for puntos in candidatos:
        valor = velocidad_set(entrada, datos, puntos=puntos, tailwind=tailwind)
        supera = valor < objetivo if trick_room else valor > objetivo
        if supera:
            return puntos - entrada.get("puntos", {}).get("speed", 0)
    return None


def _comparacion(propia, rival, trick_room=False):
    if rival is None:
        return "sin datos"
    if propia == rival:
        return "empate"
    gana = propia < rival if trick_room else propia > rival
    return "más rápido" if gana else "más lento"


def velocidades_relevantes(entrada, datos, uso_smogon, n=20):
    """Compara con el spread más común de la forma habitual del top n.

    Las amenazas siguen velocidades_reales (sin Scarf ni habilidades inferidos).
    Si falta su spread se conserva la fila con velocidad y cortes None.
    En Trick Room, «más rápido» significa que actúas primero por ser más lento.
    """
    propia = velocidad_set(entrada, datos)
    resultado = []
    for amenaza in amenazas_del_meta(uso_smogon, n, datos):
        rival = velocidades_reales(amenaza["nombre"], uso_smogon, datos).get(amenaza["forma"])
        fila = {**amenaza, "velocidad_propia": propia, "velocidad": rival,
                "comparacion": _comparacion(propia, rival),
                "comparacion_tailwind": _comparacion(propia * 2, rival),
                "comparacion_trick_room": _comparacion(propia, rival, True)}
        for clave, opciones in (("puntos_spe", {}), ("puntos_spe_tailwind", {"tailwind": True}),
                                ("puntos_spe_trick_room", {"trick_room": True})):
            fila[clave] = None if rival is None else puntos_para_superar(entrada, datos, rival, **opciones)
        resultado.append(fila)
    return resultado


def _mejor_ataque(opciones):
    validas = [r for r in opciones if r.get("ok")]
    # Mayor daño máximo; el mínimo desempata. No se pierde el texto de KO de calc.
    return max(validas, key=lambda r: (r["max"], r["min"]), default=None)


def _ko_corto(resultado):
    return bool(resultado and resultado["ko"].startswith(("guaranteed OHKO", "guaranteed 2HKO")))


def calculos_clave(entrada, datos, uso_smogon, n=20):
    """Mejores ataques en ambos sentidos, en una sola llamada calcular_lote.

    Usa sets probables y sus piedras, nivel 50/Doubles y campo vacío (sin clima,
    terreno, boosts ni pantallas añadidos). Devuelve errores por amenaza sin
    confundirlos con daño cero. RuntimeError de instalación/transporte se propaga.
    Verde/rojo exige OHKO/2HKO garantizado solo en uno de los dos sentidos.
    """
    nombres = json.loads(config.ruta_nombres().read_text(encoding="utf-8"))
    movimientos = json.loads(config.ruta_movimientos().read_text(encoding="utf-8"))
    propia = set_a_calculo(entrada, datos, nombres, megaevolucionado=True)
    filas, peticiones, destinos = [], [], []
    for amenaza in amenazas_del_meta(uso_smogon, n, datos):
        fila = {**amenaza, "ataque": None, "defensa": None, "errores": [], "ventaja": "neutra"}
        filas.append(fila)
        probable = set_probable(amenaza["nombre"], uso_smogon, datos, movimientos)
        if probable is None:
            fila["errores"].append("Sin set probable de la amenaza.")
            continue
        rival = set_a_calculo(probable, datos, nombres, megaevolucionado=True)
        for lado, atacante, defensor in (("ataque", propia, rival), ("defensa", rival, propia)):
            for movimiento in atacante["movimientos"]:
                peticiones.append({"atacante": atacante, "defensor": defensor, "movimiento": movimiento})
                destinos.append((len(filas) - 1, lado, movimiento))
    if not peticiones:
        return filas
    with Calculadora(datos=datos, nombres=nombres, movimientos=movimientos) as calculadora:
        respuestas = calculadora.calcular_lote(peticiones)
    opciones = {(i, lado): [] for i in range(len(filas)) for lado in ("ataque", "defensa")}
    for (i, lado, movimiento), respuesta in zip(destinos, respuestas):
        if respuesta.get("ok"):
            opciones[i, lado].append({**respuesta, "movimiento": movimiento})
        else:
            filas[i]["errores"].append(f"{lado} / {movimiento}: {respuesta['error']}")
    for i, fila in enumerate(filas):
        for lado in ("ataque", "defensa"):
            fila[lado] = _mejor_ataque(opciones[i, lado])
        if fila["ataque"] is not None and fila["defensa"] is not None and not fila["errores"]:
            a, d = _ko_corto(fila["ataque"]), _ko_corto(fila["defensa"])
            fila["ventaja"] = "favorable" if a and not d else "desfavorable" if d and not a else "neutra"
    return filas
