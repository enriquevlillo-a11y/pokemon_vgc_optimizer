"""Hojas abiertas de Victory Road -> equipos Showdown con el reparto de puntos más usado.

Uso (desde la raíz del repo): python data/equipos_ots/convertir_ots.py data/equipos_ots/frankfurt_2026 data/equipos_ots/frankfurt_2026
Lee crudo.json (texto en inglés y objetos de cada hoja) y escribe un .txt por jugador.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, ".")
from importar_showdown import normalizar_id

S = Path(sys.argv[1]); SALIDA = Path(sys.argv[2])
u = json.load(open("data/reg_m_c/uso_smogon.json"))["pokemon"]
n = json.load(open("data/reg_m_c/nombres.json"))
datos = json.load(open("data/reg_m_c/pokemon_datos.json"))
ETQ = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
MEGA = {"garchompitez": "garchomp-mega-z", "raichunitey": "raichu-mega-y"}

def variante(base, item):
    e = u.get(base) or {}
    vs = e.get("variantes") or {}
    it = normalizar_id(item)
    if it in MEGA and MEGA[it] in vs: return vs[MEGA[it]]
    for k, v in vs.items():
        objetos = {normalizar_id(o) for o in v.get("objetos", {})}
        if it in objetos and ("mega" in k) == ("ite" in it and it not in ("whiteherb",)): return v
    return vs.get(base) or e

def reparto(base, item, naturaleza):
    v = variante(base, item)
    for spread, _ in sorted((v.get("spreads") or {}).items(), key=lambda x: -x[1]):
        nat, pts = spread.split(":")
        if nat == naturaleza:
            return [int(x) for x in pts.split("/")], "smogon"
    # Sin datos: heurística según naturaleza.
    sube = re.search(r"\+(\w+)", naturaleza_txt[naturaleza]).group(1) if naturaleza in naturaleza_txt else "HP"
    idx = {"Atk": 1, "Def": 2, "SpA": 3, "SpD": 4, "Spe": 5}.get(sube, 0)
    pts = [32, 0, 0, 0, 0, 0]
    if idx == 5: pts = [2, 0, 0, 0, 0, 32]; pts[1 if base in fisicos else 3] = 32
    elif idx: pts[idx] = 32; pts[0] = 32; pts[5 if idx in (1, 3) else 4 if idx == 2 else 2] = 2
    return pts, "heurística"

naturaleza_txt = {}
fisicos = set()
crudo = json.load(open(S / "crudo.json"))
SALIDA.mkdir(parents=True, exist_ok=True)
informe = []
for jugador, d in crudo.items():
    bloques, actual = [], None
    for linea in d["texto"].strip().splitlines():
        if actual is None or (not linea.startswith("Ability:") and "(" not in linea and len(actual["mov"]) == 4 and actual.get("nat")):
            actual = {"esp": linea, "mov": []}; bloques.append(actual); continue
        if linea.startswith("Ability: "): actual["hab"] = linea[9:]
        elif re.match(r"\w+\(", linea):
            actual["nat"] = linea.split("(")[0]; naturaleza_txt[actual["nat"]] = linea
        else: actual["mov"].append(linea)
    assert len(bloques) == 6, (jugador, [b["esp"] for b in bloques])
    texto = []
    for b, item in zip(bloques, d["items"]):
        nombre_item = n["objetos"].get(normalizar_id(item), item.replace("-", " ").title())
        base = normalizar_id(b["esp"]).replace("hisui", "-hisui").replace("eternal", "-eternal")
        base = base if base in u or base in datos else normalizar_id(b["esp"])
        if b["nat"] in ("Adamant", "Jolly", "Brave", "Impish", "Careful"): fisicos.add(base)
        pts, fuente = reparto(base, nombre_item, b["nat"])
        evs = " / ".join(f"{p} {e}" for p, e in zip(pts, ETQ) if p)
        texto.append(f"{b['esp']} @ {nombre_item}\nAbility: {b['hab']}\nLevel: 50\nEVs: {evs}\n{b['nat']} Nature\n" + "\n".join("- " + m for m in b["mov"]))
        informe.append(f"{jugador:10s} {b['esp']:16s} {nombre_item:16s} {b['nat']:8s} {evs:32s} {fuente}")
    (SALIDA / f"{jugador}.txt").write_text("\n\n".join(texto) + "\n", encoding="utf-8")
print("\n".join(informe))
