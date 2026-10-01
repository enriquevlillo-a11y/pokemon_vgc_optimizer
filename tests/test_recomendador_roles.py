import json

from config import ruta_equipos_referencia, ruta_pokemon_datos
from evaluar import evaluar_referencias, resumir
from recomendador import _aportes, es_candidato
from roles import roles_de


def cargar_datos():
    return json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))


def test_roles_de_incineroar():
    roles = roles_de("incineroar", cargar_datos())

    assert roles["fake_out"]
    assert roles["intimidate"]


def test_roles_de_volcarona():
    roles = roles_de("volcarona", cargar_datos())

    assert roles["control_velocidad"]
    assert roles["apoyo"] >= 1


def test_roles_reales_aplican_umbrales_y_no_el_learnset():
    uso = {"pokemon": {"whimsicott": {
        "movimientos": {"tailwind": 19.9, "trick-room": 20},
        "habilidades": {"prankster": 100, "chlorophyll": 0},
    }}}
    roles = roles_de("whimsicott", cargar_datos(), uso)

    assert roles["control_velocidad"]
    assert roles["fuente"] == "uso real"
    assert roles["apoyo"] == 0


def test_redireccion_exige_veinte_por_ciento_de_uso_real():
    uso = {"pokemon": {"volcarona": {
        "movimientos": {"ragepowder": 20, "followme": 19.9},
        "habilidades": {},
    }}}

    assert roles_de("volcarona", cargar_datos(), uso)["redireccion"]


def test_megas_y_formas_solo_combate_no_son_candidatos():
    equipo = []

    assert not es_candidato("una-mega", {"es_mega": True}, equipo)
    assert not es_candidato("aegislash-blade", {"solo_combate": True}, equipo)


def test_v2_mejora_el_puesto_medio_en_equipos_m_c():
    referencias = json.loads(
        ruta_equipos_referencia().read_text(encoding="utf-8")
    )
    referencias_m_c = [r for r in referencias if r["regulacion"] == "M-C"]
    por_regulacion, _ = evaluar_referencias(referencias_m_c, cargar_datos())
    resultados = por_regulacion["M-C"]

    assert resumir(resultados, "v2")["puesto_medio"] < resumir(
        resultados, "v1"
    )["puesto_medio"]


def test_aportes_reconoce_clima_de_uso_real_y_atacante():
    datos = cargar_datos()
    uso_charizard = {"pokemon": {"charizard": {
        "movimientos": {}, "habilidades": {"drought": 70, "blaze": 30},
    }}}

    assert "pone clima/terreno" in _aportes(roles_de("charizard", datos, uso_charizard))
    assert "Atacante" in _aportes(roles_de("floette-eternal", datos))
