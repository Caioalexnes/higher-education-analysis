"""Raw score and value added (IDD) by administrative category, Enade 2019 and 2023.

For each edition:
  - share of courses in grades 4-5 and 1-2 of the Conceito Enade and of the IDD;
  - difference between each category and private for-profit courses in the raw score
    (0.25*FG + 0.75*CE) and in the raw IDD (points above or below the Enem-predicted score),
    relative to the area mean, with 95% intervals from a bootstrap of courses; this comparison
    is superseded by the within-area comparison of script 10;
  - within-area relation between the share of graduates from private secondary schools
    (Enade questionnaire, QE_I17 = B or E) and the raw score / IDD.
The 2019 IDD was computed with the method INEP used until 2021 (see script 13).
Outputs: 02_faixas_<ano>.csv, 02_diferencas_<ano>.csv, 02_origem_<ano>.csv, 02_cursos_<ano>.csv
"""
import csv, io, zipfile, collections, random
import numpy as np
import openpyxl
from config import arq, salvar_csv

BASE_CAT = "Privada com fins lucrativos"
ORDEM = ["Pública Federal", "Pública Estadual", "Comunitária/Confessional", "Privada sem fins lucrativos", BASE_CAT]


def planilha(chave):
    wb = openpyxl.load_workbook(arq(chave), read_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True)
    h = [str(x).strip().replace("  ", " ").rstrip("*").strip() for x in next(it)]
    for r in it:
        if r[0] is not None:
            yield dict(zip(h, r))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def cursos(ano):
    cur = {}
    for r in planilha(f"conceito{ano}"):
        fg, ce = num(r["Nota Bruta - FG"]), num(r["Nota Bruta - CE"])
        cur[str(r["Código do Curso"])] = dict(
            area=r["Código da Área"], cat=r["Categoria Administrativa"], ies=str(r["Código da IES"]),
            part=num(r.get("Nº de Concluintes Participantes")), cf=str(r["Conceito Enade (Faixa)"]),
            nt=(0.25 * fg + 0.75 * ce) if fg is not None and ce is not None else None)
    for r in planilha(f"idd{ano}"):
        d = cur.setdefault(str(r["Código do Curso"]), dict(area=r["Código da Área"], cat=r["Categoria Administrativa"], ies=str(r["Código da IES"])))
        d.update(nenem=num(r["Nº de Concluintes Participantes com nota no Enem"]), idd=num(r["Nota Bruta - IDD"]), idd_f=str(r["IDD (Faixa)"]))
    z = zipfile.ZipFile(arq(f"enade{ano}"))
    qf = [n for n in z.namelist() if n.endswith(".txt") and "QE_I17" in z.open(n).readline().decode("latin-1")][0]
    q = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(io.TextIOWrapper(z.open(qf), encoding="latin-1", newline=""), delimiter=";"):
        if r["QE_I17"]:
            q[r["CO_CURSO"]][r["QE_I17"]] += 1
    for c, cn in q.items():
        if c in cur:
            n = sum(cn.values())
            cur[c].update(nq=n, priv=(cn["B"] + cn["E"]) / n)
    return cur


def dp_aluno_dentro_area(ano, cur):
    z = zipfile.ZipFile(arq(f"enade{ano}"))
    nf = [n for n in z.namelist() if n.endswith(".txt") and "NT_GER" in z.open(n).readline().decode("latin-1")][0]
    by = collections.defaultdict(list)
    for r in csv.DictReader(io.TextIOWrapper(z.open(nf), encoding="latin-1", newline=""), delimiter=";"):
        if r["TP_PRES"] == "555" and r["TP_PR_GER"] == "555":
            try:
                g = float(r["NT_GER"].replace(",", "."))
            except ValueError:
                continue
            a = cur.get(r["CO_CURSO"], {}).get("area")
            if a is not None:
                by[a].append(g)
    n = sum(len(v) for v in by.values())
    ss = sum(((np.array(v) - np.mean(v)) ** 2).sum() for v in by.values())
    return float(np.sqrt(ss / n)), n


def diferencas(rows, key, wkey):
    rows = [v for v in rows if v.get(key) is not None and (v.get(wkey) or 0) > 0 and v["cat"] in ORDEM]
    g = collections.defaultdict(list)
    for v in rows:
        g[v["area"]].append(v)
    acc = collections.defaultdict(lambda: [0.0, 0.0])
    for vs in g.values():
        w = np.array([v[wkey] for v in vs]); y = np.array([v[key] for v in vs]); m = (w * y).sum() / w.sum()
        for v in vs:
            a = acc[v["cat"]]; a[0] += v[wkey] * (v[key] - m); a[1] += v[wkey]
    med = {c: acc[c][0] / acc[c][1] for c in acc if acc[c][1]}
    return {c: med[c] - med[BASE_CAT] for c in med}


def main(B=500):
    random.seed(1)
    for ano in (2019, 2023):
        cur = cursos(ano)
        vals = list(cur.values())
        out = []
        cats = sorted(set(v["cat"] for v in vals if v.get("cat")))
        grupos = [(c, [v for v in vals if v["cat"] == c]) for c in cats]
        grupos.append(("Privadas (todas)", [v for v in vals if v.get("cat") and ("Privada" in v["cat"] or "Comunit" in v["cat"])]))
        for nome, vs in grupos:
            ce = [v for v in vs if v.get("cf") in "12345" and v.get("cf")]
            iv = [v for v in vs if v.get("idd_f") in "12345" and v.get("idd_f")]
            if not ce or not iv:
                continue
            p = lambda L, k, s: round(100 * sum(v[k] in s for v in L) / len(L), 1)
            out.append([nome, len(ce), p(ce, "cf", "45"), p(ce, "cf", "12"), len(iv), p(iv, "idd_f", "45"), p(iv, "idd_f", "12")])
        salvar_csv(f"02_faixas_{ano}.csv", out, ["categoria", "cursos_conceito", "pct_conceito_4_5", "pct_conceito_1_2", "cursos_idd", "pct_idd_4_5", "pct_idd_1_2"])

        dn, di = diferencas(vals, "nt", "part"), diferencas(vals, "idd", "nenem")
        # bootstrap de cursos
        bn, bi = collections.defaultdict(list), collections.defaultdict(list)
        for _ in range(B):
            amostra = [random.choice(vals) for _ in vals]
            a, b = diferencas(amostra, "nt", "part"), diferencas(amostra, "idd", "nenem")
            for c in a:
                bn[c].append(a[c])
            for c in b:
                bi[c].append(b[c])
        out = []
        for c in ORDEM:
            if c in dn and c in di:
                ic = lambda L: (round(float(np.percentile(L, 2.5)), 2), round(float(np.percentile(L, 97.5)), 2))
                out.append([c, round(dn[c], 2), *ic(bn[c]), round(di[c], 2), *ic(bi[c]),
                            round(100 * (1 - di[c] / dn[c]), 1) if dn[c] else None])
        salvar_csv(f"02_diferencas_{ano}.csv", out, ["categoria", "dif_nota_bruta", "ic95_inf", "ic95_sup", "dif_idd_bruto", "ic95_inf", "ic95_sup", "pct_da_diferenca_que_vem_da_entrada"])

        d = [v for v in vals if v.get("cat") in ORDEM and v.get("priv") is not None and v.get("nq", 0) >= 10 and v.get("nt") is not None and v.get("idd") is not None]
        g = collections.defaultdict(list)
        for v in d:
            g[v["area"]].append(v)
        for vs in g.values():
            mx, mn, mi = (np.mean([v[k] for v in vs]) for k in ("priv", "nt", "idd"))
            for v in vs:
                v["x"], v["yn"], v["yi"] = v["priv"] - mx, v["nt"] - mn, v["idd"] - mi
        out = []
        for nome, vs in [("Todas", d)] + [(c, [v for v in d if v["cat"] == c]) for c in ORDEM]:
            x = np.array([v["x"] for v in vs]); yn = np.array([v["yn"] for v in vs]); yi = np.array([v["yi"] for v in vs])
            out.append([nome, len(vs), round(float((x * yn).sum() / (x * x).sum()), 1), round(float(np.corrcoef(x, yn)[0, 1]), 2),
                        round(float((x * yi).sum() / (x * x).sum()), 1), round(float(np.corrcoef(x, yi)[0, 1]), 2)])
        salvar_csv(f"02_origem_{ano}.csv", out, ["grupo", "cursos", "pontos_nota_bruta_por_100pp", "r_nota_bruta", "pontos_idd_por_100pp", "r_idd"])

        salvar_csv(f"02_cursos_{ano}.csv", [[c, v.get("area"), v.get("cat"), v.get("ies"), v.get("part"), v.get("nt"), v.get("cf"), v.get("nenem"), v.get("idd"), v.get("idd_f"), v.get("nq"), v.get("priv")] for c, v in cur.items()],
                   ["curso", "area", "categoria", "ies", "participantes", "nota_bruta", "conceito_faixa", "participantes_com_enem", "idd_bruto", "idd_faixa", "respondentes_qe", "pct_escola_privada"])
        if ano == 2023:
            dp, n = dp_aluno_dentro_area(ano, cur)
            salvar_csv("02_dp_aluno_2023.csv", [[round(dp, 2), n]], ["dp_nota_geral_dentro_da_area", "alunos"])
        print("02", ano, "ok")


if __name__ == "__main__":
    main()
