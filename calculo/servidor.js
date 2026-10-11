'use strict';

// Protocolo JSONL: una respuesta por línea, también para lotes.
const readline = require('node:readline');
const {Generations, Pokemon, Move, Field, calculate} = require('@smogon/calc');
const gen = Generations.get(0);
const id = value => String(value).toLowerCase().replace(/[^a-z0-9]/g, '');
const STATS = {hp: 'hp', attack: 'atk', defense: 'def', 'special-attack': 'spa',
  'special-defense': 'spd', speed: 'spe', atk: 'atk', def: 'def', spa: 'spa', spd: 'spd', spe: 'spe'};

function tabla(valores = {}, boosts = false) {
  if (!valores || typeof valores !== 'object' || Array.isArray(valores)) {
    throw new Error('Los puntos y boosts deben ser objetos de estadísticas.');
  }
  const resultado = {};
  for (const [clave, valor] of Object.entries(valores)) {
    if (!STATS[clave] || !Number.isInteger(valor) || valor < (boosts ? -6 : 0) || valor > (boosts ? 6 : 32)) {
      throw new Error(`${boosts ? 'Boost' : 'Puntos'} inválidos: ${clave}=${valor}.`);
    }
    resultado[STATS[clave]] = valor;
  }
  if (!boosts && Object.values(resultado).reduce((a, b) => a + b, 0) > 66) {
    throw new Error('El máximo total de puntos Champions es 66.');
  }
  return resultado;
}

function pokemon(entrada) {
  if (!entrada || typeof entrada !== 'object' || Array.isArray(entrada)) {
    throw new Error('Falta el Pokémon atacante o defensor.');
  }
  const especie = entrada.especie ?? entrada.name;
  const ficha = gen.species.get(id(especie));
  if (!ficha) throw new Error(`Especie inexistente en Champions: ${especie}.`);
  const naturaleza = entrada.naturaleza ?? entrada.nature ?? 'Serious';
  if (!gen.natures.get(id(naturaleza))) throw new Error(`Naturaleza inexistente: ${naturaleza}.`);
  const objeto = entrada.objeto ?? entrada.item;
  const habilidad = entrada.habilidad ?? entrada.ability;
  if (objeto && !gen.items.get(id(objeto))) throw new Error(`Objeto inexistente en Champions: ${objeto}.`);
  if (habilidad && !gen.abilities.get(id(habilidad))) throw new Error(`Habilidad inexistente en Champions: ${habilidad}.`);
  const estado = entrada.estado ?? entrada.status ?? '';
  if (!['', 'brn', 'par', 'psn', 'tox', 'slp', 'frz'].includes(estado)) throw new Error(`Estado inválido: ${estado}.`);
  const p = new Pokemon(gen, ficha.name, {
    level: 50, nature: gen.natures.get(id(naturaleza)).name,
    evs: tabla(entrada.puntos ?? entrada.evs), boosts: tabla(entrada.boosts, true),
    item: objeto ? gen.items.get(id(objeto)).name : undefined,
    ability: habilidad ? gen.abilities.get(id(habilidad)).name : undefined,
    status: estado,
  });
  const ps = entrada.ps_actuales ?? entrada.curHP;
  if (ps !== undefined) {
    if (!Number.isInteger(ps) || ps < 1 || ps > p.maxHP()) {
      throw new Error(`PS actuales inválidos: ${ps}; deben estar entre 1 y ${p.maxHP()}.`);
    }
    p.originalCurHP = ps;
  }
  return p;
}

function campo(entrada = {}) {
  const weather = entrada.clima ?? entrada.weather;
  const terrain = entrada.terreno ?? entrada.terrain;
  if (weather && !['Sun', 'Rain', 'Sand', 'Hail', 'Snow', 'Harsh Sunshine', 'Heavy Rain', 'Strong Winds'].includes(weather)) {
    throw new Error(`Clima inválido: ${weather}.`);
  }
  if (terrain && !['Electric', 'Grassy', 'Misty', 'Psychic'].includes(terrain)) throw new Error(`Terreno inválido: ${terrain}.`);
  return new Field({
    gameType: 'Doubles', weather: weather || undefined, terrain: terrain || undefined,
    attackerSide: {isHelpingHand: entrada.helping_hand ?? entrada.isHelpingHand ?? false},
    defenderSide: {
      isReflect: entrada.reflect ?? entrada.isReflect ?? false,
      isLightScreen: entrada.light_screen ?? entrada.isLightScreen ?? false,
      isAuroraVeil: entrada.aurora_veil ?? entrada.isAuroraVeil ?? false,
      isFriendGuard: entrada.friend_guard ?? entrada.isFriendGuard ?? false,
    },
  });
}

function resolver(peticion) {
  try {
    if (!peticion || typeof peticion !== 'object' || Array.isArray(peticion)) throw new Error('La petición debe ser un objeto JSON.');
    // Catálogo de la versión instalada: Python valida sin otra llamada por cálculo.
    if (peticion.catalogo === true) {
      return {ok: true, especies: Array.from(gen.species, s => s.name), movimientos: Array.from(gen.moves, m => m.name)};
    }
    const atacante = pokemon(peticion.atacante);
    const defensor = pokemon(peticion.defensor);
    const ficha = gen.moves.get(id(peticion.movimiento));
    if (!ficha) throw new Error(`Movimiento inexistente en Champions: ${peticion.movimiento}.`);
    if (peticion.isSpread !== undefined && typeof peticion.isSpread !== 'boolean') throw new Error('isSpread debe ser true o false.');
    // calc determina el área por target; overrides se conserva al clonar Move.
    const overrides = peticion.isSpread === undefined ? {} : {
      target: peticion.isSpread ? 'allAdjacentFoes' : 'normal',
    };
    const movimiento = new Move(gen, ficha.name, {ability: atacante.ability, item: atacante.item, overrides});
    const field = campo(peticion.campo);
    const respuesta = {
      ok: true, min: 0, max: 0, ps_defensor: defensor.maxHP(), porcentaje_min: 0, porcentaje_max: 0,
      ko: 'sin daño', descripcion: `${atacante.name} usa ${movimiento.name}: sin daño`,
      stats_atacante: {...atacante.rawStats}, stats_defensor: {...defensor.rawStats},
    };
    if (movimiento.category === 'Status' || !movimiento.bp) return respuesta;
    const resultado = calculate(gen, atacante, defensor, movimiento, field);
    const [min, max] = resultado.range();
    return {...respuesta, min, max,
      porcentaje_min: min * 100 / defensor.maxHP(), porcentaje_max: max * 100 / defensor.maxHP(),
      ko: resultado.kochance().text, descripcion: resultado.desc()};
  } catch (error) {
    return {ok: false, error: `No se pudo calcular el daño: ${error.message}`};
  }
}

const lineas = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
lineas.on('line', linea => {
  let respuesta;
  try {
    const peticion = JSON.parse(linea);
    respuesta = Array.isArray(peticion) ? peticion.map(resolver) : resolver(peticion);
  } catch (error) {
    respuesta = {ok: false, error: `JSON inválido: ${error.message}`};
  }
  // Evita acumular respuestas si el consumidor procesa lotes lentamente.
  if (!process.stdout.write(JSON.stringify(respuesta) + '\n')) {
    lineas.pause();
    process.stdout.once('drain', () => lineas.resume());
  }
});
