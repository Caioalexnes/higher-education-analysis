"""Paths.

The data files (zip, xlsx and csv files downloaded from INEP, the Portal da Transparencia and CAPES)
must be in the folder given by the environment variable DADOS (default: the folder that contains
this repository). Additional folders can be given in DADOS_EXTRA, separated by ':' (Linux/macOS)
or ';' (Windows).
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.environ.get("DADOS", os.path.dirname(BASE))
EXTRA = [d for d in os.environ.get("DADOS_EXTRA", "").split(os.pathsep) if d]
RES = os.path.join(BASE, "results")
os.makedirs(RES, exist_ok=True)

ARQUIVOS = {
    "censo2024": "microdados_censo_da_educacao_superior_2024.zip",
    "censo2018": "microdados_censo_da_educacao_superior_2018.zip",
    "enade2023": "microdados_enade_2023.zip",
    "enade2019": "microdados_enade_2019_LGPD.zip",
    "idd2023": "IDD_2023.xlsx",
    "conceito2023": "conceito_enade_2023.xlsx",
    "idd2019": "IDD_2019.xlsx",
    "conceito2019": "Conceito_Enade_2019.xlsx",
    "orcamento2024": "2024_OrcamentoDespesa.zip",
    "capes_discentes2024": "br-capes-colsucup-discentes-2024-2025-12-01.csv",
    "capes_programas2024": "br-capes-colsucup-prog-2024-2025-12-01.csv",
    "enem2024": "microdados_enem_2024.zip",
}


def arq(chave):
    nome = ARQUIVOS[chave]
    for d in [DADOS] + EXTRA:
        p = os.path.join(d, nome)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"{nome} not found in {[DADOS] + EXTRA}")


def salvar_csv(nome, linhas, cabecalho):
    import csv
    p = os.path.join(RES, nome)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cabecalho)
        for l in linhas:
            w.writerow(l)
    return p
