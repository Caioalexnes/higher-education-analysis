"""Cost per student and value added in federal universities, controlling for
graduate-program intensity (CAPES, Coleta Sucupira 2024).

Variables by university (e-MEC code = INEP CO_IES):
  pos_alunos      master's and doctoral students enrolled or graduated in 2024
  pos_por_grad    pos_alunos / in-person undergraduate enrollments
  conceito_medio  mean CAPES grade of the programs, weighted by students
Models (OLS, 66 universities):
  (1) IDD ~ cost
  (2) IDD ~ cost + pos_por_grad + conceito_medio
  (3) cost ~ pos_por_grad + conceito_medio   (how much of the cost graduate programs explain)
  (4) IDD ~ cost per simple student-equivalent (undergraduate + 2 x graduate)
Outputs: 05_pos_por_universidade.csv, 05_modelos.csv
Student names in the CAPES file are not read for anything other than counting and do not appear in the outputs.
"""
import csv, collections, math
import numpy as np
from config import arq, salvar_csv, RES

EXCLUIR = {'UNIVASF'}


def pos_graduacao():
    alunos = collections.Counter(); dout = collections.Counter(); soma_conc = collections.Counter()
    with open(arq('capes_discentes2024'), encoding='latin-1', newline='') as f:
        for r in csv.DictReader(f, delimiter=';'):
            if r['NM_SITUACAO_DISCENTE'] not in ('MATRICULADO', 'TITULADO'):
                continue
            co = r['CD_ENTIDADE_EMEC']
            alunos[co] += 1
            if r['DS_GRAU_ACADEMICO_DISCENTE'].startswith('DOUTORADO'):
                dout[co] += 1
            try:
                soma_conc[co] += float(r['CD_CONCEITO_PROGRAMA'])
            except ValueError:
                pass
    progs = collections.Counter(); prog_67 = collections.Counter()
    with open(arq('capes_programas2024'), encoding='latin-1', newline='') as f:
        for r in csv.DictReader(f, delimiter=';'):
            co = r['CD_ENTIDADE_EMEC']; progs[co] += 1
            if r['CD_CONCEITO_PROGRAMA'] in ('6', '7'):
                prog_67[co] += 1
    return alunos, dout, soma_conc, progs, prog_67


def mqo(y, X, nomes):
    X = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; n, k = X.shape
    s2 = e @ e / (n - k); V = s2 * np.linalg.inv(X.T @ X); se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return [(nm, float(bi), float(si), float(bi / si)) for nm, bi, si in zip(['constante'] + nomes, b, se)], float(r2), n


def main():
    alunos, dout, soma_conc, progs, prog_67 = pos_graduacao()
    fed = []
    with open(f'{RES}/03_custo_federais.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter=';'):
            fed.append(r)
    out, dados = [], []
    for r in fed:
        co = r['co_ies']; pres = int(r['matriculas_presenciais'] or 0); pos = alunos[co]
        cm = soma_conc[co] / pos if pos else None
        out.append([r['sigla'], co, pres, pos, dout[co], round(pos / pres, 3) if pres else None, round(cm, 2) if cm else None, progs[co], prog_67[co]])
        if r['sigla'] in EXCLUIR or not r['idd_bruto_medio_rel_area'] or int(r['formandos_com_enem'] or 0) < 30:
            continue
        custo = float(r['custo_corrente'])
        dados.append(dict(s=r['sigla'], custo=custo / pres / 1000, custo_eq=custo / (pres + 2 * pos) / 1000,
                          pos=pos / pres, conc=cm or 0.0, idd=float(r['idd_bruto_medio_rel_area'])))
    salvar_csv('05_pos_por_universidade.csv', out, ['sigla', 'co_ies', 'matriculas_presenciais_grad', 'pos_alunos', 'doutorandos', 'pos_por_grad', 'conceito_capes_medio', 'programas', 'programas_nota_6_7'])
    y = np.array([d['idd'] for d in dados]); c = np.array([d['custo'] for d in dados])
    p = np.array([d['pos'] for d in dados]); k = np.array([d['conc'] for d in dados]); ce = np.array([d['custo_eq'] for d in dados])
    linhas = []
    for nome, (coefs, r2, n) in [('(1) IDD ~ custo', mqo(y, [c], ['custo (R$ mil)'])),
                                 ('(2) IDD ~ custo + pós + conceito', mqo(y, [c, p, k], ['custo (R$ mil)', 'pós por aluno de graduação', 'conceito Capes médio'])),
                                 ('(3) custo ~ pós + conceito', mqo(c, [p, k], ['pós por aluno de graduação', 'conceito Capes médio'])),
                                 ('(4) IDD ~ custo por aluno-equivalente', mqo(y, [ce], ['custo por aluno-equivalente (R$ mil)']))]:
        for nm, b, se, t in coefs:
            linhas.append([nome, nm, round(b, 4), round(se, 4), round(t, 2), round(r2, 3), n])
    salvar_csv('05_modelos.csv', linhas, ['modelo', 'variavel', 'coeficiente', 'erro_padrao', 't', 'r2', 'universidades'])
    # tercis do custo por aluno-equivalente
    o = sorted(dados, key=lambda d: d['custo_eq']); m = len(o) // 3
    terc = [[i + 1, round(np.mean([d['custo_eq'] for d in o[a:b]]), 1), round(np.mean([d['idd'] for d in o[a:b]]), 2), round(np.mean([d['pos'] for d in o[a:b]]), 3)]
            for i, (a, b) in enumerate([(0, m), (m, 2 * m), (2 * m, len(o))])]
    salvar_csv('05_tercis_aluno_equivalente.csv', terc, ['tercil', 'custo_por_aluno_equivalente_mil', 'idd_medio', 'pos_por_grad_medio'])
    print('05 ok', len(dados))


if __name__ == '__main__':
    main()
