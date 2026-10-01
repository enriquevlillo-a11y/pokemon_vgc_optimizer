"""Funciones de puntuación defensiva conservadas del recomendador original."""

from motor_tipos import TODOS_LOS_TIPOS


def calcular_debilidades_equipo(equipo_defensas):
    return {
        tipo: cuenta
        for tipo in TODOS_LOS_TIPOS
        if (cuenta := sum(1 for defensa in equipo_defensas.values() if defensa[tipo] >= 2))
    }


def puntuar_candidato(defensas_candidato, debilidades_equipo):
    puntuacion = 0
    for tipo, cuenta in debilidades_equipo.items():
        valor = defensas_candidato[tipo]
        if valor == 0:
            puntuacion += 3 * cuenta
        elif valor <= 0.5:
            puntuacion += cuenta
        elif valor >= 2:
            puntuacion -= cuenta
    return puntuacion
