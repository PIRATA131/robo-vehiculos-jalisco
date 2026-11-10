# -*- coding: utf-8 -*-
"""
Descarga el Índice de Marginación Urbana por colonia 2020 (CONAPO).

Baja la base de datos y la cartografía digital, las descomprime y comprueba que el
shapefile se pueda leer. Si los archivos ya existen no vuelve a descargarlos.

Uso:
    python scripts/descargar_conapo.py [--destino data/raw/conapo]

Fuente oficial:
    https://www.gob.mx/conapo/documentos/indices-de-marginacion-2020-284372
"""
import argparse
import pathlib
import sys
import urllib.request
import zipfile

URLS = {
    "IMC_2020.zip": (
        "https://conapo.segob.gob.mx/work/models/CONAPO/"
        "Datos_Abiertos/Colonia/IMC_2020.zip"),
    "imc2020_shp.zip": (
        "https://conapo.segob.gob.mx/work/models/CONAPO/"
        "Datos_Abiertos/Colonia/imc2020_shp.zip"),
}


_ultimo_pct = [-1]


def barra(bloques, tam_bloque, total):
    """Barra de progreso. Se calla si la salida no es una terminal (logs, CI),
    donde el retorno de carro no borra la línea y ensuciaría la salida."""
    if total <= 0 or not sys.stdout.isatty():
        return
    pct = min(100, bloques * tam_bloque * 100 // total)
    if pct == _ultimo_pct[0]:
        return
    _ultimo_pct[0] = pct
    hechos = pct // 4
    sys.stdout.write("\r    [%s%s] %3d %%" % ("#" * hechos, "." * (25 - hechos), pct))
    sys.stdout.flush()


def descargar(destino: pathlib.Path):
    destino.mkdir(parents=True, exist_ok=True)

    for nombre, url in URLS.items():
        archivo = destino / nombre
        if archivo.exists():
            print("  %s ya existe (%.1f MB), se omite"
                  % (nombre, archivo.stat().st_size / 1e6))
        else:
            print("  Descargando %s ..." % nombre)
            _ultimo_pct[0] = -1
            try:
                urllib.request.urlretrieve(url, archivo, barra)
                fin = "\r" if sys.stdout.isatty() else ""
                print("%s    listo: %.1f MB      " % (fin, archivo.stat().st_size / 1e6))
            except Exception as err:
                archivo.unlink(missing_ok=True)
                print("\n  ERROR al descargar %s: %s" % (nombre, err))
                print("  Puedes bajarlo a mano desde:\n    %s" % url)
                return False

        carpeta = destino / archivo.stem
        if not carpeta.exists():
            with zipfile.ZipFile(archivo) as z:
                z.extractall(carpeta)
            print("    descomprimido en %s/" % carpeta.name)

    return True


def comprobar(destino: pathlib.Path):
    """Lee el shapefile y reporta lo que trae para Jalisco."""
    try:
        import geopandas as gpd
    except ImportError:
        print("\n  (geopandas no está instalado; se omite la comprobación)")
        print("  Instálalo con:  pip install -r requirements.txt")
        return

    shps = list((destino / "imc2020_shp").rglob("*.shp"))
    if not shps:
        print("\n  ERROR: no se encontró ningún .shp en la descarga")
        return

    print("\n  Comprobando %s ..." % shps[0].name)
    g = gpd.read_file(shps[0])
    g["CVE_ENT"] = g["CVE_ENT"].astype(str).str.zfill(2)
    jal = g[g["CVE_ENT"] == "14"]

    print("    Polígonos en todo el país : %6d" % len(g))
    print("    Polígonos en Jalisco      : %6d" % len(jal))
    print("    Proyección original       : %s" % g.crs.name)
    print("\n    Recordatorio: IM_2020 tiene la escala INVERTIDA")
    print("    (un valor alto significa marginación BAJA). Usa GM_2020.")

    orden = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
    chk = jal.groupby("GM_2020")[["IM_2020", "OVHAC"]].mean().reindex(orden).round(2)
    chk.columns = ["IM_2020 (índice)", "% hacinamiento"]
    print()
    for linea in chk.to_string().split("\n"):
        print("    " + linea)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--destino", default="data/raw/conapo",
                    help="carpeta donde guardar la descarga (por omisión: data/raw/conapo)")
    args = ap.parse_args()

    destino = pathlib.Path(args.destino)
    print("Índice de Marginación Urbana por colonia 2020 — CONAPO")
    print("Destino: %s\n" % destino.resolve())

    if descargar(destino):
        comprobar(destino)
        print("\nListo.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
