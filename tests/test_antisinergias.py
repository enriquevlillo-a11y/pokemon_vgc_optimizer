import json

from antisinergias import antisinergias
from config import ruta_equipos_referencia
from evaluar import evaluar_referencias, resumir
from puntuacion import PESOS, puntuar
from recomendador import obtener_recomendaciones


def test_sneasler_sin_fake_out_de_uso_real_no_recibe_avisos(datos):
    uso = {"sneasler": {"habilidades": {"unburden": 100},
                       "movimientos": {"closecombat": 100, "direclaw": 100, "fakeout": 19.9}}}
    # El learnset incluye Fake Out; Smogon por debajo del umbral lo descarta.
    assert antisinergias(["gardevoir", "indeedee-f"], "sneasler", datos, uso) == ([], 0)


def test_sneasler_actual_supera_umbral_fake_out(datos, uso_smogon):
    # El archivo actual da 47,53 %: se aplica el mismo umbral de 20 % a todos.
    avisos, penalizacion = antisinergias(["gardevoir", "indeedee-f"], "sneasler", datos, uso_smogon)
    assert avisos == ["Psychic Terrain bloquea su Fake Out"]
    assert penalizacion == 0


def test_incineroar_y_rillaboom_con_campo_psiquico(datos, uso_smogon):
    equipo = ["gardevoir", "indeedee-f"]
    avisos, penalizacion = antisinergias(equipo, "incineroar", datos, uso_smogon)
    assert "Psychic Terrain bloquea su Fake Out" in avisos
    assert penalizacion == 0
    assert puntuar(equipo, "incineroar", datos, uso_smogon)["fake"] == 0
    avisos, penalizacion = antisinergias(equipo, "rillaboom", datos, uso_smogon)
    assert "sustituye el campo de indeedee-f" in avisos
    assert penalizacion == 4
    assert puntuar(equipo, "rillaboom", datos, uso_smogon)["antisinergia"] == -4


def test_climas_con_pelipper_y_mega_charizard(datos, uso_smogon):
    for candidato in ["torkoal", "charizard"]:
        avisos, penalizacion = antisinergias(["pelipper"], candidato, datos, uso_smogon)
        assert "sustituye el clima de pelipper" in avisos
        assert penalizacion == 2


def test_habilidad_de_mega_cuenta_solo_con_mayoria(datos):
    uso = {"charizard": {"habilidades": {"blaze": 100}, "megas": {"charizard-mega-y": 50}}}
    assert antisinergias(["pelipper"], "charizard", datos, uso) == ([], 0)
    uso["charizard"]["megas"]["charizard-mega-y"] = 51
    assert antisinergias(["pelipper"], "charizard", datos, uso)[1] == 2


def test_umbrales_reales_y_fallback_a_learnset(datos):
    uso = {"indeedee-f": {"habilidades": {"psychic-surge": 49.9}},
           "incineroar": {"movimientos": {"fake-out": 20}}}
    assert antisinergias(["indeedee-f"], "incineroar", datos, uso) == ([], 0)
    uso["indeedee-f"]["habilidades"]["psychic-surge"] = 50
    assert "Psychic Terrain bloquea su Fake Out" in antisinergias(["indeedee-f"], "incineroar", datos, uso)[0]
    uso["incineroar"]["movimientos"]["fake-out"] = 19.9
    assert antisinergias(["indeedee-f"], "incineroar", datos, uso) == ([], 0)
    assert antisinergias(["pelipper"], "torkoal", datos) == (["sustituye el clima de pelipper"], 2)


def test_candidato_psychic_surge_avisa_sobre_equipo(datos, uso_smogon):
    avisos, _ = antisinergias(["incineroar"], "indeedee-f", datos, uso_smogon)
    assert "Psychic Terrain bloquea el Fake Out de incineroar" in avisos


def test_prioridad_ofensiva_y_avisos_sin_duplicados(datos):
    uso = {"rillaboom": {"movimientos": {"grassy-glide": 20, "protect": 100}, "habilidades": {}}}
    avisos, penalizacion = antisinergias(["indeedee-f", "indeedee"], "rillaboom", datos, uso)
    assert avisos == ["Psychic Terrain bloquea sus movimientos de prioridad"]
    assert penalizacion == 0


def test_no_penaliza_mismo_clima(datos):
    assert antisinergias(["pelipper"], "politoed", datos) == ([], 0)


def test_recomendaciones_muestran_avisos(datos, uso_smogon):
    recomendaciones = obtener_recomendaciones(["gardevoir", "indeedee-f"], datos, uso_smogon)
    incineroar = next(r for r in recomendaciones if r["nombre"] == "incineroar")
    assert "⚠️ Psychic Terrain bloquea su Fake Out" in incineroar["aporta"]


def test_baseline_sin_antisinergias_y_pesos_intactos(datos, uso_smogon):
    assert PESOS == {"fake": 3, "velocidad": 3, "apoyo": 0.5, "intimidate": 2,
                     "anti_intimidate": 1.5, "ofensivo": 1.0, "mega": 1.0,
                     "tipos": 0.3, "companeros": 8, "uso": 0.5}
    equipo = ["gardevoir", "indeedee-f"]
    base = puntuar(equipo, "incineroar", datos, uso_smogon, aplicar_antisinergias=False)
    nuevo = puntuar(equipo, "incineroar", datos, uso_smogon)
    assert base["fake"] == 3
    assert nuevo["total"] == base["total"] - 3


def test_m_c_no_empeora_mas_de_medio_puesto(datos, uso_smogon):
    referencias = json.loads(ruta_equipos_referencia().read_text(encoding="utf-8"))
    referencias = [r for r in referencias if r["regulacion"] == "M-C"]
    por_regulacion, _ = evaluar_referencias(referencias, datos, uso_smogon)
    resultados = por_regulacion["M-C"]
    assert resumir(resultados, "v2_smogon_antisinergias")["puesto_medio"] <= resumir(resultados, "v2_smogon")["puesto_medio"] + 0.5
