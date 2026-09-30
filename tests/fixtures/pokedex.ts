export const Pokedex: import('../../../sim/dex-species').SpeciesDataTable = {
  pikachu: {
    name: "Pikachu", types: ["Electric"], baseStats: {hp: 35, atk: 55, def: 40, spa: 50, spd: 50, spe: 90},
    abilities: { 0: "Static", H: "Lightning Rod" }, weightkg: 6,
  },
  mew: {
    name: "Mew", types: ["Psychic"], baseStats: {hp: 100, atk: 100, def: 100, spa: 100, spd: 100, spe: 100},
    abilities: { 0: "Synchronize" }, weightkg: 4, tags: ["Mythical"],
  },
  missingno: {
    name: "Missing No", types: ["Bird"], baseStats: {hp: 1, atk: 1, def: 1, spa: 1, spd: 1, spe: 1},
    abilities: { 0: "None" }, weightkg: 1,
  },
  salamencemega: {
    name: "Salamence-Mega", baseSpecies: "Salamence", forme: "Mega", requiredItem: "Salamencite",
    types: ["Dragon", "Flying"], baseStats: {hp: 95, atk: 145, def: 130, spa: 120, spd: 90, spe: 120},
    abilities: { 0: "Aerilate" }, weightkg: 112.6,
  },
};
