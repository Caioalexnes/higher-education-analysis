"""Annual exits from in-person undergraduate courses: federal universities and private for-profit institutions.

Source: INEP, Sinopse Estatistica da Educacao Superior, table 7.2 (in-person undergraduate courses),
row "Total Brasil", by academic organization and administrative category. For each year:
  share of enrollment links that were severed during the year (matriculas desvinculadas) and that were
  suspended (matriculas trancadas), over all links (matriculas + trancadas + desvinculadas +
  transferidos + falecidos); and enrollments per graduate (matriculas / concluintes).
Federal: universities only. For-profit: universities, university centers and colleges.
The Sinopse workbooks must be extracted in a folder named sinopse_educacao_superior_<ano> under DADOS
or DADOS_EXTRA. Output: 18_evasao_sinopse.csv
"""
import glob, os
import openpyxl
from config import DADOS, EXTRA, salvar_csv

MEDIDAS = ["cursos", "vagas", "inscritos", "ing", "mat", "conc", "tranc", "desv", "transf", "falec"]
ANOS = [2015, 2016, 2017, 2018, 2024]


def workbook(ano):
    for d in [DADOS] + EXTRA:
        f = glob.glob(os.path.join(d, f"sinopse_educacao_superior_{ano}", "*", f"Sinopse_Educação_Superior_Municipio_{ano}.xlsx"))
        if f:
            return openpyxl.load_workbook(f[0], read_only=True)
    raise FileNotFoundError(f"Sinopse {ano}")


def linha_brasil(ano):
    ws = workbook(ano)["7.2"]
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 6:
            blocos = {str(x).strip()[:12]: k for k, x in enumerate(r) if x}
        if r[0] and str(r[0]).strip() == "Total Brasil":
            return r, blocos


def main():
    out = []
    for ano in ANOS:
        r, blocos = linha_brasil(ano)
        num = lambda b, m, c: float(r[b + 7 * MEDIDAS.index(m) + c] or 0)
        grupos = {"federal universities": [(blocos["Universidade"], 1)],
                  "private for-profit": [(blocos[k], 5) for k in ("Universidade", "Centro Unive", "Faculdade")]}
        for nome, sel in grupos.items():
            d = {m: sum(num(b, m, c) for b, c in sel) for m in MEDIDAS}
            vinc = d["mat"] + d["tranc"] + d["desv"] + d["transf"] + d["falec"]
            out.append([ano, nome, int(d["mat"]), int(d["conc"]), int(d["desv"]), int(d["tranc"]),
                        round(d["desv"] / vinc, 4), round(d["tranc"] / vinc, 4), round(d["mat"] / d["conc"], 2)])
            print(ano, nome, out[-1][6:])
    salvar_csv("18_evasao_sinopse.csv", out, ["ano", "grupo", "matriculas", "concluintes", "desvinculadas", "trancadas",
                                              "taxa_desvinculadas", "taxa_trancadas", "matriculas_por_concluinte"])
    print("18 ok")


if __name__ == "__main__":
    main()
