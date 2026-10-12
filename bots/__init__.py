"""Bots de dobles; las utilidades puras no requieren poke-env ni Showdown."""

from .equipos import leer_equipo
from .evaluacion import combinar, valor_golpe, valorar_control_velocidad, velocidad_efectiva

__all__ = ["leer_equipo", "combinar", "valor_golpe", "valorar_control_velocidad",
           "velocidad_efectiva"]
