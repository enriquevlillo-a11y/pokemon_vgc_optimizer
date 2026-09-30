import json

import recomendador


def test_prefiere_uso_smogon(monkeypatch, tmp_path):
    smogon = tmp_path / "uso_smogon.json"
    pikalytics = tmp_path / "uso_pikalytics.json"
    smogon.write_text(
        json.dumps({"pokemon": {"pikachu": {"uso": 12.5}}}), encoding="utf-8"
    )
    pikalytics.write_text(json.dumps({"pikachu": 99}), encoding="utf-8")
    monkeypatch.setattr(recomendador, "ruta_uso_smogon", lambda: smogon)
    monkeypatch.setattr(recomendador, "ruta_uso_pikalytics", lambda: pikalytics)

    assert recomendador.cargar_uso() == {"pikachu": 12.5}


def test_sin_fuentes_devuelve_uso_vacio(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        recomendador, "ruta_uso_smogon", lambda: tmp_path / "smogon-inexistente.json"
    )
    monkeypatch.setattr(
        recomendador,
        "ruta_uso_pikalytics",
        lambda: tmp_path / "pikalytics-inexistente.json",
    )

    assert recomendador.cargar_uso() == {}
    assert "se usará uso 0" in capsys.readouterr().out
