"""Entry scores of the graduates: where federal and for-profit graduates stood in the national Enem distribution.

For the graduates in the IDD microdata of 2022 and 2023 (present at Enade, with an Enade score and a
recovered Enem score), the mean of the four Enem objective tests is placed in the national
distribution of the same mean among Enem 2018 participants who sat the four tests and were not
"treineiros" (most of these graduates took the Enem between 2016 and 2019; the Enem scale is
comparable across years but not identical). In-person courses only. Federal graduates are compared
with private for-profit graduates of the same assessment areas: for-profit graduates are reweighted
to the federal mix of areas.
Outputs: 19_enem_entrada.csv (summary), 19_enem_distribuicao.csv (shares by national percentile band)
"""
import os, re, glob, io, zipfile
import numpy as np, pandas as pd
from config import DADOS, EXTRA, salvar_csv

FED, FINS = 1, 4
PASTAS = [DADOS] + EXTRA


def achar(padrao):
    for d in PASTAS:
        for f in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            if re.search(padrao, f, re.I):
                return f
    return None


def enem2018_cdf():
    cols = ["IN_TREINEIRO", "TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT",
            "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT"]
    f = achar(r"MICRODADOS_ENEM_2018\.csv$")
    if f:
        fonte = f
    else:
        z = zipfile.ZipFile(achar(r"microdados_enem_2018\.zip$"))
        fonte = z.open([n for n in z.namelist() if n.upper().endswith("MICRODADOS_ENEM_2018.CSV")][0])
    hist = np.zeros(1001, dtype=np.int64)
    for ch in pd.read_csv(fonte, sep=";", encoding="latin-1", usecols=cols, chunksize=1_000_000):
        ok = (ch[cols[1:5]] == 1).all(axis=1) & (ch["IN_TREINEIRO"] == 0)
        m = ch.loc[ok, cols[5:]].mean(axis=1).dropna()
        m = m[m > 0]
        hist += np.bincount(np.clip(np.round(m).astype(int), 0, 1000), minlength=1001)
    return np.cumsum(hist) / hist.sum()


def graduados(ano):
    f = max([x for d in PASTAS for x in glob.glob(os.path.join(d, "**", "*"), recursive=True)
             if re.search(rf"microdados_idd_{ano}", x, re.I) and re.search(r"\.(txt|csv)$", x, re.I)], key=os.path.getsize)
    d = pd.read_csv(f, sep=";", encoding="latin-1", low_memory=False)
    d.columns = [c.strip().strip('"').upper() for c in d.columns]
    num = lambda c: pd.to_numeric(d[c].astype(str).str.replace(",", "."), errors="coerce")
    out = pd.DataFrame({"area": num("CO_GRUPO"), "cat": num("CO_CATEGAD"), "mod": num("CO_MODALIDADE"),
                        "pres": num("TP_PRES"), "nota": num("NT_GER")})
    out["enem"] = pd.concat([num(f"ENEM_NT_{k}") for k in ("CN", "CH", "LC", "MT")], axis=1).mean(axis=1, skipna=False)
    out = out[(out.pres == 555) & out.nota.notna() & (out.enem > 0) & (out["mod"] == 1) & out.cat.isin([FED, FINS])]
    return out


def main():
    cdf = enem2018_cdf()
    corte = {p: int(np.searchsorted(cdf, p / 100)) for p in (50, 75, 90)}
    resumo, dist = [], []
    for ano in (2022, 2023):
        g = graduados(ano)
        g["pct"] = cdf[np.clip(np.round(g.enem).astype(int), 0, 1000)] * 100
        areas = sorted(set(g.loc[g.cat == FED, "area"]) & set(g.loc[g.cat == FINS, "area"]))
        g = g[g.area.isin(areas)].copy()
        sf = g[g.cat == FED].area.value_counts(normalize=True)
        sp = g[g.cat == FINS].area.value_counts(normalize=True)
        g["w"] = np.where(g.cat == FED, 1.0, g.area.map(sf) / g.area.map(sp))
        for cat, nome in ((FED, "federal"), (FINS, "private for-profit")):
            x = g[g.cat == cat].sort_values("pct")
            w = x.w / x.w.sum()
            med = float(x.pct.values[np.searchsorted(np.cumsum(w.values), 0.5)])
            resumo.append([ano, nome, len(x), round(float(np.average(x.enem, weights=w)), 1), round(med, 1),
                           round(100 * float(w[x.enem >= corte[90]].sum()), 1), round(100 * float(w[x.enem >= corte[75]].sum()), 1),
                           round(100 * float(w[x.enem < corte[50]].sum()), 1)])
            faixa = np.minimum((x.pct // 5).astype(int), 19)
            s = w.groupby(faixa).sum().reindex(range(20), fill_value=0)
            dist += [[ano, nome, 5 * b, 5 * b + 5, round(100 * float(v), 2)] for b, v in s.items()]
            print(resumo[-1])
    salvar_csv("19_enem_entrada.csv", resumo, ["ano", "grupo", "graduados", "enem_medio", "percentil_mediano",
                                              "pct_10_superiores", "pct_25_superiores", "pct_abaixo_mediana"])
    salvar_csv("19_enem_distribuicao.csv", dist, ["ano", "grupo", "percentil_de", "percentil_ate", "pct_graduados"])
    print("national cut-offs (Enem 2018 mean of four objective tests):", corte)
    print("19 ok")


if __name__ == "__main__":
    main()
