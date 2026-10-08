export const Moves: {[id: string]: MoveData} = {
 rockslide: {
  name: "Rock Slide", type: "Rock", category: "Physical",
  basePower: 75, priority: 0, target: "allAdjacentFoes",
  secondary: { chance: 30, basePower: 999, name: "Wrong" },
  onHit() { return {name: "Not a move", basePower: 123}; },
 },
 protect: {name: "Protect", type: "Normal", category: "Status", basePower: 0, priority: 4, target: "self"},
 fakeout: {name: "Fake Out", type: "Normal", category: "Physical", basePower: 40, priority: 3, target: "normal"},
 partingshot: {name: "Parting Shot", type: "Dark", category: "Status", basePower: 0, priority: 0, target: "normal"},
 flareblitz: {name: "Flare Blitz", type: "Fire", category: "Physical", basePower: 120, priority: 0, target: "normal"},
 throatchop: {name: "Throat Chop", type: "Dark", category: "Physical", basePower: 80, priority: 0, target: "normal"},
};
