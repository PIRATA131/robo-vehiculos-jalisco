# Datos

Procedencia, licencia y transformaciones de cada archivo. Todas las fuentes son
gubernamentales mexicanas de acceso público.

---

## `raw/Estatal-Delitos-2015-2025_jul2026.csv`

| | |
|---|---|
| **Fuente** | Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública (SESNSP) |
| **Conjunto** | Incidencia delictiva del fuero común, nueva metodología |
| **Portal** | https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva |
| **Corte** | Julio de 2026 · cubre 2015–2025 |
| **Dimensiones** | 34 496 filas × 19 columnas |
| **Codificación** | `latin-1` (no UTF-8) |
| **Modificaciones** | **Ninguna.** Se incluye tal como se descargó |

### Estructura

`Año`, `Clave_Ent`, `Entidad`, `Bien jurídico afectado`, `Tipo de delito`,
`Subtipo de delito`, `Modalidad`, y luego doce columnas mensuales de `Enero` a `Diciembre`.

El total anual se obtiene **sumando las doce columnas de meses**. Ojo con los años parciales.

Para este proyecto interesa `Subtipo de delito == "Robo de vehículo automotor"`, que se
desagrega en seis modalidades: coche de cuatro ruedas, motocicleta y embarcaciones, cada una
con y sin violencia.

```python
import pandas as pd
df = pd.read_csv("Estatal-Delitos-2015-2025_jul2026.csv", encoding="latin-1")
```

---

## `processed/Base_Robo_Vehiculos_Jalisco.xlsx`

| | |
|---|---|
| **Fuente** | Instituto de Información Estadística y Geográfica de Jalisco (IIEG) |
| **Conjunto** | Base georreferenciada de incidencia delictiva del estado |
| **Portal** | https://iieg.gob.mx/ns/?page_id=19942 |
| **Periodo** | 1 de julio de 2025 a 31 de julio de 2026 |
| **Dimensiones** | 11 696 filas × 14 columnas, sin valores nulos |
| **Modificaciones** | Filtrada y limpia. Ver abajo |

### Qué se le hizo al archivo original

El archivo original del IIEG trae **52 366 registros de todos los delitos del estado** con
diez columnas. Las transformaciones aplicadas fueron:

1. **Filtrado por delito.** Se conservaron los cuatro delitos de robo vehicular
   (11 696 registros, 22.3 % del total):

   | Delito | Registros |
   |---|---|
   | Robo a vehículos particulares | 5 690 |
   | Robo de motocicleta | 3 788 |
   | Robo de autopartes | 1 361 |
   | Robo a interior de vehículos | 857 |

2. **Limpieza de `hora`.** La columna mezclaba tres formatos: texto `HH:MM`, fracción decimal
   de Excel (`0.458333333` → 11:00, se multiplica por 24) y notación científica. El literal
   `N.D.` se convirtió a nulo. Todo quedó normalizado a `HH:MM` en 24 horas.

3. **Exclusión de registros sin coordenadas.** 125 registros (0.23 %), que no pueden
   participar del análisis espacial.

4. **Columnas derivadas añadidas:**
   - `id_registro` — consecutivo asignado en la limpieza, ordenado por fecha y hora
   - `categoria` — agrupación propia: «Robo del vehículo» (particulares + motocicleta,
     9 478 casos) contra «Robo a/desde el vehículo» (autopartes + interiores, 2 218)
   - `clave_inegi` — clave de 5 dígitos: `14` + municipio de 3 dígitos
     (Guadalajara = 14039, Zapopan = 14120)

> **No se filtraron outliers**, y la decisión es deliberada: en incidencia delictiva un
> registro atípico —una colonia con concentración inusual, una hora con un pico marcado— no
> es ruido que convenga eliminar, es la señal que se busca.

### Columnas

| Columna | Descripción |
|---|---|
| `id_registro` | Consecutivo asignado en la limpieza |
| `fecha` | Día del robo |
| `hora` | Hora del robo, `HH:MM` en 24 h |
| `delito` | Uno de los cuatro tipos de robo vehicular |
| `categoria` | «Robo del vehículo» o «Robo a/desde el vehículo» |
| `bien_afectado` | Bien jurídico afectado (siempre «El patrimonio») |
| `municipio` | Municipio del hecho |
| `clave_ent`, `clave_mun`, `clave_inegi` | Claves geoestadísticas |
| `colonia` | Colonia del hecho |
| `zona_geografica` | `AMG` (Área Metropolitana de Guadalajara) o `Interior` |
| `x`, `y` | Longitud y latitud, EPSG:4326 |

La hoja `Diccionario` del propio archivo repite esta descripción.

### Nota sobre privacidad

Estos registros provienen de un conjunto de datos abiertos que el IIEG publica sin
identificadores personales: no contienen nombres, placas ni datos de víctimas. Lo que sí
conservan es la **ubicación precisa de cada hecho**, igual que en la fuente original.

En una entrega previa de la materia se produjeron versiones anonimizadas de esta base con
*k*-anonimato (*k* = 5), aplicando seudonimización de identificadores, generalización de
fecha y hora, supresión de colonias con menos de cinco casos y microagregación de
coordenadas a centroides de colonia. Esas versiones **no se incluyen aquí** porque el
análisis espacial de H3 necesita la precisión completa, pero son la opción correcta si
alguien quisiera republicar los datos a nivel de registro en otro contexto.

---

## CONAPO — se descarga sola, no está en el repositorio

| | |
|---|---|
| **Fuente** | Consejo Nacional de Población (CONAPO) |
| **Conjunto** | Índice de marginación urbana por colonia 2020 |
| **Portal** | https://www.gob.mx/conapo/documentos/indices-de-marginacion-2020-284372 |
| **Base** | Censo de Población y Vivienda 2020 |
| **Peso** | ~80 MB entre la base y la cartografía |

El cuaderno y `scripts/descargar_conapo.py` la bajan automáticamente de estas dos URLs:

```
https://conapo.segob.gob.mx/work/models/CONAPO/Datos_Abiertos/Colonia/IMC_2020.zip
https://conapo.segob.gob.mx/work/models/CONAPO/Datos_Abiertos/Colonia/imc2020_shp.zip
```

No se incluye en el repositorio por su peso y porque conviene tomarla siempre de la fuente.

### Por qué el nivel colonia y no AGEB

CONAPO publica el índice en ambos niveles. Se eligió **colonia** por dos razones:

1. El archivo de AGEB (`IMU_2020.zip`) publica el índice **pero no su geometría**, de modo
   que cruzarlo con las coordenadas de los robos exigiría descargar además el Marco
   Geoestadístico del INEGI. El de colonia sí incluye cartografía digital (`imc2020_shp.zip`).
2. La base del IIEG ya registra la colonia de cada hecho, así que el nivel colonia coincide
   con la granularidad natural de los datos.

Jalisco aporta 4 397 polígonos de colonia, de los cuales 1 974 están en el AMG.

### ⚠️ La escala del índice está invertida

El campo numérico **`IM_2020` corre al revés de lo que sugiere su nombre**: un valor alto
significa marginación **baja**.

Promedios **a nivel nacional** (las 74 226 colonias del país):

| Grado `GM_2020` | `IM_2020` promedio | % hacinamiento | % sin educación básica |
|---|---|---|---|
| Muy bajo | 153.59 | 7.46 | 8.97 |
| Bajo | 151.06 | 17.33 | 19.64 |
| Medio | 148.61 | 25.96 | 29.35 |
| Alto | 145.83 | 33.12 | 37.59 |
| Muy alto | 139.42 | 44.79 | 48.43 |

Los indicadores crudos confirman que el **grado** `GM_2020` corre en el sentido habitual
—el hacinamiento sube de 7.5 % a 44.8 % conforme empeora el grado—, mientras que el **índice
numérico** baja. Restringido a Jalisco el patrón se mantiene con niveles algo menores: de
5.99 % a 38.00 %.

Todo el análisis de este proyecto usa el grado. La celda 5 del cuaderno y
`scripts/descargar_conapo.py` reproducen esta comprobación.

### Columnas relevantes

| Columna | Descripción |
|---|---|
| `CVE_COL` | Clave de colonia, usada para el cruce |
| `COLONIA`, `NOM_MUN`, `CVE_ENT` | Nombre de colonia, municipio y clave de entidad (`14` = Jalisco) |
| `POBTOT` | Población total de la colonia, Censo 2020 |
| `GM_2020` | Grado de marginación: Muy bajo / Bajo / Medio / Alto / Muy alto |
| `IM_2020` | Índice numérico — **escala invertida**, ver arriba |
| `OVHAC` | % de viviendas con hacinamiento |
| `SBASC` | % de población de 15+ sin educación básica |
| `geometry` | Polígono de la colonia (en el shapefile) |

El shapefile viene en proyección **MEXICO_ITRF_2008_LCC** y hay que reproyectarlo a
`EPSG:4326` para cruzarlo con las coordenadas del IIEG. El cuaderno lo hace con `.to_crs()`.

---

## Archivo que genera el análisis

`Base_Robo_Vehiculos_Jalisco_con_Marginacion.xlsx` — las 14 columnas originales del IIEG más
nueve de CONAPO (`grado_marg_2020`, `indice_marg_2020`, `pob_colonia_2020`,
`pct_hacinamiento`, `pct_sin_basica`, entre otras). Incluye una hoja `Diccionario_marginacion`
que repite la advertencia de la escala invertida.

No está en el repositorio porque es un producto derivado: lo escribe la celda 7 del cuaderno.
