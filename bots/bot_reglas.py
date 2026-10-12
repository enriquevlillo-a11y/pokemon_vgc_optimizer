"""Bot C1b de reglas para dobles con cálculo de daño real.

Cada turno puntúa cada acción de cada slot (daño esperado, KO, Fake Out,
Protect, control de velocidad, apoyo, Mega) y elige la mejor combinación de
las dos con un poco de aleatoriedad (softmax), para no ser 100 % predecible.
Conoce el equipo rival completo (hojas abiertas, como en VGC).
"""

import math
import random
from calculo import set_a_calculo, _especie
from importar_showdown import normalizar_id
from velocidad import NATURALEZAS_LENTAS, NATURALEZAS_RAPIDAS, velocidad
from poke_env.battle.double_battle import DoubleBattle
from poke_env.battle.field import Field
from poke_env.battle.move_category import MoveCategory
from poke_env.battle.pokemon_type import PokemonType
from poke_env.battle.side_condition import SideCondition
from poke_env.battle.weather import Weather
from poke_env.player import Player
from poke_env.player.battle_order import (
    DoubleBattleOrder, PassBattleOrder,
)

from .equipos import leer_equipo
from .evaluacion import combinar, valor_golpe, valorar_control_velocidad, velocidad_efectiva

CLIMAS = {Weather.SUNNYDAY: "Sun", Weather.DESOLATELAND: "Sun", Weather.RAINDANCE: "Rain",
          Weather.PRIMORDIALSEA: "Rain", Weather.SANDSTORM: "Sand", Weather.SNOW: "Snow",
          Weather.HAIL: "Snow"}
TERRENOS = {Field.GRASSY_TERRAIN: "Grassy", Field.ELECTRIC_TERRAIN: "Electric",
            Field.MISTY_TERRAIN: "Misty", Field.PSYCHIC_TERRAIN: "Psychic"}
SETUP = {"nastyplot", "swordsdance", "calmmind", "dragondance", "quiverdance", "bulkup"}
REDIRECCION = {"followme", "ragepowder"}


class BotReglas(Player):
    def __init__(self, *args, equipo_propio, equipo_rival, calculadora, temperatura=0.08,
                 solo_dano=False, preview=None, **kwargs):
        super().__init__(*args, team=equipo_propio, **kwargs)
        self.calc = calculadora
        self.temperatura = temperatura
        self.solo_dano = solo_dano
        self.preview = preview  # lista de especies: 2 líderes y 2 de reserva
        datos, nombres = calculadora.datos, calculadora.nombres
        self.sets = {}
        for lado, texto in (("propio", equipo_propio), ("rival", equipo_rival)):
            for base, entrada in leer_equipo(texto, datos).items():
                normal = set_a_calculo(entrada, datos, nombres)
                mega = set_a_calculo(entrada, datos, nombres, megaevolucionado=True)
                self.sets[(lado, normalizar_id(base))] = (normal, mega)
        self._cache = {}

    # ---------- utilidades ----------
    def _set(self, mon, lado, mega=None):
        especie = normalizar_id(mon.species)
        es_mega = "mega" in especie if mega is None else mega
        for (l, base), (normal, megaset) in self.sets.items():
            if l == lado and (especie == base or especie.startswith(base)):
                return megaset if es_mega else normal
        return None

    def _campo(self, battle):
        campo = {}
        for clima in battle.weather:
            if clima in CLIMAS:
                campo["clima"] = CLIMAS[clima]
        for f in battle.fields:
            if f in TERRENOS:
                campo["terreno"] = TERRENOS[f]
        return campo

    def _dano(self, battle, atk_mon, atk_lado, def_mon, def_lado, movimiento, mega_atk=None):
        """Fracción media de PS máximos que quita y rango, o None si no aplica."""
        a, d = self._set(atk_mon, atk_lado, mega_atk), self._set(def_mon, def_lado)
        if a is None or d is None:
            return None
        a = dict(a, boosts={k: v for k, v in atk_mon.boosts.items() if k in ("atk", "def", "spa", "spd", "spe") and v})
        d = dict(d, boosts={k: v for k, v in def_mon.boosts.items() if k in ("atk", "def", "spa", "spd", "spe") and v})
        estado = atk_mon.status.name.lower() if atk_mon.status else ""
        if estado in ("brn", "par", "psn", "tox", "slp", "frz"):
            a["estado"] = estado
        campo = self._campo(battle)
        clave = (str(a), str(d), movimiento, str(campo))
        if clave not in self._cache:
            r = self.calc.calcular({"atacante": a, "defensor": d, "movimiento": movimiento, "campo": campo})
            self._cache[clave] = (r["porcentaje_min"] / 100, r["porcentaje_max"] / 100) if r.get("ok") else None
        return self._cache[clave]

    def _velocidades(self, activos, lado, tailwind):
        """Stats naturales Champions del set abierto + estado actual del combate."""
        velocidades = []
        for mon in activos:
            if mon is None or mon.fainted:
                continue
            entrada = self._set(mon, lado)
            if entrada is None:
                continue
            especie = _especie(entrada["especie"], self.calc.datos)
            naturaleza = entrada["naturaleza"]
            modificador = (1.1 if naturaleza in NATURALEZAS_RAPIDAS else
                           0.9 if naturaleza in NATURALEZAS_LENTAS else 1.0)
            stat = velocidad(especie, self.calc.datos,
                             entrada["puntos"].get("spe", 0), modificador)
            # poke-env distingue objeto desconocido de objeto consumido/retirado.
            objeto = mon.item
            if objeto == "unknown_item":
                objeto = entrada.get("objeto")
            velocidades.append(velocidad_efectiva(
                stat, mon.boosts.get("spe", 0),
                paralizado=bool(mon.status and mon.status.name == "PAR"),
                tailwind=tailwind, scarf=normalizar_id(objeto or "") == "choicescarf",
            ))
        return velocidades

    def _control_velocidad(self, battle, movimiento):
        propio_tw = SideCondition.TAILWIND in battle.side_conditions
        rival_tw = SideCondition.TAILWIND in battle.opponent_side_conditions
        tr = Field.TRICK_ROOM in battle.fields
        activos = valorar_control_velocidad(
            movimiento,
            self._velocidades(battle.active_pokemon, "propio", propio_tw),
            self._velocidades(battle.opponent_active_pokemon, "rival", rival_tw),
            trick_room=tr, tailwind=propio_tw,
        )
        rivales = [m for m in battle.opponent_team.values() if not m.fainted] or battle.opponent_active_pokemon
        equipo = valorar_control_velocidad(
            movimiento,
            self._velocidades([m for m in battle.team.values() if not m.fainted], "propio", propio_tw),
            self._velocidades(rivales, "rival", rival_tw),
            trick_room=tr, tailwind=propio_tw,
        )
        return 0.4 * activos + 0.6 * equipo

    def _amenaza(self, battle, objetivo, lado_objetivo):
        """Lo peor que le pueden hacer los rivales activos a ``objetivo`` (valor de golpe)."""
        if objetivo is None or objetivo.fainted:
            return 0.0
        rivales = battle.opponent_active_pokemon if lado_objetivo == "propio" else battle.active_pokemon
        lado_rival = "rival" if lado_objetivo == "propio" else "propio"
        peor = 0.0
        for r in rivales:
            if r is None or r.fainted:
                continue
            s = self._set(r, lado_rival)
            for nombre in (s or {}).get("movimientos", []):
                rango = self._dano(battle, r, lado_rival, objetivo, lado_objetivo, nombre)
                if rango:
                    peor = max(peor, valor_golpe(rango, objetivo.current_hp_fraction))
        return peor

    def _armor_tail_rival(self, battle):
        for r in battle.opponent_active_pokemon:
            if r is not None and not r.fainted:
                s = self._set(r, "rival")
                if s and normalizar_id(s.get("habilidad") or "") in ("armortail", "queenlymajesty", "dazzling"):
                    return True
        return Field.PSYCHIC_TERRAIN in battle.fields

    # ---------- puntuación de una orden ----------
    def _puntuar(self, battle, i, orden):
        """Devuelve (valor base, {objetivo_id: (rango, ps)}) para una orden del slot i."""
        if isinstance(orden, PassBattleOrder) or orden.order is None:
            return 0.0, {}
        mon = battle.active_pokemon[i]
        aliado = battle.active_pokemon[1 - i]
        if not hasattr(orden.order, "base_power"):  # cambio
            entra = orden.order
            ofensiva = 0.0
            for r in battle.opponent_active_pokemon:
                if r is None or r.fainted:
                    continue
                s = self._set(entra, "propio")
                ofensiva += max((valor_golpe(x, r.current_hp_fraction) for x in (
                    self._dano(battle, entra, "propio", r, "rival", m) for m in (s or {}).get("movimientos", [])) if x), default=0)
            recibe = self._amenaza(battle, entra, "propio")
            if mon is None or mon.fainted:  # cambio forzado: elegir buen enfrentamiento
                return 0.3 * ofensiva - 0.3 * recibe, {}
            # Cambio voluntario: quien entra no ataca este turno y recibe el golpe.
            return -0.3 + 0.1 * ofensiva + 0.6 * (self._amenaza(battle, mon, "propio") - recibe), {}
        mov = orden.order
        mid = mov.id
        mega = orden.mega
        valor, golpes = 0.0, {}
        if mov.category != MoveCategory.STATUS and mov.base_power > 0:
            precision = mov.accuracy if isinstance(mov.accuracy, float) else 1.0
            objetivos = []
            if orden.move_target in (-1, -2):
                return -2.0, {}  # nunca atacar al compañero (salvo casos especiales futuros)
            if orden.move_target in (1, 2):
                r = battle.opponent_active_pokemon[orden.move_target - 1]
                objetivos = [r] if r is not None and not r.fainted else []
            else:  # área o sin objetivo concreto
                objetivos = [r for r in battle.opponent_active_pokemon if r is not None and not r.fainted]
                tgt = mov.target.name if mov.target else ""
                if tgt in ("ALL_ADJACENT", "ALL") and aliado is not None and not aliado.fainted:
                    rango = self._dano(battle, mon, "propio", aliado, "propio", mov.id, mega or None)
                    if rango:
                        valor -= 1.2 * valor_golpe(rango, aliado.current_hp_fraction)
            for r in objetivos:
                rango = self._dano(battle, mon, "propio", r, "rival", mov.id, mega or None)
                if rango:
                    golpes[id(r)] = (rango, r.current_hp_fraction, precision)
            if mid == "fakeout":
                if not mon.first_turn or self._armor_tail_rival(battle):
                    return -1.0, {}
                if not self.solo_dano and objetivos:
                    r = objetivos[0]
                    if PokemonType.GHOST not in r.types:
                        valor += 0.7 * self._amenaza_de(battle, r)
        elif not self.solo_dano:
            amenaza = self._amenaza(battle, mon, "propio")
            if mov.is_protect_move:
                valor += 0.75 * amenaza if mon.protect_counter == 0 else -0.5
            elif mid in ("tailwind", "trickroom"):
                valor += self._control_velocidad(battle, mid)
            elif mid in SETUP:
                valor += 0.45 if amenaza < 0.45 else 0.05
            elif mid == "helpinghand":
                valor += 0.25 if aliado is not None and not aliado.fainted else -1
            elif mid in REDIRECCION:
                valor += 0.6 * self._amenaza(battle, aliado, "propio") if aliado is not None and not aliado.fainted else 0
            elif mid == "partingshot":
                valor += 0.25
            else:
                valor += 0.1
        if mega:
            valor += 0.05
        return valor, golpes

    def _amenaza_de(self, battle, rival):
        """Cuánto daño podría hacer ``rival`` a mi equipo activo (para Fake Out)."""
        peor = 0.0
        s = self._set(rival, "rival")
        for propio in battle.active_pokemon:
            if propio is None or propio.fainted:
                continue
            for nombre in (s or {}).get("movimientos", []):
                rango = self._dano(battle, rival, "rival", propio, "propio", nombre)
                if rango:
                    peor = max(peor, valor_golpe(rango, propio.current_hp_fraction))
        return peor

    # ---------- decisiones ----------
    def choose_move(self, battle):
        if not isinstance(battle, DoubleBattle):
            return self.choose_random_move(battle)
        validas = battle.valid_orders
        puntuadas = [[(o, *self._puntuar(battle, i, o)) for o in validas[i]] for i in range(2)]
        candidatas = []
        for o1, v1, g1 in puntuadas[0] or [(PassBattleOrder(), 0, {})]:
            for o2, v2, g2 in puntuadas[1] or [(PassBattleOrder(), 0, {})]:
                if not DoubleBattleOrder.join_orders([o1], [o2]):
                    continue
                candidatas.append((v1 + v2 + combinar(g1, g2), o1, o2))
        if not candidatas:
            return self.choose_random_doubles_move(battle)
        candidatas.sort(key=lambda c: -c[0])
        top = candidatas[:12]
        if self.temperatura <= 0:
            _, o1, o2 = top[0]
        else:
            m = top[0][0]
            pesos = [math.exp((c[0] - m) / self.temperatura) for c in top]
            _, o1, o2 = random.choices(top, weights=pesos)[0]
        return DoubleBattleOrder(o1, o2)

    def teampreview(self, battle):
        miembros = list(battle.team.values())
        if self.preview:
            ids = [normalizar_id(m.species) for m in miembros]
            orden = [ids.index(normalizar_id(e)) + 1 for e in self.preview]
            for i in orden:
                miembros[i - 1]._selected_in_teampreview = True
            return "/team " + "".join(map(str, orden))
        rivales = list(battle.teampreview_opponent_team)
        puntos = []
        for idx, mon in enumerate(miembros, 1):
            s = self._set(mon, "propio", mega=True) or {}
            valor = 0.0
            for r in rivales:
                sr = self._set(r, "rival", mega=True) or {}
                hace = max([self._max_frac(s, sr, m) for m in s.get("movimientos", [])] or [0])
                recibe = max([self._max_frac(sr, s, m) for m in sr.get("movimientos", [])] or [0])
                valor += min(hace, 1) - 0.8 * min(recibe, 1)
            puntos.append((valor, idx, mon))
        puntos.sort(key=lambda p: -p[0])
        elegidos = puntos[:4]
        for _, _, mon in elegidos:
            mon._selected_in_teampreview = True
        return "/team " + "".join(str(idx) for _, idx, _ in elegidos)

    def _max_frac(self, a, d, movimiento):
        clave = ("tp", str(a), str(d), movimiento)
        if clave not in self._cache:
            r = self.calc.calcular({"atacante": a, "defensor": d, "movimiento": movimiento})
            self._cache[clave] = (r["porcentaje_min"] + r["porcentaje_max"]) / 200 if r.get("ok") else 0
        return self._cache[clave]
