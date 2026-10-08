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

La aplicación permite elegir hasta cinco Pokémon, inspeccionar sus roles y datos
de uso, y comparar recomendaciones, afinidades y debilidades del equipo.

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
la orientación dominante y su spread más usado; excluyen ataques de la categoría
opuesta, conservando los Status. Sin inversión ofensiva se consideran de apoyo;
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
sobre el peso de esa forma. Los datos agregados siguen alimentando el recomendador,
por lo que su puntuación y la evaluación de referencia se mantienen.

`set_probable(..., variante="garchomp-mega-z")`, `roles_de(..., variante=...)` y
`velocidad_real(..., variante=...)` permiten elegir una forma; por defecto usan la
de mayor uso. El set usa exclusivamente sus distribuciones. Una Mega lleva su
Megapiedra y exporta su habilidad si también existe en la base; en caso contrario,
la habilidad más usada de la variante normal. `sets_equipo`, `revisar_equipo` y
`amenazas_del_meta` aceptan `variantes={"garchomp": "garchomp-mega-z"}`.

En la app, el selector «Mega / sin Mega» de cada miembro con variantes Mega cambia
roles, cobertura de amenazas, velocidad y exportación. Con varias Megas se puede
elegir cada forma por separado. Las amenazas usan también las inmunidades por
habilidad de la variante con uso ≥ 50 %. Los JSON antiguos sin `variantes` conservan
el comportamiento anterior; vuelve a ejecutar la importación local de Smogon para
disponer de los selectores. Los tests usan un fixture con variantes y no requieren
regenerar los datos de uso incluidos.
