"""API compartida de daño Champions (nivel 50), mediante un proceso Node JSONL.

Las peticiones usan atacante, defensor, movimiento, campo e isSpread. Los
Pokémon usan especie, naturaleza, puntos, objeto, habilidad, boosts, estado y
ps_actuales. calcular y calcular_lote devuelven errores como {ok: False, error}.
Los errores de instalación/transporte lanzan RuntimeError. Las estadísticas de
la respuesta son las naturales (antes de boosts, objetos y efectos del campo).
"""

import json
from pathlib import Path
import shutil
import subprocess
from threading import RLock

from importar_showdown import normalizar_id

BASE = Path(__file__).resolve().parent
DIRECTORIO_CALCULO = BASE / "calculo"
DIRECTORIO_DATOS = BASE / "data" / "reg_m_c"
INSTALACION = "Instala Node 18 o superior y ejecuta: npm ci --prefix calculo"
STATS = {"hp": "hp", "attack": "atk", "defense": "def", "special-attack": "spa",
         "special-defense": "spd", "speed": "spe", "atk": "atk", "def": "def",
         "spa": "spa", "spd": "spd", "spe": "spe"}


def _leer_json(nombre):
    return json.loads((DIRECTORIO_DATOS / f"{nombre}.json").read_text(encoding="utf-8"))


def _especie(nombre, datos):
    if not isinstance(nombre, str):
        raise ValueError(f"Especie inválida: {nombre}; debe ser un nombre de Pokémon.")
    if nombre in datos:
        return nombre
    identificador = normalizar_id(nombre)
    for clave, ficha in datos.items():
        if identificador in (normalizar_id(clave), normalizar_id(ficha.get("nombre_showdown", clave))):
            return clave
    raise ValueError(f"Especie inexistente en reg_m_c: {nombre}.")


def set_a_calculo(entrada, datos, nombres, *, megaevolucionado=False):
    """Convierte un set del repo; con megaevolucionado=True aplica su piedra.

    Una especie Mega explícita se conserva. Para un set base, la piedra debe
    corresponder a esa especie; al evolucionar se usa la habilidad de la Mega.
    No modifica el set ni los catálogos recibidos.
    """
    if not isinstance(entrada, dict):
        raise ValueError("El set debe ser un objeto de datos de Pokémon.")
    especie = _especie(entrada.get("nombre", entrada.get("especie", "")), datos)
    if megaevolucionado and not datos[especie].get("es_mega"):
        piedra = entrada.get("objeto") or ""
        if not isinstance(piedra, str):
            raise ValueError("El objeto debe ser un nombre o identificador.")
        objeto = normalizar_id(piedra)
        formas = [clave for clave, ficha in datos.items()
                  if ficha.get("es_mega") and ficha.get("especie_base") == especie
                  and objeto and normalizar_id(ficha.get("objeto_mega") or "") == objeto]
        if formas:
            especie = formas[0]
    ficha = datos[especie]
    nombre_showdown = ficha.get("nombre_showdown")
    if not nombre_showdown:
        raise ValueError(f"Falta nombre_showdown para {especie}; ejecuta importar_showdown.py.")

    def visible(categoria, valor):
        if valor is not None and not isinstance(valor, str):
            raise ValueError(f"Nombre inválido en {categoria}: {valor}.")
        return nombres.get(categoria, {}).get(normalizar_id(valor), valor) if valor else None

    habilidad = entrada.get("habilidad")
    if ficha.get("es_mega"):
        habilidades = ficha.get("habilidades", [])
        if not habilidades:
            raise ValueError(f"Falta la habilidad de la forma Mega {nombre_showdown}.")
        habilidad = habilidades[0]
        if isinstance(habilidad, dict):
            habilidad = habilidad["nombre"]
    resultado = {
        "especie": nombre_showdown, "naturaleza": entrada.get("naturaleza") or "Serious",
        "puntos": _tabla_stats(entrada.get("puntos", {})),
        "objeto": visible("objetos", entrada.get("objeto")),
        "habilidad": visible("habilidades", habilidad),
        "movimientos": [visible("movimientos", m) for m in entrada.get("movimientos", [])],
    }
    for clave in ("boosts", "estado", "ps_actuales"):
        if clave in entrada:
            resultado[clave] = _tabla_stats(entrada[clave], boosts=True) if clave == "boosts" else entrada[clave]
    return resultado


def _tabla_stats(valores, *, boosts=False):
    if not isinstance(valores, dict):
        raise ValueError("Los puntos y boosts deben ser objetos de estadísticas.")
    resultado = {}
    for clave, valor in valores.items():
        if clave not in STATS or type(valor) is not int or not (-6 if boosts else 0) <= valor <= (6 if boosts else 32):
            raise ValueError(f"{'Boost' if boosts else 'Puntos'} inválidos: {clave}={valor}.")
        resultado[STATS[clave]] = valor
    if not boosts and sum(resultado.values()) > 66:
        raise ValueError("El máximo total de puntos Champions es 66.")
    return resultado


class Calculadora:
    """Reutiliza un único Node; admite llamadas en serie desde varios hilos.

    Puede usarse como context manager o cerrarse con cerrar(). La primera
    llamada fuera de un contexto también inicia el servidor. En un lote los
    errores son individuales y se conserva el orden de todas las peticiones.
    """

    def __init__(self, datos=None, nombres=None, movimientos=None):
        self.datos = _leer_json("pokemon_datos") if datos is None else datos
        self.nombres = _leer_json("nombres") if nombres is None else nombres
        self.movimientos = _leer_json("movimientos") if movimientos is None else movimientos
        self._proceso = None
        self._cerrada = False
        self._lock = RLock()
        self._especies = {}
        self._movimientos = {}

    def __enter__(self):
        with self._lock:
            self._iniciar()
        return self

    def __exit__(self, tipo, valor, traceback):
        self.cerrar()

    def _iniciar(self):
        if self._cerrada:
            raise RuntimeError("La calculadora está cerrada.")
        if self._proceso is not None:
            if self._proceso.poll() is not None:
                raise RuntimeError("El servidor de cálculo terminó inesperadamente.")
            return
        node = shutil.which("node")
        if not node:
            raise RuntimeError(f"No se encontró node en el PATH. {INSTALACION}")
        if not (DIRECTORIO_CALCULO / "node_modules" / "@smogon" / "calc" / "package.json").is_file():
            raise RuntimeError(f"Falta calculo/node_modules. {INSTALACION}")
        try:
            self._proceso = subprocess.Popen(
                [node, str(DIRECTORIO_CALCULO / "servidor.js")],
                cwd=BASE, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            )
            catalogo = self._enviar({"catalogo": True})
            if not catalogo.get("ok"):
                raise RuntimeError(catalogo.get("error", "No se pudo cargar el catálogo Champions."))
            self._especies = {normalizar_id(n): n for n in catalogo["especies"]}
            self._movimientos = {normalizar_id(n): n for n in catalogo["movimientos"]}
        except (OSError, RuntimeError, KeyError) as error:
            self.cerrar()
            raise RuntimeError(f"No se pudo iniciar el servidor de cálculo: {error}. {INSTALACION}") from error

    def _enviar(self, peticion):
        try:
            texto = json.dumps(peticion, ensure_ascii=False, allow_nan=False)
            self._proceso.stdin.write(texto + "\n")
            self._proceso.stdin.flush()
            linea = self._proceso.stdout.readline()
            if not linea:
                raise RuntimeError("El servidor de cálculo terminó sin responder.")
            return json.loads(linea)
        except (OSError, ValueError) as error:
            raise RuntimeError(f"Error de comunicación con el servidor de cálculo: {error}") from error

    def _preparar(self, peticion):
        if not isinstance(peticion, dict):
            raise ValueError("La petición debe ser un objeto JSON.")
        preparada = dict(peticion)
        for lado in ("atacante", "defensor"):
            pokemon = peticion.get(lado)
            if not isinstance(pokemon, dict):
                raise ValueError(f"Falta el Pokémon {lado}.")
            if "nombre" in pokemon:
                pokemon = set_a_calculo(pokemon, self.datos, self.nombres,
                                        megaevolucionado=pokemon.get("megaevolucionado", False))
            else:
                pokemon = dict(pokemon)
            especie = pokemon.get("especie", "")
            if not isinstance(especie, str) or normalizar_id(especie) not in self._especies:
                raise ValueError(f"Especie inexistente en Champions: {especie}.")
            pokemon["especie"] = self._especies[normalizar_id(especie)]
            pokemon["puntos"] = _tabla_stats(pokemon.get("puntos", {}))
            if "boosts" in pokemon:
                pokemon["boosts"] = _tabla_stats(pokemon["boosts"], boosts=True)
            for clave, categoria in (("objeto", "objetos"), ("habilidad", "habilidades")):
                valor = pokemon.get(clave)
                if valor is not None and not isinstance(valor, str):
                    raise ValueError(f"{clave.capitalize()} inválida: debe ser un nombre o identificador.")
                if valor:
                    pokemon[clave] = self.nombres.get(categoria, {}).get(normalizar_id(valor), valor)
            preparada[lado] = pokemon
        movimiento = peticion.get("movimiento", "")
        if not isinstance(movimiento, str) or normalizar_id(movimiento) not in self._movimientos:
            raise ValueError(f"Movimiento inexistente en Champions: {movimiento}.")
        identificador = normalizar_id(movimiento)
        preparada["movimiento"] = self._movimientos[identificador]
        if "isSpread" not in preparada:
            objetivo = self.movimientos.get(identificador, {}).get("objetivo")
            if objetivo is not None:
                preparada["isSpread"] = objetivo in ("allAdjacentFoes", "allAdjacent")
        elif type(preparada["isSpread"]) is not bool:
            raise ValueError("isSpread debe ser true o false.")
        # Comprueba serialización antes de tocar stdin, también en lotes mixtos.
        json.dumps(preparada, allow_nan=False)
        return preparada

    def calcular(self, peticion):
        with self._lock:
            self._iniciar()
            try:
                preparada = self._preparar(peticion)
            except (ValueError, TypeError) as error:
                return {"ok": False, "error": str(error)}
            return self._enviar(preparada)

    def calcular_lote(self, peticiones):
        with self._lock:
            self._iniciar()
            resultados, validas, indices = [], [], []
            for peticion in peticiones:
                try:
                    validas.append(self._preparar(peticion))
                    indices.append(len(resultados))
                    resultados.append(None)
                except (ValueError, TypeError) as error:
                    resultados.append({"ok": False, "error": str(error)})
            if validas:
                respuestas = self._enviar(validas)
                if not isinstance(respuestas, list) or len(respuestas) != len(validas):
                    raise RuntimeError("Respuesta de lote inválida del servidor de cálculo.")
                for indice, respuesta in zip(indices, respuestas):
                    resultados[indice] = respuesta
            return resultados

    def cerrar(self):
        with self._lock:
            self._cerrada = True
            proceso = self._proceso
            if proceso is None:
                return
            try:
                proceso.stdin.close()
            except OSError:
                pass
            try:
                proceso.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proceso.terminate()
                try:
                    proceso.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                    proceso.wait()
            finally:
                proceso.stdout.close()


def _leer_equipo(ruta, datos, nombres):
    """Lector de los fixtures Showdown de la demostración de Frankfurt."""
    etiquetas = {"HP": "hp", "Atk": "attack", "Def": "defense", "SpA": "special-attack",
                 "SpD": "special-defense", "Spe": "speed"}
    equipo = {}
    for bloque in ruta.read_text(encoding="utf-8").strip().split("\n\n"):
        lineas = bloque.splitlines()
        especie, _, objeto = lineas[0].partition(" @ ")
        entrada = {"nombre": _especie(especie, datos), "objeto": objeto, "movimientos": [], "puntos": {}}
        for linea in lineas[1:]:
            if linea.startswith("Ability: "):
                entrada["habilidad"] = linea.removeprefix("Ability: ")
            elif linea.startswith("EVs: "):
                for reparto in linea.removeprefix("EVs: ").split(" / "):
                    cantidad, stat = reparto.split()
                    entrada["puntos"][etiquetas[stat]] = int(cantidad)
            elif linea.endswith(" Nature"):
                entrada["naturaleza"] = linea.removesuffix(" Nature")
            elif linea.startswith("- "):
                entrada["movimientos"].append(linea[2:])
        equipo[entrada["nombre"]] = set_a_calculo(entrada, datos, nombres, megaevolucionado=True)
    return equipo


def main():
    fixtures = BASE / "tests" / "fixtures" / "final_frankfurt"
    with Calculadora() as calculadora:
        eric = _leer_equipo(fixtures / "eric.txt", calculadora.datos, calculadora.nombres)
        sebastian = _leer_equipo(fixtures / "sebastian.txt", calculadora.datos, calculadora.nombres)
        duelos = [
            (sebastian["torkoal"], eric["gholdengo"], "Eruption", {"clima": "Sun"}),
            (sebastian["sylveon"], eric["garchomp"], "Hyper Voice", {}),
            (eric["garchomp"], sebastian["torkoal"], "Earth Power", {}),
            (eric["gholdengo"], sebastian["sylveon"], "Make It Rain", {}),
            (sebastian["garchomp"], eric["gholdengo"], "Draco Meteor", {}),
        ]
        peticiones = [{"atacante": a, "defensor": d, "movimiento": m, "campo": c} for a, d, m, c in duelos]
        print("Final de Frankfurt · Champions · nivel 50 · Doubles")
        for respuesta in calculadora.calcular_lote(peticiones):
            print(respuesta["descripcion"] if respuesta["ok"] else respuesta["error"])


if __name__ == "__main__":
    main()
