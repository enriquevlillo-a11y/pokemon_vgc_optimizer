from interfaz import construir_filas_recomendaciones, frases_afinidad, opciones_selector


def test_opciones_selector_filtra_y_ordena_por_uso():
    datos = {
        "b": {"es_mega": False, "solo_combate": False},
        "a": {"es_mega": False, "solo_combate": False},
        "mega": {"es_mega": True, "solo_combate": False},
    }
    uso = {"pokemon": {"a": {"uso": 54.06}, "b": {"uso": 2}}}

    assert opciones_selector(datos, uso) == [("a", "a (54.1%)"), ("b", "b (2.0%)")]


def test_construir_filas_incluye_campos_y_limite():
    recomendaciones = [{
        "nombre": "pikachu", "tipos": ["electric"], "aporta": "Fake Out",
        "puntuacion": {"companeros": 3.456, "total": 10.129},
    }]
    uso = {"pokemon": {"pikachu": {"uso": 12.34}}}

    assert construir_filas_recomendaciones(recomendaciones, uso) == [{
        "Pokémon": "pikachu", "Tipos": "electric", "Aporta": "Fake Out",
        "Uso %": 12.3, "Afinidad con el equipo": 3.46, "Total": 10.13,
    }]


def test_frases_afinidad_usa_companeros_y_cero_si_falta():
    uso = {"pokemon": {"rillaboom": {"companeros": {"raichu": 40}}}}

    assert frases_afinidad("raichu", ["rillaboom", "garchomp"], uso) == [
        "Lo llevan el 40 % de los equipos con Rillaboom",
        "Lo llevan el 0 % de los equipos con Garchomp",
    ]
