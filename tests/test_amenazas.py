from amenazas import amenazas_del_meta, revisar_equipo
from interfaz import construir_filas_amenazas


def pokemon(tipos, velocidad):
    return {"tipos": tipos, "stats": {"speed": velocidad}}


def test_agua_sin_planta_ni_electrico_no_tiene_respuesta():
    datos = {"amenaza": pokemon(["water"], 80), "aliado": pokemon(["fire"], 90)}
    resultado = revisar_equipo(["aliado"], datos, {"amenaza": {"uso": 20}})[0]
    assert resultado["estado"] == "sin respuesta"
    assert resultado["le_pegan"] == []
    assert resultado["debiles"] == ["aliado"]


def test_en_riesgo_con_tres_debiles_y_respuesta():
    datos = {"amenaza": pokemon(["water"], 80), "planta": pokemon(["grass"], 90)}
    datos.update({n: pokemon(["fire"], 80) for n in ["uno", "dos", "tres"]})
    resultado = revisar_equipo(["planta", "uno", "dos", "tres"], datos, {"amenaza": {"uso": 20}})[0]
    assert resultado["le_pegan"] == ["planta"]
    assert resultado["debiles"] == ["uno", "dos", "tres"]
    assert resultado["estado"] == "en riesgo"
    assert resultado["mas_rapidos"] == ["planta"]  # La igualdad no cuenta.


def test_velocidad_real_y_fallback_al_maximo():
    datos = {"amenaza": pokemon(["water"], 100), "planta": pokemon(["grass"], 80)}
    uso = {"amenaza": {"uso": 20, "spreads": {"Quiet:32/0/0/32/2/0": 90}}}
    resultado = revisar_equipo(["planta"], datos, uso)[0]
    assert resultado["estado"] == "cubierta"
    assert resultado["mas_rapidos"] == ["planta"]
    uso["amenaza"]["spreads"] = {}
    assert revisar_equipo(["planta"], datos, uso)[0]["mas_rapidos"] == []


def test_doble_tipo_se_aplican_resistencias_e_inmunidades():
    datos = {"amenaza": pokemon(["water", "ground"], 80),
             "electrico": pokemon(["electric"], 90), "planta": pokemon(["grass"], 90)}
    resultado = revisar_equipo(["electrico", "planta"], datos, {"amenaza": {"uso": 20}})[0]
    assert resultado["le_pegan"] == ["planta"]
    assert resultado["debiles"] == ["electrico"]


def test_meta_ordenado_limitado_y_mega_habitual(datos):
    uso = {"pokemon": {"charizard": {"uso": 10, "megas": {"charizard-mega-x": 60}},
                       "pelipper": {"uso": 20}, "rillaboom": {"uso": 5}}}
    amenazas = amenazas_del_meta(uso, n=2, datos=datos)
    assert [a["nombre"] for a in amenazas] == ["pelipper", "charizard"]
    assert amenazas[1]["tipos"] == ["fire", "dragon"]
    assert amenazas_del_meta(uso, n=0, datos=datos) == []
    assert amenazas_del_meta({}, datos=datos) == []
    # La API solicitada también carga datos desde las rutas de config.py.
    assert amenazas_del_meta(uso, n=1)[0]["nombre"] == "pelipper"


def test_comparacion_de_velocidad_usa_mega_y_no_base(datos):
    uso = {"gardevoir": {"uso": 20, "megas": {"gardevoir-mega": 90},
                         "spreads": {"Timid:2/0/0/32/0/32": 100}}}
    # Rillaboom máximo 150 supera Gardevoir base 145, pero no la Mega 167.
    resultado = revisar_equipo(["rillaboom"], datos, uso)[0]
    assert resultado["forma"] == "gardevoir-mega"
    assert resultado["mas_rapidos"] == []


def test_tabla_ordena_sin_respuesta_antes_de_riesgo_y_cubierta():
    comunes = {"uso": 20, "le_pegan": [], "mas_rapidos": [], "debiles": []}
    amenazas = [{**comunes, "nombre": n, "forma": n, "estado": estado}
                for n, estado in [("agua", "cubierta"), ("fuego", "sin respuesta"), ("roca", "en riesgo")]]
    filas = construir_filas_amenazas(amenazas)
    assert [f["Estado"] for f in filas] == ["sin respuesta", "en riesgo", "cubierta"]
    assert set(filas[0]) == {"Amenaza", "Uso %", "Le pegan", "Más rápidos", "Débiles", "Estado", "Con"}
