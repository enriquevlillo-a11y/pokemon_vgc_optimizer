"""Interfaz web local del recomendador de equipos VGC."""

import json
from copy import deepcopy
import shutil

import pandas as pd
import streamlit as st

from amenazas import revisar_equipo
from analisis_set import calculos_clave, velocidad_set, velocidades_relevantes
from calculo import DIRECTORIO_CALCULO, INSTALACION
from diagnostico import debilidades_equipo, explicar
from config import REGULACION_ACTIVA, ruta_pokemon_datos, ruta_regulacion, ruta_uso_smogon
from config import ruta_nombres
from sets import sets_equipo, set_probable
from exportar import a_showdown
from importar_showdown import normalizar_id
from datos_uso import entrada_variante, forma_variante, seleccionar_variante
from interfaz import construir_filas_amenazas, construir_filas_recomendaciones, frases_afinidad, opciones_selector
from motor_tipos import calcular_defensas
from recomendador import obtener_recomendaciones
from recomendador_tipos import calcular_debilidades_equipo
from roles import roles_de
from velocidad import velocidad, velocidades_reales

EJEMPLO = ["gholdengo", "volcarona", "garchomp", "rillaboom", "raichu"]
NATURALEZAS = sorted("Hardy Lonely Brave Adamant Naughty Bold Docile Relaxed Impish Lax Timid Hasty Serious Jolly Naive Modest Mild Quiet Bashful Rash Calm Gentle Sassy Careful Quirky".split())
ETIQUETAS_STATS = {"hp": "PS", "attack": "Atk", "defense": "Def", "special-attack": "SpA",
                   "special-defense": "SpD", "speed": "Spe"}


def restablecer_set(clave, probable):
    st.session_state.sets_editados[clave] = deepcopy(probable)
    for widget in list(st.session_state):
        if widget.startswith(f"editar_{clave}_"):
            del st.session_state[widget]


def editar_set(clave, probable, datos, nombres):
    guardados = st.session_state.setdefault("sets_editados", {})
    entrada = deepcopy(guardados.setdefault(clave, deepcopy(probable)))
    prefijo = f"editar_{clave}_"
    with st.expander("Editar set"):
        st.button("Volver al set probable", key=f"reset_{clave}",
                  on_click=restablecer_set, args=(clave, probable))
        naturaleza = entrada.get("naturaleza") or "Serious"
        entrada["naturaleza"] = st.selectbox("Naturaleza", NATURALEZAS,
                                             index=NATURALEZAS.index(naturaleza), key=prefijo + "naturaleza")
        columnas = st.columns(6)
        for columna, (stat, etiqueta) in zip(columnas, ETIQUETAS_STATS.items()):
            entrada["puntos"][stat] = columna.number_input(
                f"Puntos {etiqueta}", min_value=0, max_value=32,
                value=entrada["puntos"].get(stat, 0), step=1, key=prefijo + stat,
            )
        total = sum(entrada["puntos"].values())
        st.caption(f"Puntos: {total}/66")
        if total > 66:
            st.warning(f"Sobran {total - 66} puntos: el máximo es 66. Ajusta el reparto para calcular daño y exportar.")

        def selector(etiqueta, campo, categoria, opciones, actual):
            opciones = sorted(set(opciones) | ({actual} if actual else set()),
                              key=lambda valor: nombres.get(categoria, {}).get(valor, valor))
            opciones = [None] + opciones
            return st.selectbox(etiqueta, opciones, index=opciones.index(actual),
                                format_func=lambda valor: nombres.get(categoria, {}).get(valor, valor) if valor else "—",
                                key=prefijo + campo)

        entrada["objeto"] = selector("Objeto", "objeto", "objetos", nombres.get("objetos", {}),
                                     normalizar_id(entrada["objeto"]) if entrada.get("objeto") else None)
        ficha = datos[entrada["nombre"]]
        habilidades = [normalizar_id(h["nombre"] if isinstance(h, dict) else h)
                       for h in ficha.get("habilidades", [])]
        entrada["habilidad"] = selector("Habilidad", "habilidad", "habilidades", habilidades,
                                        normalizar_id(entrada["habilidad"]) if entrada.get("habilidad") else None)
        learnset = [normalizar_id(m) for m in ficha.get("movimientos", [])]
        actuales = entrada.get("movimientos", [])
        entrada["movimientos"] = []
        for i in range(4):
            actual = normalizar_id(actuales[i]) if i < len(actuales) and actuales[i] else None
            movimiento = selector(f"Movimiento {i + 1}", f"movimiento_{i}", "movimientos", learnset, actual)
            entrada["movimientos"].append(movimiento)
        # Guarda también los huecos de los cuatro selectores para no desplazar slots.
        guardados[clave] = deepcopy(entrada)
    return {**entrada, "movimientos": [m for m in entrada["movimientos"] if m]}


def corte_spe(valor, sin_datos=False, trick_room=False):
    if sin_datos:
        return "sin datos"
    if valor is None:
        return "imposible con esta naturaleza"
    if valor == 0:
        return "0 (en el corte)"
    if trick_room:
        return f"Quitar {-valor}" if valor < 0 else f"Margen +{valor}"
    return f"Faltan {valor}" if valor > 0 else f"Sobran {-valor}"


@st.cache_data(max_entries=128, show_spinner=False)
def calcular_duelos(entrada, datos, uso):
    return calculos_clave(entrada, datos, uso)


def tabla_dano(resultados):
    filas = []
    for resultado in resultados:
        fila = {"Amenaza": resultado["forma"]}
        for lado, etiqueta in (("ataque", "Tu ataque"), ("defensa", "Su ataque")):
            ataque = resultado[lado]
            fila[etiqueta] = ataque["movimiento"] if ataque else "sin datos"
            fila[etiqueta + " (%)"] = f"{ataque['porcentaje_min']:.1f}–{ataque['porcentaje_max']:.1f} %" if ataque else "—"
            fila[etiqueta + " KO"] = ataque["ko"] if ataque else "—"
        fila["Avisos"] = " • ".join(resultado["errores"])
        filas.append(fila)
    colores = {"favorable": "background-color: #c8e6c9; color: #17351a",
               "desfavorable": "background-color: #ffcdd2; color: #52171b", "neutra": ""}
    return pd.DataFrame(filas).style.apply(
        lambda fila: [colores[resultados[fila.name]["ventaja"]]] * len(fila), axis=1,
    )


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

    st.header("Sets, velocidades y cálculos")
    st.caption("Velocidad Champions a nivel 50: tu objeto Scarf sí se aplica; las amenazas usan su spread más común sin inferir Scarf ni habilidades. Tailwind solo para ti; Trick Room invierte el orden, con empate en igualdad. Los cortes Spe permiten redistribuir otros stats.")
    calculadora_disponible = bool(shutil.which("node")) and (
        DIRECTORIO_CALCULO / "node_modules" / "@smogon" / "calc" / "package.json"
    ).is_file()
    if not calculadora_disponible:
        st.warning(f"Cálculo de daño no disponible. {INSTALACION}")
    st.caption("Daño en Doubles con campo vacío y PS completos. Mejor ataque por daño máximo (mínimo para desempatar). Verde: OHKO/2HKO garantizado solo a tu favor; rojo: solo a favor de la amenaza.")
    sets = []
    for probable in sets_equipo(equipo, uso, datos, variantes=variantes_equipo):
        nombre = probable["nombre"]
        st.subheader(f"Set de {nombre.title()}")
        clave = f"{nombre}:{variantes_equipo.get(nombre) or 'habitual'}"
        entrada = editar_set(clave, probable, datos, nombres)
        sets.append(entrada)
        st.write(f"**Velocidad del set:** {velocidad_set(entrada, datos)} · **Con Tailwind:** {velocidad_set(entrada, datos, tailwind=True)}")
        filas_velocidad = []
        for fila in velocidades_relevantes(entrada, datos, uso):
            sin_datos = fila["velocidad"] is None
            filas_velocidad.append({
                "Amenaza": fila["forma"], "Tu velocidad": fila["velocidad_propia"],
                "Su velocidad": fila["velocidad"], "Orden": fila["comparacion"],
                "Corte Spe": corte_spe(fila["puntos_spe"], sin_datos),
                "Con Tailwind": fila["comparacion_tailwind"],
                "Corte Spe Tailwind": corte_spe(fila["puntos_spe_tailwind"], sin_datos),
                "Bajo Trick Room": {"más rápido": "actúas primero", "más lento": "actúas después"}.get(
                    fila["comparacion_trick_room"], fila["comparacion_trick_room"]),
                "Corte Spe Trick Room": corte_spe(fila["puntos_spe_trick_room"], sin_datos, True),
            })
        if filas_velocidad:
            st.dataframe(filas_velocidad, hide_index=True, width="stretch")
        else:
            st.info("Sin amenazas de uso para comparar velocidades.")
        if sum(entrada["puntos"].values()) > 66:
            st.info("Ajusta el reparto a 66 puntos para ver los cálculos de daño.")
        elif calculadora_disponible:
            try:
                resultados = calcular_duelos(entrada, datos, uso)
                if resultados:
                    st.dataframe(tabla_dano(resultados), hide_index=True, width="stretch")
                else:
                    st.info("Sin amenazas de uso para calcular daño.")
            except (RuntimeError, ValueError) as error:
                st.warning(f"No se pudo calcular el daño de {nombre}: {error}")

    st.header("Exportar equipo")
    for entrada in sets:
        if entrada.get("generico"):
            st.warning(f"{entrada['nombre'].title()}: set genérico (sin datos de uso)")
    if any(sum(entrada["puntos"].values()) > 66 for entrada in sets):
        st.warning("No se puede exportar: algún set supera el máximo de 66 puntos.")
    elif sets:
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
