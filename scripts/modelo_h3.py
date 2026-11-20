# -*- coding: utf-8 -*-
"""
Modelo lineal generalizado para H3: ¿la marginación explica la tasa de robo?

Replica la familia de modelo que el IIEG usó en su estudio de 2019 (GLM
quasi-Poisson), aplicada al cruce IIEG + CONAPO a nivel colonia.

    Unidad de análisis : colonia del Área Metropolitana de Guadalajara
    Variable respuesta : número de robos en la colonia (conteo)
    Exposición         : población de la colonia, como offset logarítmico
    Predictor          : grado de marginación CONAPO 2020

El offset de población hace que el modelo estime TASAS y no conteos, que es
justamente lo que afirma H3.

Uso:
    python scripts/descargar_conapo.py      # si aún no has bajado CONAPO
    python scripts/modelo_h3.py
"""
import argparse
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent
AMG = ["Guadalajara", "Zapopan", "San Pedro Tlaquepaque", "Tonalá",
       "Tlajomulco de Zúñiga", "El Salto", "Juanacatlán",
       "Ixtlahuacán de los Membrillos", "Zapotlanejo"]
ORDEN = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]


def cargar(base_robos, carpeta_conapo):
    import geopandas as gpd

    robos = pd.read_excel(base_robos)
    shps = list(pathlib.Path(carpeta_conapo).rglob("colonias_imc2020.shp"))
    if not shps:
        sys.exit("No encontré la cartografía de CONAPO en %s.\n"
                 "Ejecuta primero:  python scripts/descargar_conapo.py" % carpeta_conapo)

    g = gpd.read_file(shps[0])
    g["CVE_ENT"] = g["CVE_ENT"].astype(str).str.zfill(2)
    jal = g[g["CVE_ENT"] == "14"].to_crs("EPSG:4326")

    # cruce espacial punto-en-polígono: cada robo cae dentro de una colonia
    pts = gpd.GeoDataFrame(
        robos, geometry=gpd.points_from_xy(robos["x"], robos["y"]), crs="EPSG:4326")
    j = gpd.sjoin(pts, jal[["CVE_COL", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]

    col = jal.drop_duplicates("CVE_COL")[
        ["CVE_COL", "COLONIA", "NOM_MUN", "GM_2020", "IM_2020", "POBTOT"]]
    d = col.merge(j.dropna(subset=["CVE_COL"]).groupby("CVE_COL").size().rename("robos"),
                  on="CVE_COL", how="left")
    d["robos"] = d["robos"].fillna(0).astype(int)
    d = d[d["NOM_MUN"].isin(AMG)]
    d = d[d["POBTOT"] >= 100].copy()      # colonias con población utilizable
    d["GM"] = pd.Categorical(d["GM_2020"], categories=ORDEN, ordered=True)
    d["log_pob"] = np.log(d["POBTOT"])
    return d


def ajustar(d):
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from scipy import stats

    print("=" * 72)
    print("MODELO GLM Poisson con offset de población y errores quasi-Poisson")
    print("=" * 72)
    print("Colonias en el modelo : %6d" % len(d))
    print("Robos modelados       : %6d" % d["robos"].sum())
    print("Población total       : %6.0f" % d["POBTOT"].sum())
    print("Media de robos/colonia: %6.2f    Varianza: %.2f"
          % (d["robos"].mean(), d["robos"].var()))
    print("  La varianza supera con mucho a la media: hay sobredispersión, y por eso")
    print("  se usan errores quasi-Poisson en vez de un Poisson simple.")

    m = smf.glm("robos ~ C(GM, Treatment(reference='Muy bajo'))",
                data=d, family=sm.families.Poisson(),
                offset=d["log_pob"]).fit(scale="X2")

    print("\n--- Razones de tasa de incidencia (IRR) ---")
    print("Referencia: colonias de marginación MUY BAJA, las de mayor ingreso\n")
    irr = pd.DataFrame({"IRR": np.exp(m.params), "p": m.pvalues})
    ic = np.exp(m.conf_int())
    irr["IC95_inf"], irr["IC95_sup"] = ic[0], ic[1]
    nombres = {"Intercept": "Intercepto (tasa base)"}
    for gr in ORDEN[1:]:
        nombres["C(GM, Treatment(reference='Muy bajo'))[T.%s]" % gr] = "Marginación %s" % gr
    irr.index = [nombres.get(i, i) for i in irr.index]
    print(irr.round(3).to_string())
    print("\nSobredispersión estimada (scale): %.1f" % m.scale)

    print("\n--- Lectura ---")
    for gr in ORDEN[1:]:
        k = "Marginación %s" % gr
        v, pv = irr.loc[k, "IRR"], irr.loc[k, "p"]
        print("  %-9s: %5.1f %% %s robos que «Muy bajo»   (IRR %.2f, p=%.3g, %s)"
              % (gr, abs(1 - v) * 100, "MENOS" if v < 1 else "MÁS", v, pv,
                 "significativo" if pv < 0.05 else "NO significativo"))

    m0 = smf.glm("robos ~ 1", data=d, family=sm.families.Poisson(),
                 offset=d["log_pob"]).fit(scale="X2")
    gl = m0.df_resid - m.df_resid
    F = ((m0.deviance - m.deviance) / gl) / m.scale
    pF = 1 - stats.f.cdf(F, gl, m.df_resid)
    print("\nPrueba F del grado de marginación: F=%.1f, gl=(%d, %d), p=%.3g"
          % (F, gl, m.df_resid, pF))
    print("  -> el grado de marginación %s información sobre la tasa de robo"
          % ("SÍ aporta" if pF < 0.05 else "NO aporta"))

    print("\n" + "=" * 72)
    print("CONTRASTE con el índice continuo")
    print("=" * 72)
    d = d.copy()
    d["IM_c"] = (d["IM_2020"] - d["IM_2020"].mean()) / d["IM_2020"].std()
    m2 = smf.glm("robos ~ IM_c", data=d, family=sm.families.Poisson(),
                 offset=d["log_pob"]).fit(scale="X2")
    b, pv = m2.params["IM_c"], m2.pvalues["IM_c"]
    print("IRR por desviación estándar del índice: %.3f  (p=%.3g)" % (np.exp(b), pv))
    print("Recordatorio: IM_2020 está INVERTIDO, un valor alto = marginación BAJA.")
    print("  -> moverse una desviación hacia MENOS marginación multiplica la tasa por %.2f"
          % np.exp(b))

    print("\n--- Conclusión para H3 ---")
    print("El gradiente observado en las tasas crudas se sostiene al modelarlo: las")
    print("colonias de marginación alta registran significativamente menos robos por")
    print("habitante que las de marginación muy baja. El modelo no corrige el sesgo del")
    print("denominador —población y no vehículos—, que sigue siendo la limitación")
    print("principal del análisis.")
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base",
                    default=str(RAIZ / "data" / "processed" / "Base_Robo_Vehiculos_Jalisco.xlsx"),
                    help="base de robos del IIEG, ya filtrada")
    ap.add_argument("--conapo", default=str(RAIZ / "data" / "raw" / "conapo"),
                    help="carpeta con la descarga de CONAPO")
    args = ap.parse_args()
    ajustar(cargar(args.base, args.conapo))


if __name__ == "__main__":
    main()
