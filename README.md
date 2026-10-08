# Optimizador de equipos Pokémon VGC

Este proyecto analiza las debilidades defensivas de un equipo de Pokémon VGC y
recomienda integrantes que complementen su cobertura, teniendo en cuenta además
su uso en el metajuego de Pikalytics.

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
equipo**. Los sets usan las opciones más frecuentes de Smogon, resuelven objetos
repetidos con Item Clause y conservan los puntos Champions (0 a 32) en la línea
`EVs`. Si no hay datos de Smogon de algún miembro, la app lo indica y espera a
que estén disponibles para exportar el equipo completo. Si no quedan objetos
alternativos libres, ese miembro se exporta sin objeto.
