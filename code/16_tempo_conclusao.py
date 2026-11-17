"""Time from entry to the Enade exam, federal and private for-profit graduates, Enade 2019 and 2023.

The Enade microdata give, for each enrolled graduating student, the year of entry in the
undergraduate programme (ANO_IN_GRAD). Time to graduation is approximated by the Enade year minus
the year of entry. Courses are classified by the administrative category and assessment area of the
Conceito Enade spreadsheet, as in the other scripts. Federal graduates are compared with private
for-profit graduates of the same area: the for-profit figures are reweighted to the federal mix of
areas (area weights equal to the share of federal students in each area, as in equation (1) of the
paper). Variants: all courses or in-person courses only; all records or only records with at least
two years between entry and the exam (shorter spans are mostly transfers or recording errors); mean
or median.
Limitations: only students who reached the end of the programme are observed (dropouts are not);
ANO_IN_GRAD is the year of entry in the current programme, so students who transferred may appear
with a shorter time; the 2023 cohort was affected by the suspension of classes in 2020-2021.
Outputs: 16_tempo_conclusao.csv
"""
import csv, io, zipfile, collections, statistics
import openpyxl
from config import arq, salvar_csv

FED, BASE = "Pública Federal", "Privada com fins lucrativos"


def cursos(ano):
    wb = openpyxl.load_workbook(arq(f"conceito{ano}"), read_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True)
    h = [str(x).strip().replace("  ", " ").rstrip("*").strip() for x in next(it)]
    cur = {}
    for r in it:
        if r[0] is None:
            continue
        d = dict(zip(h, r))
        cur[str(d["Código do Curso"])] = (d["Categoria Administrativa"], d["Código da Área"])
    return cur


def tempos(ano, cur):
    z = zipfile.ZipFile(arq(f"enade{ano}"))
    nomes = [n for n in z.namelist() if n.endswith(".txt")]
    f1 = [n for n in nomes if n.endswith("arq1.txt")][0]
    f2 = [n for n in nomes if n.endswith("arq2.txt")][0]
    mod = {}
    for r in csv.DictReader(io.TextIOWrapper(z.open(f1), encoding="latin-1", newline=""), delimiter=";"):
        mod[r["CO_CURSO"]] = r["CO_MODALIDADE"]
    t = collections.defaultdict(list)  # (cat, area, presencial) -> years
    for r in csv.DictReader(io.TextIOWrapper(z.open(f2), encoding="latin-1", newline=""), delimiter=";"):
        c = r["CO_CURSO"]
        if c not in cur:
            continue
        try:
            a = int(r["ANO_IN_GRAD"])
        except ValueError:
            continue
        if not 1950 <= a <= ano:
            continue
        cat, area = cur[c]
        t[(cat, area, mod.get(c) == "1")].append(ano - a)
    return t


def resumo(t, presencial_so, minimo, estat):
    """Federal mean, for-profit mean reweighted to the federal area mix, gap, shares above 5 years."""
    g = collections.defaultdict(list)
    for (cat, area, pres), v in t.items():
        if cat in (FED, BASE) and (pres or not presencial_so):
            g[(cat, area)].extend(x for x in v if x >= minimo)
    nf = {a: len(l) for (c, a), l in g.items() if c == FED and l}
    areas = [a for a in nf if g.get((BASE, a))]
    w = sum(nf[a] for a in areas)
    def media(cat, f):
        return sum(nf[a] / w * f(g[(cat, a)]) for a in areas)
    acima5 = lambda v: sum(x > 5 for x in v) / len(v)
    tf, tb = media(FED, estat), media(BASE, estat)
    return dict(federal=tf, privada=tb, dif=tf - tb, rel=tf / tb - 1, p5_federal=media(FED, acima5),
                p5_privada=media(BASE, acima5), n_federal=w, n_privada=sum(len(g[(BASE, a)]) for a in areas), areas=len(areas))


ESTAT = {"mean": lambda v: sum(v) / len(v), "median": statistics.median}
linhas = []
for ano in (2019, 2023):
    cur = cursos(ano)
    t = tempos(ano, cur)
    for amostra, pres in (("all", False), ("in-person", True)):
        for minimo in (0, 2):
            for nome, f in ESTAT.items():
                r = resumo(t, pres, minimo, f)
                linhas.append([ano, amostra, minimo, nome, r["n_federal"], r["n_privada"], r["areas"],
                               round(r["federal"], 3), round(r["privada"], 3), round(r["dif"], 3), round(r["rel"], 4),
                               round(r["p5_federal"], 4), round(r["p5_privada"], 4)])
                print(ano, amostra, "min", minimo, nome, {k: round(v, 3) for k, v in r.items()})
salvar_csv("16_tempo_conclusao.csv", linhas,
           ["ano", "amostra", "anos_minimos", "estatistica", "estudantes_federal", "estudantes_privada", "areas",
            "anos_federal", "anos_privada", "dif_anos", "dif_relativa", "pct_mais_5_anos_federal", "pct_mais_5_anos_privada"])
print("16_tempo_conclusao.csv written")
