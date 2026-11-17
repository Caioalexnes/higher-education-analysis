"""Cost and value added among federal universities, adding the university hospitals' own budget units.

Robustness of Section 6.5. The cost in script 03 excludes university hospitals. Here the current
spending of each university's hospital budget units in 2024 (Portal da Transparencia; without
pensions, special charges and capital) is added at 35% (the share the TCU indicators attribute to
teaching) and at 100%. Ebserh (26443) and the Hospital de Clinicas de Porto Alegre (26294) are
separate companies whose budgets are not split by hospital in this file, so they are not included.
Sample and models as in script 05: 66 universities; (1) IDD ~ cost; (2) IDD ~ cost + graduate
students per undergraduate + mean CAPES grade. Cost in R$ 1,000 per in-person undergraduate.
Outputs: 20_custo_hu.csv, 20_modelos_hu.csv
"""
import csv, io, zipfile, collections, os
import numpy as np
from config import arq, salvar_csv, RES

HU = {'26358': 'UFAL', '26359': 'UFBA', '26362': 'UFC', '26364': 'UFES', '26365': 'UFG', '26366': 'UFF', '26367': 'UFJF',
      '26368': 'UFMG', '26369': 'UFPA', '26370': 'UFPA', '26371': 'UFPB', '26372': 'UFPR', '26373': 'UFPE', '26374': 'UFRN',
      '26378': 'UFRJ', '26385': 'UFGD', '26386': 'UFSC', '26387': 'UFSM', '26388': 'UFCG', '26389': 'UFTM', '26391': 'UNIRIO',
      '26392': 'UFAM', '26393': 'UNB', '26394': 'UFMA', '26395': 'FURG', '26396': 'UFU', '26397': 'UFMT', '26398': 'UFPEL',
      '26399': 'UFPI', '26400': 'UFS', '26445': 'UNIFESP'}
EXCLUIR = {'UNIVASF'}


def valor(x):
    return float(x.replace('.', '').replace(',', '.')) if x else 0.0


def ler(nome):
    with open(os.path.join(RES, nome), encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter=';'))


def custo_hu():
    z = zipfile.ZipFile(arq('orcamento2024'))
    f = io.TextIOWrapper(z.open(z.namelist()[0]), encoding='latin-1', newline='')
    c, nomes = collections.Counter(), {}
    for row in csv.DictReader(f, delimiter=';'):
        uo = row['CÓDIGO UNIDADE ORÇAMENTÁRIA']
        if uo not in HU:
            continue
        nomes[uo] = row['NOME UNIDADE ORÇAMENTÁRIA']
        if row['CÓDIGO CATEGORIA ECONÔMICA'] == '3' and row['CÓDIGO FUNÇÃO'] not in ('09', '28'):
            c[HU[uo]] += valor(row['ORÇAMENTO REALIZADO (R$)'])
    falta = set(HU) - set(nomes)
    if falta:
        raise ValueError(f'hospital budget units not found: {falta}')
    return c


def mqo(y, X):
    X = np.column_stack([np.ones(len(y))] + X)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b; n, k = X.shape
    se = np.sqrt(np.diag(e @ e / (n - k) * np.linalg.inv(X.T @ X)))
    return b, se


def main():
    hu = custo_hu()
    pos = {r['sigla']: r for r in ler('05_pos_por_universidade.csv')}
    dados, out = [], []
    for r in ler('03_custo_federais.csv'):
        s = r['sigla']; pres = int(r['matriculas_presenciais'] or 0)
        out.append([s, round(float(r['custo_corrente'])), round(hu.get(s, 0.0))])
        if s in EXCLUIR or not r['idd_bruto_medio_rel_area'] or int(r['formandos_com_enem'] or 0) < 30:
            continue
        p = pos[s]
        dados.append(dict(c=float(r['custo_corrente']), hu=hu.get(s, 0.0), pres=pres, idd=float(r['idd_bruto_medio_rel_area']),
                          pg=float(p['pos_por_grad'] or 0), cc=float(p['conceito_capes_medio'] or 0)))
    salvar_csv('20_custo_hu.csv', out, ['sigla', 'custo_corrente_sem_hu', 'custo_corrente_hu'])
    y = np.array([d['idd'] for d in dados]); pg = np.array([d['pg'] for d in dados]); cc = np.array([d['cc'] for d in dados])
    linhas = []
    for parte in (0.0, 0.35, 1.0):
        x = np.array([(d['c'] + parte * d['hu']) / d['pres'] / 1000 for d in dados])
        b1, s1 = mqo(y, [x]); b2, s2 = mqo(y, [x, pg, cc])
        r = float(np.corrcoef(x, y)[0, 1])
        linhas.append([parte, len(dados), round(float(np.median(x)), 1), round(float(b1[1]), 4), round(float(s1[1]), 4), round(float(b1[1] / s1[1]), 2),
                       round(r, 3), round(float(b2[1]), 4), round(float(s2[1]), 4), round(float(b2[1] / s2[1]), 2)])
        print(linhas[-1])
    salvar_csv('20_modelos_hu.csv', linhas, ['parcela_hu', 'universidades', 'custo_mediano_mil', 'inclinacao', 'ep', 't',
                                             'pearson_r', 'inclinacao_com_controles', 'ep_com_controles', 't_com_controles'])
    print('universities with a hospital unit in the sample:', sum(1 for d in dados if d['hu'] > 0))
    print('20 ok')


if __name__ == '__main__':
    main()
