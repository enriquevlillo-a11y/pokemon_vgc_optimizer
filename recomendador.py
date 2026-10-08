"""Recomendador de Pokémon basado en los roles necesarios en VGC."""

import json

from antisinergias import antisinergias
from config import ruta_pokemon_datos, ruta_uso_pikalytics, ruta_uso_smogon
from datos_uso import entrada_variante, normalizar, uso_agregado
from diagnostico import debilidades_equipo, explicar
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


def obtener_recomendaciones(equipo, datos, uso_smogon=None, aplicar_antisinergias=True, variantes=None):
    """Devuelve todos los candidatos ordenados; es la API reutilizable y testeable."""
    uso_variantes = uso_smogon
    variantes = variantes or {}
    uso_smogon = uso_agregado(uso_smogon)
    recomendaciones = []
    usuarios_fake = sum(roles_de(n, datos, uso_variantes, variantes.get(n)).get("fake_out", False) for n in equipo)
    for nombre, pokemon in datos.items():
        if not es_candidato(nombre, pokemon, equipo):
            continue
        componentes = puntuar(equipo, nombre, datos, uso_smogon, aplicar_antisinergias)
        rol = roles_de(nombre, datos, uso_smogon)
        aporta = _aportes(rol)
        if usuarios_fake >= 2:
            rol_variante = roles_de(nombre, datos, uso_variantes, variantes.get(nombre))
            uso_fake = max((p for m, p in (entrada_variante(nombre, uso_variantes, variantes.get(nombre)) or {}).get("movimientos", {}).items()
                            if normalizar(m) == "fakeout"), default=0)
            if rol_variante.get("fake_out") and uso_fake < 50:
                aporta += "; ⚠️ ya hay 2 Fake Out: su set no debería llevarlo"
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
    # Los errores de coma flotante no deben decidir empates matemáticos.
    return sorted(recomendaciones, key=lambda r: (-round(r["puntuacion"]["total"], 6), r["nombre"]))


def recomendar(equipo_nombres, top_n=10, movimientos=None, variantes=None):
    datos = json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))
    uso = cargar_uso_smogon()
    print("\nDebilidades de tu equipo:")
    debilidades = debilidades_equipo(equipo_nombres, datos, uso, movimientos, variantes)
    for debilidad in debilidades:
        print(f"  [{debilidad['gravedad']}] {debilidad['texto']}")
    if not debilidades:
        print("  No se detectan debilidades con estos criterios.")
    recomendaciones = obtener_recomendaciones(equipo_nombres, datos, uso, variantes=variantes)
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
        motivos = explicar(equipo_nombres, recomendacion["nombre"], datos, uso, movimientos, variantes)
        for motivo in motivos:
            print(f"    Por qué: {motivo['texto']}")
        if not motivos:
            print("    Por qué: no cubre las debilidades detectadas; se recomienda por su puntuación global.")
    return recomendaciones[:top_n]


def main():
    recomendar(["gholdengo", "volcarona", "garchomp", "rillaboom", "raichu"])


if __name__ == "__main__":
    main()
