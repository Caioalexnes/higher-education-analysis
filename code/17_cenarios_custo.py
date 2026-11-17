"""Federal cost per student against private tuition under the most and least favourable choices, 2024.

Federal side (all federal universities of script 03, total / total):
  current cost of the universities' own budget units, without pensions, special charges and capital
  (script 03; it already includes the employer pension contribution, action 09HB), plus a share of
  the current cost of university hospitals: the hospitals' own budget units, Ebserh (26443) and the
  Hospital de Clinicas de Porto Alegre (26294), also without pensions, special charges and capital.
  Students: undergraduates (script 03) plus stricto sensu graduate students (script 05).
  Research discount: share of expenditure that Bielschowsky and Amaral (2022) attribute to research
  and extension in federal universities, aggregate (script 04).
Private side: median tuition actually paid in in-person private courses (Hoper Educacao/ABMES, 2026),
  twelve payments a year, in reais of 2024 (IPCA, mean of 2024 over mean of January-March 2026),
  with or without the taxes on revenue (ISS 2% to 5%; PIS 0.65% and Cofins 3%, cumulative regime for
  higher education, Lei 10.833/2003 art. 10, XIV).
Per graduate: enrolments per graduate, federal over private for-profit, in-person bachelor's and
  licentiate courses of the same CINE label, weighted by federal enrolments (Census 2024 and 2018).
Outputs: 17_cenarios_custo.csv, 17_matriculas_por_concluinte.csv
"""
import csv, io, zipfile, collections
from config import arq, salvar_csv, RES
import os

HU_SHARE = {"mais favorável": 0.0, "central": 0.35, "mais desfavorável": 1.0}
DISCOUNT = {"mais favorável": True, "central": False, "mais desfavorável": False}
TAX = {"mais favorável": 0.0, "central": 0.02 + 0.0365, "mais desfavorável": 0.05 + 0.0365}
TUITION_MONTH, MONTHS = 835.0, 12
IPCA_2024 = [6801.72, 6858.17, 6869.14, 6895.24, 6926.96, 6941.51, 6967.89, 6966.50, 6997.15, 7036.33, 7063.77, 7100.50]
IPCA_2026Q1 = [7427.72, 7479.71, 7545.53]


def ler(nome):
    with open(os.path.join(RES, nome), encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def valor(x):
    return float(x.replace(".", "").replace(",", ".")) if x else 0.0


def hospitais():
    z = zipfile.ZipFile(arq("orcamento2024"))
    f = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="latin-1", newline="")
    c = collections.Counter()
    for row in csv.DictReader(f, delimiter=";"):
        if row["CÓDIGO ÓRGÃO SUPERIOR"] != "26000":
            continue
        uo, nome = row["CÓDIGO UNIDADE ORÇAMENTÁRIA"], row["NOME UNIDADE ORÇAMENTÁRIA"].upper()
        if not (uo in ("26443", "26294") or "HOSP" in nome):
            continue
        if row["CÓDIGO CATEGORIA ECONÔMICA"] != "3" or row["CÓDIGO FUNÇÃO"] in ("09", "28"):
            continue
        grupo = {"26443": "ebserh", "26294": "hcpa"}.get(uo, "hu_universidades")
        c[grupo] += valor(row["ORÇAMENTO REALIZADO (R$)"])
    return c


def matriculas_por_concluinte(chave):
    z = zipfile.ZipFile(arq(chave))
    cur = [n for n in z.namelist() if "CADASTRO_CURSOS" in n.upper() and n.upper().endswith(".CSV")][0]
    g = collections.defaultdict(lambda: [0, 0])
    for d in csv.DictReader(io.TextIOWrapper(z.open(cur), encoding="latin-1", newline=""), delimiter=";"):
        if d["TP_MODALIDADE_ENSINO"] != "1" or d["TP_GRAU_ACADEMICO"] not in ("1", "2"):
            continue
        if d["TP_CATEGORIA_ADMINISTRATIVA"] not in ("1", "4"):
            continue
        k = (d["TP_CATEGORIA_ADMINISTRATIVA"], d["CO_CINE_ROTULO"])
        g[k][0] += int(d["QT_MAT"] or 0)
        g[k][1] += int(d["QT_CONC"] or 0)
    fed = {a: v for (c, a), v in g.items() if c == "1" and v[1] > 0}
    areas = [a for a in fed if g.get(("4", a), [0, 0])[1] > 0]
    w = sum(fed[a][0] for a in areas)
    rf = sum(fed[a][0] / w * fed[a][0] / fed[a][1] for a in areas)
    rp = sum(fed[a][0] / w * g[("4", a)][0] / g[("4", a)][1] for a in areas)
    return rf, rp, len(areas)


def main():
    c03 = ler("03_custo_federais.csv")
    custo = sum(float(r["custo_corrente"]) for r in c03)
    patronal = sum(float(r["contrib_patronal_09HB"]) for r in c03)
    grad = sum(float(r["matriculas"]) for r in c03)
    pos = sum(float(r["pos_alunos"]) for r in ler("05_pos_por_universidade.csv"))
    pesquisa = [float(r["pct_descontado_pesquisa"]) for r in ler("04_bielschowsky_amaral.csv")
                if r["segmento"] == "Universidades federais"][0] / 100
    hu = hospitais()
    hu_total = sum(hu.values())
    alunos = grad + pos
    deflator = (sum(IPCA_2026Q1) / 3) / (sum(IPCA_2024) / 12)
    mpc = {ano: matriculas_por_concluinte(f"censo{ano}") for ano in (2024, 2018)}
    fator = mpc[2024][0] / mpc[2024][1]
    linhas = []
    for cen in HU_SHARE:
        fed = (custo + HU_SHARE[cen] * hu_total) * ((1 - pesquisa) if DISCOUNT[cen] else 1) / alunos
        priv = TUITION_MONTH * MONTHS / deflator * (1 - TAX[cen])
        linhas.append([cen, HU_SHARE[cen], round(pesquisa, 3) if DISCOUNT[cen] else 0, TAX[cen], round(fed), round(priv),
                       round(fed / priv, 2), round(fed / priv * fator, 2)])
        print(cen, round(fed), round(priv), round(fed / priv, 2), round(fed / priv * fator, 2))
    salvar_csv("17_cenarios_custo.csv", linhas, ["cenario", "parcela_hu", "desconto_pesquisa", "impostos_sobre_receita",
                                                 "custo_federal_por_aluno", "mensalidade_anual_2024", "razao_por_ano", "razao_por_formado"])
    salvar_csv("17_matriculas_por_concluinte.csv", [[a, round(v[0], 2), round(v[1], 2), round(v[0] / v[1], 3), v[2]] for a, v in mpc.items()],
               ["ano", "federal", "privada_com_fins", "razao", "rotulos_cine"])
    print("custo corrente", round(custo / 1e9, 2), "patronal", round(patronal / 1e9, 2), "HU", {k: round(v / 1e9, 2) for k, v in hu.items()},
          "alunos", int(grad), int(pos), "pesquisa", round(pesquisa, 3), "deflator", round(deflator, 4), "fator", {a: round(v[0] / v[1], 3) for a, v in mpc.items()})
    print("17 ok")


if __name__ == "__main__":
    main()
