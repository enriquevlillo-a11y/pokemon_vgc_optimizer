# Optimizador de equipos Pokémon VGC

Este proyecto analiza las debilidades defensivas de un equipo de Pokémon VGC y
recomienda integrantes que complementen su cobertura, teniendo en cuenta además
su uso en el metajuego de Pikalytics.

El recomendador también consulta Smogon para detectar conflictos de campos y
climas, y avisa cuando Psychic Terrain reduce el valor de Fake Out o de otros
movimientos de prioridad. Usa habilidades con al menos 50 % de uso y movimientos
con al menos 20 %; sin datos de uso, consulta las habilidades y el learnset.
Los PESOS de roles y afinidad se conservan: los conflictos de campo descuentan
4 puntos por compañero y los de clima, 2.

La interfaz muestra velocidades máximas y según el spread más usado, calculadas
con la fórmula de Champions a nivel 50. Si una especie megaevoluciona en más del
50 % de sus equipos (sumando sus formas Mega), también muestra la Mega más usada.
La tabla «Amenazas del meta» revisa las 20 especies con mayor uso y presenta
primero aquellas sin respuesta. Considera movimientos de cobertura frecuentes, sin
cálculo de daño; las velocidades no incluyen
habilidades, Scarf ni Tailwind salvo que se pidan explícitamente a `velocidad`.

`python3 evaluar.py` compara v1, v2, v2 + Smogon y v2 + Smogon + antisinergias
con las mismas referencias y PESOS. Ejecuta `python3 -m pytest` para validar
la lógica y la interfaz.

## Instalación

Se necesita Python 3. Instala las dependencias con:

```bash
pip3 install -r requirements.txt
```

## Pipeline de datos

Los scripts se ejecutan en este orden:

1. `python3 obtener_regulacion.py`: genera la lista de Pokémon permitidos.
2. `python3 descargar_pokemon.py`: descarga sus datos desde PokéAPI.
3. `python3 scraper_pikalytics.py`: obtiene los porcentajes de uso de Pikalytics.
4. `python3 recomendador.py`: analiza el equipo y muestra las recomendaciones.

Los tres primeros pasos acceden a servicios externos. No es necesario repetirlos
para usar los datos que ya están incluidos en el repositorio.

## Interfaz web

Instala las dependencias y arranca la interfaz local:

```bash
pip3 install -r requirements.txt
streamlit run app.py
```

La aplicación permite elegir hasta seis Pokémon, inspeccionar sus roles y datos
de uso, y comparar recomendaciones, afinidades y debilidades del equipo.

### Editar sets y ver velocidades/cálculos

En **Sets, velocidades y cálculos**, cada miembro tiene un desplegable **Editar
set** con naturaleza, seis repartos de puntos, objeto, habilidad y cuatro
movimientos. Parte del set probable de `sets.py`, con los ajustes de equipo de
Item Clause y Fake Out; sin uso se emplea el set genérico. Las habilidades y
movimientos proceden de los datos de la especie base y los objetos y nombres
visibles de `nombres.json`. Los cambios se conservan en `st.session_state` por
miembro y variante y se usan al descargar la exportación Showdown. **Volver al
set probable** restaura los valores iniciales para el equipo actual.

Cada stat admite de 0 a 32 puntos. Si la suma supera 66, aparece un aviso en
vivo y se suspende el daño y la exportación hasta corregir el reparto; la
comparación de velocidades sigue disponible.

`analisis_set.velocidades_relevantes(set, datos, uso_smogon, n=20)` compara la
velocidad del set con las 20 especies más usadas y el spread más común de su
variante habitual. Aplica la piedra Mega y Choice Scarf del set propio; las
amenazas usan `velocidad.velocidades_reales`, sin inferir Scarf ni habilidades.
La tabla muestra el orden normal, con **Tailwind** solo para ti (×2), y bajo
**Trick Room** (actúa primero el más lento; la igualdad sigue siendo empate).
Los cortes buscan superar estrictamente al rival con tu naturaleza y objeto:
«Faltan»/«Sobran» son puntos respecto a tu Spe actual. En Trick Room se indica
cuántos quitar o el margen para añadir. «Imposible con esta naturaleza» significa
que ningún valor entre 0 y 32 Spe alcanza ese corte. Se permite redistribuir
otros stats para llegar al corte; si falta un spread rival, se muestra «sin datos».

`analisis_set.calculos_clave(set, datos, uso_smogon, n=20)` enfrenta el set con
los sets probables del top 20. Calcula todos los movimientos en ambos sentidos
en una sola llamada a `Calculadora.calcular_lote` por miembro, y elige el de
mayor daño máximo (mínimo como desempate). Muestra rango porcentual y texto de
KO de la biblioteca. Verde indica OHKO/2HKO **garantizado** solo a tu favor;
rojo, solo a favor del rival. Los cálculos usan Champions a nivel 50, Doubles,
las formas Mega de las piedras y campo vacío, sin añadir clima, terreno,
pantallas ni boosts. Los errores individuales aparecen en «Avisos».

Para habilitar el daño, instala Node 18 o superior y ejecuta desde la raíz:

```bash
npm ci --prefix calculo
```

Si faltan Node o las dependencias de `calculo/node_modules`, la sección muestra
ese comando y el resto de la app continúa funcionando. Las pruebas de daño real
se omiten en ese caso; las de velocidad y edición siguen ejecutándose con
`python -m pytest tests/test_analisis_set.py`.

## Cambiar de regulación

Cada regulación tiene su definición en `data/regulaciones/<regulacion>.json` y
sus datos generados en `data/<regulacion>/`. Para añadir otra regulación:

1. Crea su archivo de definición, incluido el campo `formato_pikalytics`.
2. Cambia `REGULACION_ACTIVA` en `config.py` al nombre del nuevo archivo, sin la
   extensión `.json`.
3. Ejecuta el pipeline en el orden anterior para generar sus datos.

Todos los scripts obtienen las rutas desde `config.py`, por lo que no necesitan
otros cambios al seleccionar una regulación.

### Cobertura y exportación Showdown

La tabla de amenazas considera los movimientos ofensivos con al menos un 20 %
de uso en Smogon y muestra con cuáles responde cada miembro. Sin estadísticas
de un miembro, se aproxima su cobertura con sus tipos propios.

Para habilitar la exportación, ejecuta `python3 importar_showdown.py` en local.
El importador añade `movimientos.json`, los nombres de habilidades y el nombre
original de Showdown de cada especie. No es necesario cambiar la puntuación del
recomendador. Las entradas Champions con `inherit: true` sobrescriben solo sus
campos y usan una caché distinta de los movimientos base.

Puedes seleccionar hasta seis Pokémon y descargar el equipo desde **Exportar
equipo**. Los sets suman el uso de los spreads físicos y especiales para elegir
la orientación dominante y su spread más usado. En variantes, los movimientos
con uso ≥ 50 % se conservan aunque sean de la categoría opuesta; el filtro de
orientación se aplica al resto, conservando los Status. Sin inversión ofensiva se consideran de apoyo;
sin `movimientos.json` no se filtra por categoría. Se elige una habilidad de la
forma base y con Choice Scarf/Band/Specs se omiten Protect y los movimientos
Status conocidos. Además, resuelven objetos
repetidos con Item Clause y conservan los puntos Champions (0 a 32 por stat y
66 en total) en la línea `EVs`. Los repartos que exceden esos límites lanzan
`ValueError`. Si no hay datos de Smogon de algún miembro, se exporta un set
genérico y la app muestra «set genérico (sin datos de uso)». Usa la primera
habilidad, ningún objeto, naturaleza Adamant o Modest según el ataque base
mayor (físico en empate), 32 puntos en ese ataque, 32 en velocidad y 2 en PS.
Lleva Protect si lo aprende y hasta tres ataques de su orientación, priorizando
STAB y luego potencia. Si no quedan objetos alternativos libres para un set
de Smogon, ese miembro se exporta sin objeto.

La validación oficial de los 24 equipos de referencia es opcional. Con una
instalación de Pokémon Showdown preparada, ejecuta:

```bash
SHOWDOWN_DIR=/ruta/a/pokemon-showdown python3 -m pytest tests/test_validador_showdown.py
```

Sin `SHOWDOWN_DIR`, ese test se omite; el resto de pruebas comprueba también los
equipos de Yvar Vlieger y Emilio Forbes, sus seis miembros y los límites de puntos.

La importación de Smogon conserva además `variantes` por especie: uso, habilidades,
objetos, movimientos y spreads de cada entrada original, con porcentajes calculados
sobre el peso de esa forma. Por variante guarda habilidades con uso ≥ 1 %, los
10 objetos más usados, movimientos con uso ≥ 5 % (máximo 20) y los 15 spreads
más usados. Los datos agregados siguen alimentando el recomendador y su lógica
de puntuación usa esa vista agregada. Las referencias de evaluación distinguen
el JSON antiguo del regenerado. Para actualizar el perfil activo con resultados
calculados, ejecuta `python evaluar.py --actualizar-referencia`.

`set_probable(..., variante="garchomp-mega-z")`, `roles_de(..., variante=...)` y
`velocidad_real(..., variante=...)` permiten elegir una forma; por defecto usan la
de mayor uso. El set usa exclusivamente sus distribuciones. Una Mega lleva su
Megapiedra (o el objeto más usado de la variante si falta `objeto_mega` en los
datos) y exporta su habilidad si también existe en la base; en caso contrario,
la habilidad más usada de la variante normal. `sets_equipo`, `revisar_equipo` y
`amenazas_del_meta` aceptan `variantes={"garchomp": "garchomp-mega-z"}`.

En la app, el selector «Mega / sin Mega» de cada miembro con variantes Mega cambia
roles, cobertura de amenazas, velocidad y exportación. Con varias Megas se puede
elegir cada forma por separado. Las amenazas usan también las inmunidades por
habilidad de la variante con uso ≥ 50 %. Los JSON antiguos sin `variantes` conservan
el comportamiento anterior; vuelve a ejecutar la importación local de Smogon para
disponer de los selectores. Los tests usan un fixture con variantes y no requieren
regenerar los datos de uso incluidos.

### Diagnóstico y motivos de recomendación

«Debilidades de tu equipo» aparece antes de las recomendaciones y ordena los
problemas por gravedad e identificador. Detecta carencias de Fake Out, control de
velocidad, Intimidate y atacantes con estadística ofensiva ≥ 120; el control solo
con Icy Wind/Electroweb se considera débil y de gravedad media. También señala
los tipos que golpean superefectivo a tres miembros sin ninguna resistencia o
inmunidad y las amenazas del top 20 sin respuesta o en riesgo.

`diagnostico.debilidades_equipo(...)` y `diagnostico.explicar(equipo, candidato, ...)`
aceptan el catálogo `movimientos` y `variantes={especie: forma}`. Usan las variantes
seleccionadas y las inmunidades de `amenazas._defensas`. «Por qué» explica los
roles, resistencias y mejoras de estado de amenazas que aporta cada candidato.
La app y el CLI calculan los motivos solo para las recomendaciones mostradas.

Fake Out recibe su peso completo cuando el equipo no tiene usuarios, la mitad
cuando tiene uno y cero con dos o más, sin penalización negativa. Si al construir
los sets hay al menos tres usuarios, se retira de los que lo usan en menos del
50 % de su variante y se sustituye según el uso, la orientación y el objeto final.
Los usuarios con uso ≥ 50 % lo conservan, incluso si hay tres o más. El
recomendador avisa cuando un candidato minoritario se suma a dos usuarios.

## Cálculo de daño

Requiere **Node 18 o superior**. Instala la versión fijada `@smogon/calc 0.12.0`
con el lockfile incluido, desde la raíz del repo:

```bash
npm ci --prefix calculo
python calculo.py
python -m pytest
```

`python calculo.py` muestra los duelos de la final de Frankfurt usando los equipos
de `tests/fixtures/final_frankfurt/`. Eruption al sol y en área hace 258–306 sin
objeto; con el Charcoal del fixture hace 312–368 contra Gholdengo.

La API usa Champions (`Generations.get(0)`), nivel 50 y Doubles. Los puntos son
los valores 0–32 de Champions, con un máximo total de 66, sin convertir a EVs.
`Calculadora` inicia un único proceso Node y lo reutiliza hasta salir del contexto:

```python
from calculo import Calculadora, set_a_calculo

with Calculadora() as calculadora:
    atacante = set_a_calculo(
        {"nombre": "garchomp", "objeto": "garchompitez", "habilidad": "roughskin",
         "naturaleza": "Modest", "puntos": {"hp": 2, "special-attack": 32, "speed": 32}},
        calculadora.datos, calculadora.nombres, megaevolucionado=True,
    )
    peticion = {
        "atacante": atacante,
        "defensor": {"especie": "Torkoal", "naturaleza": "Quiet",
                     "puntos": {"hp": 32, "spa": 32, "spd": 2}},
        "movimiento": "Earth Power",
        "campo": {},
    }
    print(calculadora.calcular(peticion))
    resultados = calculadora.calcular_lote([peticion] * 1000)
```

Cada Pokémon admite `especie`, `naturaleza`, `puntos`, `objeto`, `habilidad`,
`boosts` (−6 a +6), `estado` (`brn`, `par`, `psn`, `tox`, `slp`, `frz` o vacío)
y `ps_actuales` (1 a sus PS máximos; por defecto completos). Las estadísticas
usan `hp`, `atk`, `def`, `spa`, `spd`, `spe`; también se aceptan las claves largas
del repo. Los sets con `nombre` se convierten automáticamente; añade
`megaevolucionado=True` al set para aplicar la forma de su piedra. Una especie
Mega explícita conserva su forma y usa su habilidad Mega.

`campo` admite `clima` (por ejemplo `Sun`, `Rain`, `Sand`, `Snow`), `terreno`
(`Electric`, `Grassy`, `Misty`, `Psychic`), `helping_hand`, `reflect`,
`light_screen`, `aurora_veil` y `friend_guard`. Los booleanos de pantallas y
Friend Guard corresponden al lado defensor; Helping Hand al atacante. El clima
se especifica en el campo. `isSpread` se infiere de `movimientos.json` para
`allAdjacentFoes` y `allAdjacent`; una petición con `isSpread=False` calcula
el ataque contra un único objetivo.

Cada respuesta contiene `ok`, `min`, `max`, `ps_defensor` (PS máximos),
`porcentaje_min`, `porcentaje_max` (sobre los PS máximos), `ko`, `descripcion`,
`stats_atacante` y `stats_defensor`. Las estadísticas incluyen puntos y naturaleza,
antes de boosts y otros modificadores. Los movimientos Status o de potencia cero
devuelven daño 0 y `ko="sin daño"`. Las peticiones inválidas devuelven
`{"ok": False, "error": "mensaje en español"}` sin detener el proceso; en un lote
se conserva el orden y cada error ocupa su posición. Python valida especies y
movimientos contra el catálogo Champions de la versión instalada antes de enviar.
Los errores de instalación o comunicación lanzan `RuntimeError`.

El servidor también se puede usar directamente con `node calculo/servidor.js`:
lee un objeto JSON o una lista por línea de stdin y responde una línea JSON.
Los tests de esta capa se omiten si falta `node` o `calculo/node_modules`.
