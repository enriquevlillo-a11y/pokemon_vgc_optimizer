"""Interfaz web local del recomendador de equipos VGC."""

import json

import pandas as pd
import streamlit as st

from amenazas import revisar_equipo
from diagnostico import debilidades_equipo, explicar
from config import REGULACION_ACTIVA, ruta_pokemon_datos, ruta_regulacion, ruta_uso_smogon
from config import ruta_nombres
from sets import sets_equipo, set_probable
from exportar import a_showdown
from datos_uso import entrada_variante, forma_variante, seleccionar_variante
from interfaz import construir_filas_amenazas, construir_filas_recomendaciones, frases_afinidad, opciones_selector
from motor_tipos import calcular_defensas
from recomendador import obtener_recomendaciones
from recomendador_tipos import calcular_debilidades_equipo
from roles import roles_de
from velocidad import velocidad, velocidades_reales

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
    variantes_equipo = {}
    for columna, nombre in zip(columnas, equipo):
        with columna.container(border=True):
            st.subheader(nombre.title())
            variantes = uso.get("pokemon", {}).get(nombre, {}).get("variantes", {})
            megas = [forma for forma in variantes if datos.get(forma, {}).get("es_mega")]
            if megas:
                habitual = seleccionar_variante(nombre, uso)
                formas = sorted(variantes, key=lambda f: (-variantes[f].get("uso", 0), f))
                variante = st.selectbox(
                    "Mega / sin Mega", formas, index=formas.index(habitual),
                    format_func=lambda f: "Mega" + (f" ({f})" if len(megas) > 1 else "") if f in megas else "sin Mega",
                    key=f"variante_{nombre}",
                )
                variantes_equipo[nombre] = variante
            variante = variantes_equipo.get(nombre)
            forma = forma_variante(nombre, uso, datos, variante) if variantes else nombre
            pokemon = datos[forma]
            rol = roles_de(nombre, datos, uso, variante)
            estadisticas = entrada_variante(nombre, uso, variante)
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
            st.write("**Tipos:** " + " / ".join(pokemon["tipos"]))
            st.write("**Roles:** " + (", ".join(roles) or "daño/cobertura"))
            st.write(f"**Velocidad máxima:** {velocidad(forma, datos)}")
            reales = velocidades_reales(nombre, uso, datos, variante)
            real = reales.get(forma)
            st.write(f"**Velocidad real:** {real if real is not None else 'sin datos'}")
            if not variantes:
                for otra_forma, real in reales.items():
                    if otra_forma != nombre:
                        st.write(f"**{otra_forma} — velocidad máxima:** {velocidad(otra_forma, datos)}")
                        st.write(f"**{otra_forma} — velocidad real:** {real if real is not None else 'sin datos'}")
            if estadisticas:
                if variantes:
                    probable = set_probable(nombre, uso, datos, variante=variante)
                    movimientos = probable["movimientos"][:3]
                    objeto = probable["objeto"] or "—"
                else:
                    movimientos = list(estadisticas.get("movimientos", {}))[:3]
                    objeto = next(iter(estadisticas.get("objetos", {})), "—")
                movimientos_visibles = [
                    nombres.get("movimientos", {}).get(movimiento, movimiento)
                    for movimiento in movimientos
                ]
                objeto_visible = nombres.get("objetos", {}).get(objeto, objeto)
                st.write("**Movimientos:** " + ", ".join(movimientos_visibles))
                st.write("**Objeto:** " + objeto_visible)

    st.header("Debilidades de tu equipo")
    diagnostico = debilidades_equipo(equipo, datos, uso, variantes=variantes_equipo)
    for debilidad in diagnostico:
        mensaje = f"**Gravedad {debilidad['gravedad']}:** {debilidad['texto']}"
        if debilidad["gravedad"] == "alta":
            st.error(mensaje)
        else:
            st.warning(mensaje)
    if not diagnostico:
        st.info("No se detectan debilidades con estos criterios.")

    recomendaciones = obtener_recomendaciones(equipo, datos, uso, variantes=variantes_equipo)
    filas = construir_filas_recomendaciones(recomendaciones, uso)
    for fila, recomendacion in zip(filas, recomendaciones):
        motivos = explicar(equipo, recomendacion["nombre"], datos, uso, variantes=variantes_equipo)
        fila["Por qué"] = " • ".join(m["texto"] for m in motivos) or "No cubre las debilidades detectadas; destaca por su puntuación global."
    st.header("Recomendaciones")
    st.dataframe(filas, hide_index=True, width="stretch")
    for recomendacion in recomendaciones[:5]:
        with st.expander(f"Desglose: {recomendacion['nombre'].title()}"):
            for componente, valor in recomendacion["puntuacion"].items():
                st.write(f"**{componente.replace('_', ' ').title()}:** {valor:.2f}")
            for frase in frases_afinidad(recomendacion["nombre"], equipo, uso):
                st.caption(frase)

    st.header("Amenazas del meta")
    st.caption("Cobertura por ataques con uso ≥ 20 %; sin datos de Smogon, tipos propios. Sin cálculo de daño. Velocidad máxima sin Scarf ni Tailwind; velocidad real según el spread más usado.")
    amenazas = revisar_equipo(equipo, datos, uso, variantes=variantes_equipo)
    if amenazas:
        st.dataframe(construir_filas_amenazas(amenazas), hide_index=True, width="stretch")
    else:
        st.info("No hay datos de uso para comprobar las amenazas del meta.")

    st.header("Exportar equipo")
    sets = sets_equipo(equipo, uso, datos, variantes=variantes_equipo)
    for entrada in sets:
        if entrada.get("generico"):
            st.warning(f"{entrada['nombre'].title()}: set genérico (sin datos de uso)")
    if sets:
        if not nombres.get("habilidades") or any(not datos[s["nombre"]].get("nombre_showdown") for s in sets):
            st.info("Ejecuta importar_showdown.py en local para actualizar los nombres de exportación.")
        else:
            texto = a_showdown(sets, datos, nombres)
            st.code(texto, language=None)
            st.download_button("Descargar equipo (.txt)", texto, file_name="equipo_showdown.txt", mime="text/plain")

    st.header("Debilidades del equipo")
    defensas = {}
    for nombre in equipo:
        tiene_variantes = uso.get("pokemon", {}).get(nombre, {}).get("variantes")
        forma = forma_variante(nombre, uso, datos, variantes_equipo.get(nombre)) if tiene_variantes else nombre
        defensas[nombre] = calcular_defensas(datos[forma]["tipos"])
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
