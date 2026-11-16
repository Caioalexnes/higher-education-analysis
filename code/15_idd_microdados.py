"""Recomputes the IDD from INEP's student-level IDD microdata, with both methods, for every edition.

For each assessment area, the Enade score of graduate i in course c is modelled as
    C_ic = g0 + u_c + b1 CN_ic + b2 CH_ic + b3 LC_ic + b4 MT_ic + e_ic,
with a random course intercept u_c (variance tau^2) and e_ic (variance sigma^2), estimated by REML
(profile likelihood in rho = tau^2 / sigma^2, Fuller-Battese transformation). As in INEP's technical
notes, the model is estimated twice: students with an absolute standardized residual above 3 in the
first estimation are excluded from the second. With lambda_c = n_c rho / (1 + n_c rho):
    new method (from 2022):  IDD_c = u_hat_c = lambda_c * rbar_c
    old method (until 2021): IDD_c = mean of (C_ic - g0 - X_ic b - u_hat_c) = (1 - lambda_c) * rbar_c
where rbar_c is the course mean of C_ic - g0 - X_ic b. The old-method mean is computed both over the
students kept in the second estimation and over all students, to see which reproduces INEP's values.
Courses enter the estimation if INEP published an IDD for them (scripts 12 and 13 read those files).

Input: microdados_IDD_<year> (.zip as published, or the folder extracted from the .7z/.rar archives)
in the data folder (config.DADOS). Usage: python 15_idd_microdados.py 2021 2023
Outputs: results/15_parametros.csv, results/15_idd_cursos_<year>.csv, results/15_comparacao.csv
"""
import os, re, sys, glob, zipfile, io
import numpy as np
import pandas as pd
from config import DADOS, RES
import importlib.util
aqui = os.path.dirname(os.path.abspath(__file__))
def mod(nome, arq):
    s = importlib.util.spec_from_file_location(nome, os.path.join(aqui, arq)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
p = mod('p', '10_diferencas_pareadas.py'); s12 = mod('s12', '12_serie_historica.py')
CAT = {1: 'Pública Federal', 2: 'Pública Estadual', 3: 'Pública Municipal', 4: 'Privada com fins lucrativos',
       5: 'Privada sem fins lucrativos', 7: 'Especial', 8: 'Comunitária/Confessional'}
PRIV = {'Privada com fins lucrativos', 'Privada sem fins lucrativos', 'Comunitária/Confessional', 'Privada (não separada)'}


def ler_microdados(ano):
    """Finds the student file of an edition (inside a zip or in an extracted folder) and returns a DataFrame."""
    cands = [f for f in glob.glob(os.path.join(DADOS, '**', '*'), recursive=True)
             if re.search(rf'microdados_idd_{ano}', f, re.I) and re.search(r'\.(txt|csv)$', f, re.I)]
    if cands:
        f = max(cands, key=os.path.getsize)
        raw = open(f, 'rb').read()
    else:
        z = [f for f in glob.glob(os.path.join(DADOS, '*')) if re.search(rf'microdados_idd_{ano}\.zip$', f, re.I)]
        if not z or not zipfile.is_zipfile(z[0]):
            raise FileNotFoundError(f'IDD microdata {ano}: extract the archive into {DADOS}')
        zz = zipfile.ZipFile(z[0]); n = max([i for i in zz.infolist() if re.search(r'\.(txt|csv)$', i.filename, re.I)], key=lambda i: i.file_size)
        raw = zz.read(n)
    txt = raw.decode('latin-1')
    sep = ';' if txt[:2000].count(';') > txt[:2000].count(',') else ','
    d = pd.read_csv(io.StringIO(txt), sep=sep, low_memory=False)
    d.columns = [c.strip().strip('"').upper() for c in d.columns]
    def col(*pads):
        for pd_ in pads:
            for c in d.columns:
                if re.fullmatch(pd_, c): return c
        raise KeyError(f'{pads} not in {list(d.columns)}')
    out = pd.DataFrame({'curso': pd.to_numeric(d[col('CO_CURSO')], errors='coerce'),
                        'area': pd.to_numeric(d[col('CO_GRUPO', 'CO_AREA')], errors='coerce'),
                        'cat': pd.to_numeric(d[col('CO_CATEGAD')], errors='coerce'),
                        'pres': pd.to_numeric(d[col('TP_PRES')], errors='coerce'),
                        'C': pd.to_numeric(d[col('NT_GER')].astype(str).str.replace(',', '.'), errors='coerce')})
    for k in ('CN', 'CH', 'LC', 'MT'):
        out[k] = pd.to_numeric(d[col(rf'(ENEM_NT|VL_NOTA_ENEM|VL_NT_ENEM|NT_ENEM)_{k}', rf'.*ENEM.*_{k}')].astype(str).str.replace(',', '.'), errors='coerce')
    out = out[out['pres'] == 555].dropna(subset=['curso', 'area', 'C', 'CN', 'CH', 'LC', 'MT'])
    return out


def reml(y, X, g):
    """Random-intercept REML by profile likelihood in rho. g: integer group codes 0..G-1."""
    n = np.bincount(g).astype(float); N, k = X.shape
    sy = np.bincount(g, weights=y); sX = np.column_stack([np.bincount(g, weights=X[:, j]) for j in range(k)])
    ybar, Xbar = sy / n, sX / n[:, None]
    def fit(r):
        th = 1 - 1 / np.sqrt(1 + n * r)
        ys = y - th[g] * ybar[g]; Xs = X - th[g][:, None] * Xbar[g]
        XtX = Xs.T @ Xs; b = np.linalg.solve(XtX, Xs.T @ ys)
        rss = np.sum((ys - Xs @ b) ** 2); s2 = rss / (N - k)
        ll = -0.5 * ((N - k) * np.log(s2) + np.sum(np.log(1 + n * r)) + np.linalg.slogdet(XtX)[1])
        return ll, b, s2
    lo, hi = np.log(1e-5), np.log(20.0); gr = (np.sqrt(5) - 1) / 2
    a, c = hi - gr * (hi - lo), lo + gr * (hi - lo); fa, fc = fit(np.exp(a))[0], fit(np.exp(c))[0]
    for _ in range(60):
        if fa > fc: hi, c, fc = c, a, fa; a = hi - gr * (hi - lo); fa = fit(np.exp(a))[0]
        else: lo, a, fa = a, c, fc; c = lo + gr * (hi - lo); fc = fit(np.exp(c))[0]
    r = np.exp((lo + hi) / 2); ll, b, s2 = fit(r)
    rbar = ybar - Xbar @ b; lam = n * r / (1 + n * r); u = lam * rbar
    return dict(rho=r, b=b, s2=s2, n=n, rbar=rbar, lam=lam, u=u, ll=ll)


def estima(d, cursos_ok):
    linhas, pars = [], []
    for a, da in d[d['curso'].isin(cursos_ok)].groupby('area'):
        cods, g = np.unique(da['curso'].values, return_inverse=True)
        if len(cods) < 2: continue
        y = da['C'].values.astype(float); X = np.column_stack([np.ones(len(da)), da[['CN', 'CH', 'LC', 'MT']].values.astype(float)])
        f1 = reml(y, X, g)
        z = (y - X @ f1['b'] - f1['u'][g]) / np.sqrt(f1['s2'])
        keep = np.abs(z) <= 3
        g2u, g2 = np.unique(g[keep], return_inverse=True)
        f2 = reml(y[keep], X[keep], g2)
        u = np.zeros(len(cods)); u[g2u] = f2['u']
        res_all = y - X @ f2['b'] - u[g]
        old_all = np.bincount(g, weights=res_all) / np.bincount(g)
        old_keep = np.zeros(len(cods)); old_keep[g2u] = np.bincount(g2, weights=res_all[keep]) / f2['n']
        lam = np.zeros(len(cods)); lam[g2u] = f2['lam']
        nk = np.zeros(len(cods)); nk[g2u] = f2['n']
        linhas.append(pd.DataFrame({'curso': cods, 'area': a, 'n_estudantes': np.bincount(g), 'n_modelo': nk, 'lambda': lam,
                                    'idd_novo': u, 'idd_antigo_mantidos': old_keep, 'idd_antigo_todos': old_all}))
        pars.append(dict(area=a, cursos=len(cods), estudantes=len(da), excluidos=int((~keep).sum()), rho=f2['rho'],
                         sigma=np.sqrt(f2['s2']), tau=np.sqrt(f2['rho'] * f2['s2']), b_cn=f2['b'][1], b_ch=f2['b'][2], b_lc=f2['b'][3], b_mt=f2['b'][4]))
    return pd.concat(linhas), pd.DataFrame(pars)


if __name__ == '__main__':
    anos = [int(a) for a in sys.argv[1:]]
    comp, pars_all = [], []
    for ano in anos:
        pub = s12.base(ano)                                        # published course-level results
        if 'curso' not in pub:
            print(ano, 'no course codes in the published spreadsheet; skipped'); continue
        d = ler_microdados(ano)
        cur, par = estima(d, set(pub['curso']))
        par.insert(0, 'ano', ano); pars_all.append(par)
        cur = cur.merge(pub[['curso', 'categoria', 'participantes', 'participantes_com_enem', 'nota_bruta', 'idd_bruto']], on='curso', how='left')
        cur.to_csv(f'{RES}/15_idd_cursos_{ano}.csv', sep=';', index=False, float_format='%.4f')
        metodo_pub = 'idd_novo' if ano >= 2022 else 'idd_antigo_mantidos'
        linha = dict(ano=ano, cursos=len(cur))
        for c in ('idd_novo', 'idd_antigo_mantidos', 'idd_antigo_todos'):
            ok = cur[['idd_bruto', c]].dropna()
            linha[f'corr_pub_{c}'] = ok['idd_bruto'].corr(ok[c]); linha[f'mad_pub_{c}'] = (ok['idd_bruto'] - ok[c]).abs().median()
        dd = cur.dropna(subset=['nota_bruta', 'idd_bruto']).copy()
        dd = dd[(dd['participantes'] > 0) & (dd['participantes_com_enem'] > 0)]
        for nome_base, cats in [('private for-profit', {p.BASE}), ('all private', PRIV)]:
            b = dd[dd['categoria'].isin(cats)]; g = dd[dd['categoria'] == p.FED]
            if len(b) < 30: continue
            for c in ('idd_bruto', 'idd_novo', 'idd_antigo_mantidos', 'idd_antigo_todos'):
                dn, di = p.pareada(g.assign(idd_bruto=g[c]), b.assign(idd_bruto=b[c]))
                linha[f'{nome_base}: dif_nota'] = dn; linha[f'{nome_base}: dif_{c}'] = di
        comp.append(linha); print(ano, 'ok', flush=True)
    for nome, L in [('15_parametros.csv', pars_all), ('15_comparacao.csv', comp)]:
        out = pd.concat(L) if nome == '15_parametros.csv' else pd.DataFrame(L)
        dest = f'{RES}/{nome}'
        if os.path.exists(dest):
            old = pd.read_csv(dest, sep=';'); out = pd.concat([old[~old['ano'].isin(anos)], out])
        out.sort_values('ano', kind='stable').to_csv(dest, sep=';', index=False, float_format='%.4f')
