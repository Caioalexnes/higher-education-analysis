"""Approximate reconstruction of the IDD of editions 2014-2021 with the method INEP uses from 2022.

In the random-intercept model behind the IDD, with rho = tau^2 / sigma^2 (between-course over
within-course residual variance in the area) and n_c graduates with an Enem score in course c:
    lambda_c = n_c rho / (1 + n_c rho)
    IDD_old_c = (1 - lambda_c) rbar_c          (method until 2021)
    IDD_new_c = lambda_c rbar_c                (method from 2022)
so that IDD_new_c = n_c rho IDD_old_c and the unshrunk mean residual is rbar_c = (1 + n_c rho) IDD_old_c.
The student-level data INEP used are no longer published, so rho is estimated from the course-level
IDD itself: under the model, Var(IDD_old_c) = sigma^2 / (n_c (1 + n_c rho)) and
Var(IDD_new_c) = tau^2 n_c rho / (1 + n_c rho). rho is estimated by maximum likelihood (normal
approximation), either common to all areas of an edition (with area-specific variance and mean)
or separately by area. The reconstruction ignores INEP's exclusion of outlying students.
Outputs: results/14_rho.csv, results/14_reconstrucao.csv
"""
import os, sys
import numpy as np
import pandas as pd
from config import RES
import importlib.util
aqui = os.path.dirname(os.path.abspath(__file__))
def mod(nome, arq):
    s = importlib.util.spec_from_file_location(nome, os.path.join(aqui, arq)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
p = mod('p', '10_diferencas_pareadas.py'); s12 = mod('s12', '12_serie_historica.py')
GRID = 10 ** np.linspace(-3, 0.5, 351)
PRIV = {'Privada com fins lucrativos', 'Privada sem fins lucrativos', 'Comunitária/Confessional', 'Privada (não separada)'}

def ll_area(x, n, r, novo):
    w = n * r / (1 + n * r) if novo else 1 / (n * (1 + n * r))
    W = 1 / w; mu = np.sum(W * x) / W.sum(); s2 = np.mean((x - mu) ** 2 / w)
    return -0.5 * np.sum(np.log(s2 * w)) - 0.5 * len(x)

def ajusta(d, novo):
    grupos = [(a, g['idd_bruto'].values, g['participantes_com_enem'].values.astype(float)) for a, g in d.groupby('area') if len(g) >= 20]
    tot = np.array([sum(ll_area(x, n, r, novo) for _, x, n in grupos) for r in GRID])
    comum = GRID[tot.argmax()]
    por_area = {a: GRID[np.argmax([ll_area(x, n, r, novo) for r in GRID])] for a, x, n in grupos}
    return comum, por_area

if __name__ == '__main__':
    anos = [int(a) for a in sys.argv[1:]] or sorted(s12.ARQ)
    rhos, linhas = [], []
    for ano in anos:
        novo = ano >= 2022
        d = s12.base(ano); d = d[d['participantes_com_enem'] >= 2].copy()
        comum, por_area = ajusta(d, novo)
        rhos.append(dict(ano=ano, metodo='new' if novo else 'old', rho_comum=comum, rho_area_mediana=np.median(list(por_area.values())),
                         rho_area_p25=np.percentile(list(por_area.values()), 25), rho_area_p75=np.percentile(list(por_area.values()), 75), areas=len(por_area)))
        n = d['participantes_com_enem'].astype(float)
        ra = d['area'].map(por_area).fillna(comum)
        if novo:
            d['idd_atual_comum'] = d['idd_bruto']; d['idd_atual_area'] = d['idd_bruto']
            d['rbar_comum'] = d['idd_bruto'] * (1 + n * comum) / (n * comum)
        else:
            d['idd_atual_comum'] = d['idd_bruto'] * n * comum
            d['idd_atual_area'] = d['idd_bruto'] * n * ra
            d['rbar_comum'] = d['idd_bruto'] * (1 + n * comum)
        for nome_base, cats in [('private for-profit', {p.BASE}), ('all private', PRIV)]:
            b = d[d['categoria'].isin(cats)]; g = d[d['categoria'] == p.FED]
            if len(b) < 30: continue
            linha = dict(ano=ano, base=nome_base, metodo='new' if novo else 'old')
            for col in ['idd_bruto', 'idd_atual_comum', 'idd_atual_area', 'rbar_comum']:
                gg, bb = g.assign(idd_bruto=g[col]), b.assign(idd_bruto=b[col])
                dn, di = p.pareada(gg, bb)
                linha['dif_nota'] = dn; linha[f'dif_{col}'] = di
            linhas.append(linha)
        print(ano, 'rho', round(comum, 4), flush=True)
    for nome, L in [('14_rho.csv', rhos), ('14_reconstrucao.csv', linhas)]:
        out = pd.DataFrame(L); dest = f'{RES}/{nome}'
        if os.path.exists(dest) and sys.argv[1:]:
            old = pd.read_csv(dest, sep=';'); out = pd.concat([old[~old['ano'].isin(anos)], out])
        out.sort_values(['ano'] + (['base'] if 'base' in out else []), kind='stable').to_csv(dest, sep=';', index=False, float_format='%.4f')
