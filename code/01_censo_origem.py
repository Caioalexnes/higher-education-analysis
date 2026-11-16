"""School origin (public or private secondary school) of undergraduate students,
by administrative category, competition for seats and course. 2024 Higher Education Census.

Outputs (results/):
  01_origem_por_categoria.csv
  01_origem_por_concorrencia.csv   (in-person courses of public institutions, quintiles)
  01_origem_por_curso.csv          (selected in-person courses)
"""
import csv, io, zipfile, collections
from config import arq, salvar_csv

CAT = {"1": "Pública Federal", "2": "Pública Estadual", "3": "Pública Municipal",
       "4": "Privada com fins lucrativos", "5": "Privada sem fins lucrativos", "7": "Especial"}
VARS = ["QT_MAT", "QT_ING", "QT_MAT_PROCESCPUBLICA", "QT_MAT_PROCESCPRIVADA", "QT_MAT_PROCNAOINFORMADA",
        "QT_ING_PROCESCPUBLICA", "QT_ING_PROCESCPRIVADA", "QT_CONC_PROCESCPUBLICA", "QT_CONC_PROCESCPRIVADA",
        "QT_MAT_RESERVA_VAGA", "QT_VG_NOVA", "QT_INSC_VG_NOVA"]


def ler_cursos():
    z = zipfile.ZipFile(arq("censo2024"))
    nome = [n for n in z.namelist() if n.endswith("MICRODADOS_CADASTRO_CURSOS_2024.CSV")][0]
    f = io.TextIOWrapper(z.open(nome), encoding="latin-1", newline="")
    r = csv.reader(f, delimiter=";")
    h = next(r)
    ix = {k: i for i, k in enumerate(h)}
    for row in r:
        d = {v: (int(row[ix[v]]) if row[ix[v]].strip().lstrip("-").isdigit() else 0) for v in VARS}
        d.update(cat=row[ix["TP_CATEGORIA_ADMINISTRATIVA"]], mod=row[ix["TP_MODALIDADE_ENSINO"]],
                 rot=row[ix["NO_CINE_ROTULO"]], grau=row[ix["TP_GRAU_ACADEMICO"]])
        yield d


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def resumo(rs):
    s = collections.Counter()
    for r in rs:
        s.update({k: r[k] for k in VARS})
    inf = s["QT_MAT_PROCESCPUBLICA"] + s["QT_MAT_PROCESCPRIVADA"]
    ing = s["QT_ING_PROCESCPUBLICA"] + s["QT_ING_PROCESCPRIVADA"]
    con = s["QT_CONC_PROCESCPUBLICA"] + s["QT_CONC_PROCESCPRIVADA"]
    return dict(mat=s["QT_MAT"], pub_mat=pct(s["QT_MAT_PROCESCPUBLICA"], inf), priv_mat=pct(s["QT_MAT_PROCESCPRIVADA"], inf),
                pub_ing=pct(s["QT_ING_PROCESCPUBLICA"], ing), pub_conc=pct(s["QT_CONC_PROCESCPUBLICA"], con),
                nao_inf=pct(s["QT_MAT_PROCNAOINFORMADA"], s["QT_MAT"]), reserva=pct(s["QT_MAT_RESERVA_VAGA"], s["QT_MAT"]),
                priv_fora_reserva=pct(s["QT_MAT_PROCESCPRIVADA"], s["QT_MAT"] - s["QT_MAT_RESERVA_VAGA"]),
                insc_vaga=round(s["QT_INSC_VG_NOVA"] / s["QT_VG_NOVA"], 1) if s["QT_VG_NOVA"] else None)


def main():
    rows = [r for r in ler_cursos() if r["cat"] in CAT]
    out = []
    grupos = [(CAT[c], [r for r in rows if r["cat"] == c]) for c in CAT]
    grupos += [("Públicas (1-3)", [r for r in rows if r["cat"] in "123"]), ("Privadas (4-5)", [r for r in rows if r["cat"] in "45"]),
               ("Total", rows)]
    for mod, lab in [(None, "todas"), ("1", "presencial"), ("2", "a distância")]:
        for nome, rs in grupos:
            rr = [r for r in rs if mod is None or r["mod"] == mod]
            if rr:
                s = resumo(rr)
                out.append([nome, lab, s["mat"], s["pub_mat"], s["priv_mat"], s["pub_ing"], s["pub_conc"], s["nao_inf"], s["reserva"]])
    salvar_csv("01_origem_por_categoria.csv", out,
               ["categoria", "modalidade", "matriculas", "pct_escola_publica_mat", "pct_escola_privada_mat",
                "pct_escola_publica_ing", "pct_escola_publica_conc", "pct_nao_informado", "pct_reserva_vaga"])

    pub = [r for r in rows if r["cat"] in "123" and r["mod"] == "1" and r["QT_VG_NOVA"] > 0 and r["QT_MAT"] > 0]
    for r in pub:
        r["ratio"] = r["QT_INSC_VG_NOVA"] / r["QT_VG_NOVA"]
    pub.sort(key=lambda r: r["ratio"])
    tot = sum(r["QT_MAT"] for r in pub)
    bins, acc = [[] for _ in range(5)], 0
    for r in pub:
        bins[min(4, int(5 * acc / tot))].append(r)
        acc += r["QT_MAT"]
    out = []
    for i, b in enumerate(bins):
        s = resumo(b)
        out.append([i + 1, round(b[0]["ratio"], 1), round(b[-1]["ratio"], 1), s["mat"], s["insc_vaga"], s["priv_mat"], s["reserva"], s["priv_fora_reserva"]])
    salvar_csv("01_origem_por_concorrencia.csv", out,
               ["quintil", "insc_vaga_min", "insc_vaga_max", "matriculas", "insc_vaga", "pct_escola_privada", "pct_reserva_vaga", "pct_escola_privada_fora_reserva"])

    alvo = ["Medicina", "Odontologia", "Engenharia civil", "Direito", "Engenharia de computação", "Ciência da computação",
            "Administração", "Pedagogia"]
    out = []
    for c in alvo + ["Engenharias (todas)", "Matemática (todas)", "Licenciaturas (grau 2)", "Bacharelados (grau 1)"]:
        if c == "Engenharias (todas)":
            sel = lambda r: r["rot"].lower().startswith("engenharia")
        elif c == "Matemática (todas)":
            sel = lambda r: r["rot"].lower().startswith("matemática")
        elif c.startswith("Licenciaturas"):
            sel = lambda r: r["grau"] == "2"
        elif c.startswith("Bacharelados"):
            sel = lambda r: r["grau"] == "1"
        else:
            sel = lambda r, c=c: r["rot"].lower() == c.lower()
        for nome, cats in [("Federal", "1"), ("Públicas", "123"), ("Privadas", "45")]:
            rr = [r for r in rows if r["cat"] in cats and r["mod"] == "1" and sel(r)]
            if rr:
                s = resumo(rr)
                out.append([c, nome, s["mat"], s["priv_mat"], s["reserva"], s["priv_fora_reserva"], s["insc_vaga"]])
    salvar_csv("01_origem_por_curso.csv", out,
               ["curso", "rede", "matriculas_presenciais", "pct_escola_privada", "pct_reserva_vaga", "pct_escola_privada_fora_reserva", "insc_vaga"])
    print("01 ok")


if __name__ == "__main__":
    main()
