"""Compara los recomendadores por tipos (v1) y por roles (v2)."""

import json
from collections import defaultdict
from statistics import median

from config import ruta_equipos_referencia, ruta_pokemon_datos, ruta_uso_smogon
from motor_tipos import calcular_defensas
from recomendador import (
    calcular_debilidades_equipo,
    es_candidato,
    obtener_recomendaciones,
    puntuar_candidato,
)


def obtener_recomendaciones_v1(equipo, datos):
    """Ordena candidatos usando exclusivamente la cobertura defensiva de tipos."""
    defensas_equipo = {
        nombre: calcular_defensas(datos[nombre]["tipos"]) for nombre in equipo
    }
    debilidades = calcular_debilidades_equipo(defensas_equipo)
    candidatos = (
        nombre
        for nombre, pokemon in datos.items()
        if es_candidato(nombre, pokemon, equipo)
    )
    return sorted(
        candidatos,
        key=lambda nombre: (
            -puntuar_candidato(calcular_defensas(datos[nombre]["tipos"]), debilidades),
            nombre,
        ),
    )


def _puesto(nombre, recomendaciones):
    return recomendaciones.index(nombre) + 1


def evaluar_equipo(equipo, datos, uso_smogon=None):
    """Calcula los puestos v1 y v2 de cada integrante ocultado del equipo."""
    resultados = []
    for quitado in equipo:
        parcial = equipo.copy()
        parcial.remove(quitado)
        v1 = obtener_recomendaciones_v1(parcial, datos)
        v2 = [
            recomendacion["nombre"]
            for recomendacion in obtener_recomendaciones(parcial, datos, uso_smogon)
        ]
        resultados.append(
            {
                "pokemon": quitado,
                "puesto_v1": _puesto(quitado, v1),
                "puesto_v2": _puesto(quitado, v2),
            }
        )
    return resultados


def resumir(resultados, version):
    """Resume una colección de resultados para una versión del recomendador."""
    puestos = [resultado[f"puesto_{version}"] for resultado in resultados]
    return {
        "puesto_medio": sum(puestos) / len(puestos),
        "mediana": median(puestos),
        "top_10": sum(puesto <= 10 for puesto in puestos),
    }


def evaluar_referencias(referencias, datos, uso_smogon=None):
    """Agrupa la evaluación de todos los equipos por regulación."""
    por_regulacion = defaultdict(list)
    todos = []
    for referencia in referencias:
        resultados = evaluar_equipo(referencia["equipo"], datos, uso_smogon)
        for resultado in resultados:
            resultado.update(
                equipo=referencia["nombre"], regulacion=referencia["regulacion"]
            )
        por_regulacion[referencia["regulacion"]].extend(resultados)
        todos.extend(resultados)
    return dict(por_regulacion), todos


def imprimir_resumen(por_regulacion, todos):
    print(
        f"{'Regulación':<12} {'Versión':<8} "
        f"{'Media':>8} {'Mediana':>9} {'Top 10':>8}"
    )
    print("-" * 49)
    for regulacion, resultados in por_regulacion.items():
        for version in ("v1", "v2"):
            resumen = resumir(resultados, version)
            print(
                f"{regulacion:<12} {version:<8} {resumen['puesto_medio']:>8.2f} "
                f"{resumen['mediana']:>9.1f} {resumen['top_10']:>8}"
            )

    print("\n8 Pokémon peor recomendados por v2:")
    print(f"{'Pokémon':<20} {'Puesto':>7}  Equipo")
    print("-" * 70)
    for resultado in sorted(todos, key=lambda r: -r["puesto_v2"])[:8]:
        print(
            f"{resultado['pokemon']:<20} {resultado['puesto_v2']:>7}  "
            f"{resultado['equipo']}"
        )


def main():
    datos = json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))
    uso = (
        json.loads(ruta_uso_smogon().read_text(encoding="utf-8"))
        if ruta_uso_smogon().exists()
        else {}
    )
    referencias = json.loads(ruta_equipos_referencia().read_text(encoding="utf-8"))
    por_regulacion, todos = evaluar_referencias(referencias, datos, uso)
    imprimir_resumen(por_regulacion, todos)


if __name__ == "__main__":
    main()
