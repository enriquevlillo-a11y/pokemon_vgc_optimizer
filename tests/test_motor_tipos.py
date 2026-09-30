import pytest

from motor_tipos import calcular_defensas


@pytest.mark.parametrize(
    ("tipos", "multiplicadores"),
    [
        (["dragon", "ground"], {"ice": 4, "electric": 0}),
        (["ghost", "fairy"], {"normal": 0, "fighting": 0, "dragon": 0}),
        (["fire", "dark"], {"psychic": 0, "ground": 2}),
        (["grass", "poison"], {"grass": 0.25}),
    ],
)
def test_calcular_defensas(tipos, multiplicadores):
    defensas = calcular_defensas(tipos)

    for tipo, multiplicador in multiplicadores.items():
        assert defensas[tipo] == multiplicador
