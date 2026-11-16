"""Course-level regressions: selection versus value added (depends on script 08).

For each course c in assessment area a:
    Y_c = alpha_a + sum_k beta_k * Category_kc + X_c' gamma + e_c
with Y = raw Enade score (0.25 FG + 0.75 CE) or raw IDD (observed minus Enem-predicted
Enade score, same points scale). Reference category: private for-profit.
Weighted least squares (weights: participants for the score, participants with an Enem
score for the IDD), standard errors clustered by institution (CR1), normal p-values.
Only numpy and pandas are required.
Outputs: results/09_regressoes.csv, results/09_resumo.csv
"""
import math
import numpy as np
import pandas as pd
from config import RES

REF = 'Privada com fins lucrativos'
CAT = {'Pública Federal': 'federal', 'Pública Estadual': 'state', 'Pública Municipal': 'municipal',
       'Privada sem fins lucrativos': 'private_nonprofit', 'Comunitária/Confessional': 'community_confessional',
       'Especial': 'special'}
ORG = {'Universidade': 'university', 'Centro Universitário': 'university_center', 'Faculdade': 'college',
       'Instituto Federal de Educação, Ciência e Tecnologia': 'federal_institute',
       'Centro Federal de Educação Tecnológica': 'federal_institute'}
SD_ALUNO = pd.read_csv(f'{RES}/02_dp_aluno_2023.csv', sep=';')['dp_nota_geral_dentro_da_area'].iloc[0]


def wls_cluster(y, X, w, g):
    y, X, w = np.asarray(y, float), np.asarray(X, float), np.asarray(w, float)
    sw = np.sqrt(w)
    Xw, yw = X * sw[:, None], y * sw
    XtX_inv = np.linalg.pinv(Xw.T @ Xw)
    b = XtX_inv @ (Xw.T @ yw)
    e = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1]))
    gs = pd.Series(np.arange(len(y))).groupby(np.asarray(g)).indices
    for idx in gs.values():
        s = (X[idx] * (w[idx] * e[idx])[:, None]).sum(axis=0)
        meat += np.outer(s, s)
    n, k, G = len(y), np.linalg.matrix_rank(Xw), len(gs)
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    ybar = np.average(y, weights=w)
    r2 = 1 - np.sum(w * e ** 2) / np.sum(w * (y - ybar) ** 2)
    return b, np.sqrt(np.clip(np.diag(V), 0, None)), n, G, r2


def desenho(d, controles, fe):
    X = pd.DataFrame({'const': 1.0}, index=d.index)
    for nome in CAT.values():
        X[nome] = (d['cat'] == nome).astype(float)
    for c in controles:
        X[c] = d[c].astype(float)
    for f in fe:
        X = X.join(pd.get_dummies(d[f], prefix=f, drop_first=True, dtype=float))
    X = X.loc[:, (X != 0).any()]
    return X


def prepara(ano):
    d = pd.read_csv(f'{RES}/08_base_cursos_{ano}.csv', sep=';', low_memory=False)
    d = d[d['categoria'].isin([REF] + list(CAT))].copy()
    d['cat'] = d['categoria'].map(CAT).fillna('private_forprofit')
    d['org'] = d['organizacao'].map(ORG).fillna('other')
    d['ead'] = (d['modalidade'] == 'Educação a Distância').astype(float)
    for o in ['university_center', 'college', 'federal_institute']:
        d['org_' + o] = (d['org'] == o).astype(float)
    d['log_participantes'] = np.log(d['participantes'].clip(lower=1))
    if 'inscritos_por_vaga_2018' in d:
        d['log1_insc_vaga'] = np.log1p(d['inscritos_por_vaga_2018'])
        d['baixa_procura'] = (d['inscritos_por_vaga_2018'] < 2).astype(float).where(d['inscritos_por_vaga_2018'].notna())
        d['registro_1'] = np.isclose(d['inscritos_por_vaga_2018'], 1.0)
        d['fed_x_log1_insc_vaga'] = d['log1_insc_vaga'] * (d['cat'] == 'federal')
        d['fed_x_baixa_procura'] = d['baixa_procura'] * (d['cat'] == 'federal')
        d['log_matriculas'] = np.log(d['matriculas_2018'].clip(lower=1))
    return d


BASICOS = ['ead', 'org_university_center', 'org_college', 'org_federal_institute', 'log_participantes']
COMPOSICAO = ['ing_escola_privada_2018', 'ing_25mais_2018', 'ing_noturno_2018', 'ing_fies_2018',
              'ing_prouni_2018', 'ing_reserva_2018', 'log_matriculas']


def roda(d, y, w, controles, fe, nome, amostra, linhas, extras=()):
    s = d.dropna(subset=[y, w] + controles + list(fe))
    s = s[s[w] > 0]
    X = desenho(s, controles, fe)
    b, se, n, G, r2 = wls_cluster(s[y], X, s[w], s['ies'])
    for i, v in enumerate(X.columns):
        if v in list(CAT.values()) + list(controles) or v in extras:
            z = b[i] / se[i] if se[i] > 0 else float('nan')
            p = math.erfc(abs(z) / math.sqrt(2)) if se[i] > 0 else float('nan')
            linhas.append(dict(modelo=nome, amostra=amostra, dependente=y, variavel=v, coef=b[i], ep=se[i], p=p,
                               n=n, clusters=G, r2=r2))
    return dict(zip(X.columns, b)), dict(zip(X.columns, se)), n


def coef(linhas, modelo, amostra, dep, var='federal'):
    for l in linhas:
        if l['modelo'] == modelo and l['amostra'] == amostra and l['dependente'] == dep and l['variavel'] == var:
            return l['coef'], l['ep']
    return float('nan'), float('nan')


if __name__ == '__main__':
    L = []
    pares = [('nota_bruta', 'participantes'), ('idd_bruto', 'participantes_com_enem')]
    d23, d19 = prepara(2023), prepara(2019)
    # comparable sample: courses with both measures
    for d in (d23, d19):
        d.dropna(subset=['nota_bruta', 'idd_bruto'], inplace=True)
        d.drop(d[(d['participantes'] <= 0) | (d['participantes_com_enem'] <= 0)].index, inplace=True)
    especs = [
        ('M1 area FE', [], ['area']),
        ('M2 + modality, organization, size, UF FE', BASICOS, ['area', 'uf']),
    ]
    for ano, d in [('2023', d23), ('2019', d19)]:
        for nome, ctr, fe in especs:
            for y, w in pares:
                roda(d, y, w, ctr, fe, nome, ano, L)
    # 2023: entering-cohort composition (Census 2018)
    for y, w in pares:
        roda(d23, y, w, BASICOS + COMPOSICAO, ['area', 'uf'], 'M3 + entrant composition (Census 2018)', '2023', L)
    # 2023: selectivity interactions
    for y, w in pares:
        roda(d23, y, w, BASICOS + ['log1_insc_vaga', 'fed_x_log1_insc_vaga'], ['area', 'uf'],
             'M4 + log(1+applicants per seat) x federal', '2023', L)
        roda(d23, y, w, BASICOS + ['baixa_procura', 'fed_x_baixa_procura'], ['area', 'uf'],
             'M5 + low demand (<2 applicants per seat) x federal', '2023', L)
    for y, w in pares:
        roda(d23[~d23['registro_1']], y, w, BASICOS + ['baixa_procura', 'fed_x_baixa_procura'], ['area', 'uf'],
             'M5b low demand x federal, excluding courses reporting exactly 1.0 applicant per seat', '2023', L)
    # robustness on M2 (2023)
    rob = {
        'unweighted': (d23.assign(um=1.0), 'um'),
        'in-person only': (d23[d23['ead'] == 0], None),
        'universities only': (d23[d23['org'] == 'university'], None),
        '>=20 graduates with Enem': (d23[d23['participantes_com_enem'] >= 20], None),
        'Enem coverage >= 50%': (d23[d23['prop_com_enem'] >= 0.5], None),
    }
    for amostra, (d, peso) in rob.items():
        for y, w in pares:
            roda(d, y, peso or w, BASICOS, ['area', 'uf'], 'M2 robustness', '2023 ' + amostra, L)
    for y, w in pares:
        roda(d23, y, w, BASICOS + ['prop_com_enem'], ['area', 'uf'], 'M2 + Enem coverage control', '2023', L)
    out = pd.DataFrame(L)
    out.to_csv(f'{RES}/09_regressoes.csv', sep=';', index=False, float_format='%.4f')
    # summary: federal gap in score and in value added, selection share
    R = []
    for (m, a) in out[['modelo', 'amostra']].drop_duplicates().itertuples(index=False):
        bn, en = coef(L, m, a, 'nota_bruta'); bv, ev = coef(L, m, a, 'idd_bruto')
        R.append(dict(modelo=m, amostra=a, fed_nota=bn, ep_nota=en, fed_idd=bv, ep_idd=ev,
                      parcela_selecao=1 - bv / bn if bn else float('nan'), fed_idd_dp_aluno=bv / SD_ALUNO))
    R = pd.DataFrame(R)
    R.to_csv(f'{RES}/09_resumo.csv', sep=';', index=False, float_format='%.4f')
    pd.set_option('display.width', 200)
    print(R.round(3).to_string(index=False))
    print()
    print(out[out['variavel'].str.contains('insc|procura')].round(3).to_string(index=False))
