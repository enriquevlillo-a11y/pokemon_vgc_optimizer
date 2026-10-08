"""Interfaz web local del recomendador de equipos VGC."""

import json

import pandas as pd
import streamlit as st

from config import REGULACION_ACTIVA, ruta_pokemon_datos, ruta_regulacion, ruta_uso_smogon
from config import ruta_nombres
from amenazas import revisar_equipo
from sets import sets_equipo
from exportar import a_showdown
from interfaz import construir_filas_recomendaciones, frases_afinidad, opciones_selector
from motor_tipos import calcular_defensas
from recomendador import obtener_recomendaciones
from recomendador_tipos import calcular_debilidades_equipo
from roles import roles_de

EJEMPLO = ["gholdengo", "volcarona", "garchomp", "rillaboom", "raichu"]


@st.cache_data
def cargar_datos():
    return json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))


@st.cache_data
def cargar_uso():
    ruta = ruta_uso_smogon()
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


@st.cache_data
def cargar_regulacion():
    return json.loads(ruta_regulacion().read_text(encoding="utf-8"))


@st.cache_data
def cargar_nombres():
    ruta = ruta_nombres()
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


datos, uso, regulacion = cargar_datos(), cargar_uso(), cargar_regulacion()
nombres = cargar_nombres()
info = uso.get("info", {})
st.set_page_config(page_title="Optimizador VGC", page_icon="⚔️", layout="wide")
st.title("Optimizador de equipos Pokémon VGC")

with st.sidebar:
    st.header("Datos activos")
    st.write(f"**Regulación:** {regulacion.get('nombre', REGULACION_ACTIVA)}")
    if uso.get("pokemon"):
        st.write(f"**Mes:** {info.get('mes', '—')}")
        st.write(f"**Rating:** {info.get('rating', '—')}")
        st.write(f"**Formato:** {info.get('formato', '—')}")
    else:
        st.warning("No hay datos de uso disponibles; se mostrarán porcentajes de 0 %.")

if st.button("Cargar ejemplo: Eric Rios (Frankfurt 17-0)"):
    st.session_state.equipo = EJEMPLO

opciones = opciones_selector(datos, uso)
etiquetas = dict(opciones)
equipo = st.multiselect(
    "Elige de 1 a 6 Pokémon",
    options=[nombre for nombre, _ in opciones],
    format_func=lambda nombre: etiquetas[nombre],
    max_selections=6,
    key="equipo",
)

if equipo:
    st.header("Tu equipo")
    columnas = st.columns(len(equipo))
    entrada_uso = uso.get("pokemon", {})
    for columna, nombre in zip(columnas, equipo):
        pokemon, rol, estadisticas = datos[nombre], roles_de(nombre, datos, uso), entrada_uso.get(nombre, {})
        etiquetas_roles = {
            "fake_out": "Fake Out",
            "control_velocidad": "control de velocidad",
            "intimidate": "Intimidate",
            "anti_intimidate": "anti-Intimidate",
            "redireccion": "redirección",
            "pone_clima_terreno": "pone clima/terreno",
        }
        roles = [etiqueta for clave, etiqueta in etiquetas_roles.items() if rol.get(clave)]
        if rol["apoyo"] > 0:
            roles.append("apoyo")
        if rol["ofensivo"] >= 120:
            roles.append("atacante")
        with columna.container(border=True):
            st.subheader(nombre.title())
            st.write("**Tipos:** " + " / ".join(pokemon["tipos"]))
            st.write("**Roles:** " + (", ".join(roles) or "daño/cobertura"))
            if estadisticas:
                movimientos = list(estadisticas.get("movimientos", {}))[:3]
                objeto = next(iter(estadisticas.get("objetos", {})), "—")
                movimientos_visibles = [
                    nombres.get("movimientos", {}).get(movimiento, movimiento)
                    for movimiento in movimientos
                ]
                objeto_visible = nombres.get("objetos", {}).get(objeto, objeto)
                st.write("**Movimientos:** " + ", ".join(movimientos_visibles))
                st.write("**Objeto:** " + objeto_visible)

    recomendaciones = obtener_recomendaciones(equipo, datos, uso)
    st.header("Recomendaciones")
    st.dataframe(construir_filas_recomendaciones(recomendaciones, uso), hide_index=True, width="stretch")
    for recomendacion in recomendaciones[:5]:
        with st.expander(f"Desglose: {recomendacion['nombre'].title()}"):
            for componente, valor in recomendacion["puntuacion"].items():
                st.write(f"**{componente.replace('_', ' ').title()}:** {valor:.2f}")
            for frase in frases_afinidad(recomendacion["nombre"], equipo, uso):
                st.caption(frase)

    st.header("Amenazas")
    amenazas = revisar_equipo(equipo, datos, uso)
    st.dataframe([{
        "Pokémon": amenaza["nombre"],
        "Uso %": round(amenaza["uso"], 1),
        "Le pegan": ", ".join(amenaza["le_pegan"]) or "Sin respuesta",
        "Con": ", ".join(
            miembro + (" (" + ", ".join(movimientos) + ")" if movimientos else "")
            for miembro, movimientos in amenaza["con"].items()
        ),
    } for amenaza in amenazas], hide_index=True, width="stretch")

    st.header("Exportar equipo")
    sets = sets_equipo(equipo, uso, datos)
    faltantes = [nombre for nombre in equipo if not any(s["nombre"] == nombre for s in sets)]
    if faltantes:
        st.warning("Sin datos de Smogon para: " + ", ".join(faltantes))
    if sets:
        if not nombres.get("habilidades") or any(not datos[s["nombre"]].get("nombre_showdown") for s in sets):
            st.info("Ejecuta importar_showdown.py en local para actualizar los nombres de exportación.")
        elif faltantes:
            st.info("La exportación completa requiere datos de Smogon de todos los miembros.")
        else:
            texto = a_showdown(sets, datos, nombres)
            st.code(texto, language=None)
            st.download_button("Descargar equipo (.txt)", texto, file_name="equipo_showdown.txt", mime="text/plain")

    st.header("Debilidades del equipo")
    defensas = {nombre: calcular_defensas(datos[nombre]["tipos"]) for nombre in equipo}
    debilidades = calcular_debilidades_equipo(defensas)
    tabla = pd.DataFrame(
        [
            {"Tipo atacante": tipo, "Miembros débiles": cantidad}
            for tipo, cantidad in sorted(
                debilidades.items(), key=lambda elemento: (-elemento[1], elemento[0])
            )
        ]
    )
    if tabla.empty:
        st.info("El equipo no tiene debilidades de tipo.")
    else:
        st.dataframe(
            tabla.style.map(lambda valor: "background-color: #ff8f8f; font-weight: bold" if isinstance(valor, int) and valor >= 3 else "", subset=["Miembros débiles"]),
            hide_index=True,
            width="stretch",
        )
