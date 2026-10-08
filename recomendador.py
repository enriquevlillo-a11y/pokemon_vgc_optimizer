"""Recomendador de Pokémon basado en los roles necesarios en VGC."""

import json

from antisinergias import antisinergias
from config import ruta_pokemon_datos, ruta_uso_pikalytics, ruta_uso_smogon
from puntuacion import puntuar
from recomendador_tipos import calcular_debilidades_equipo, puntuar_candidato
from roles import roles_de


def cargar_uso():
    """Carga porcentajes simples, manteniendo la interfaz de la versión anterior."""
    uso = cargar_uso_smogon()
    if uso:
        return {nombre: entrada.get("uso", 0) for nombre, entrada in uso["pokemon"].items()}
    ruta = ruta_uso_pikalytics()
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    print("⚠️  No se encontró uso_smogon.json ni uso_pikalytics.json; se usará uso 0 para todos.")
    return {}


def cargar_uso_smogon():
    ruta = ruta_uso_smogon()
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def es_candidato(nombre, datos_pokemon, equipo):
    return (
        nombre not in equipo
        and not datos_pokemon.get("es_mega", False)
        and not datos_pokemon.get("solo_combate", False)
    )


def _aportes(rol):
    aportes = []
    fuente = rol["fuente"]
    if rol["fake_out"]:
        aportes.append(f"Fake Out ({fuente})")
    if rol["intimidate"]:
        aportes.append(f"Intimidate ({fuente})")
    if rol["anti_intimidate"]:
        aportes.append(f"anti-Intimidate ({fuente})")
    if rol["control_velocidad"]:
        aportes.append(f"Tailwind/Trick Room ({fuente})")
    elif rol["control_velocidad_debil"]:
        aportes.append(f"control velocidad débil ({fuente})")
    if rol["apoyo"]:
        aportes.append(f"apoyo {rol['apoyo']} ({fuente})")
    if rol["ofensivo"] >= 120:
        etiqueta = "Atacante (Mega)" if rol["ofensivo_base"] < 120 else "Atacante"
        aportes.append(etiqueta)
    if rol["pone_clima_terreno"]:
        aportes.append(f"pone clima/terreno ({fuente})")
    if rol["tiene_mega"]:
        aportes.append("Mega")
    return ", ".join(aportes) or "daño/cobertura"


def obtener_recomendaciones(equipo, datos, uso_smogon=None, aplicar_antisinergias=True):
    """Devuelve todos los candidatos ordenados; es la API reutilizable y testeable."""
    recomendaciones = []
    for nombre, pokemon in datos.items():
        if not es_candidato(nombre, pokemon, equipo):
            continue
        componentes = puntuar(equipo, nombre, datos, uso_smogon, aplicar_antisinergias)
        aporta = _aportes(roles_de(nombre, datos, uso_smogon))
        if aplicar_antisinergias:
            avisos, _ = antisinergias(equipo, nombre, datos, uso_smogon)
            if avisos:
                aporta += "; " + "; ".join(f"⚠️ {aviso}" for aviso in avisos)
        recomendaciones.append({
            "nombre": nombre,
            "tipos": pokemon["tipos"],
            "aporta": aporta,
            "puntuacion": componentes,
        })
    return sorted(recomendaciones, key=lambda r: (-r["puntuacion"]["total"], r["nombre"]))


def recomendar(equipo_nombres, top_n=10):
    datos = json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))
    recomendaciones = obtener_recomendaciones(equipo_nombres, datos, cargar_uso_smogon())
    print(f"\nTop {top_n} recomendaciones:")
    print(f"{'Pokémon':<22} {'Tipos':<18} {'Aporta':<43} {'Total':>6}")
    print("=" * 93)
    for recomendacion in recomendaciones[:top_n]:
        print(
            f"{recomendacion['nombre']:<22} "
            f"{' / '.join(recomendacion['tipos']):<18} "
            f"{recomendacion['aporta']:<43} "
            f"{recomendacion['puntuacion']['total']:>6.2f}"
        )
    return recomendaciones[:top_n]


def main():
    recomendar(["gholdengo", "volcarona", "garchomp", "rillaboom", "raichu"])


if __name__ == "__main__":
    main()
