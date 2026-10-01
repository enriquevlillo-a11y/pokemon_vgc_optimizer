import json

from config import ruta_equipos_referencia, ruta_pokemon_datos
from evaluar import evaluar_referencias, resumir
from recomendador import es_candidato
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
