"""Robustness of the federal minus for-profit gaps (Sections 6.1 and 6.4).

Parts (run separately; each writes its own output):
  presencial  In-person courses only, every edition with recomputed IDD (current method, script 15).
              The share of for-profit graduates in distance-learning courses is also reported.
  microdados  2022 and 2023, from the IDD microdata (script 15 reads them):
              (a) value added without shrinkage: the course mean residual (IDD / lambda);
              (b) Enem coefficients estimated within courses (course fixed effects, outliers with an
                  absolute standardized residual above 3 excluded and the model re-estimated), course
                  value added = course mean of C - X b_within;
              (c) raw score computed only over the graduates with an Enem score (same sample as the IDD).
  areas       Growth within each group of areas, restricted to the areas assessed in every edition of
              the group (group I: 2016, 2019, 2023; group II: 2017, 2021; group III: 2018, 2022),
              with all courses and with in-person courses only (common areas defined within each set).
              The increase between the group's first and last edition gets an interval from resampling
              institutions jointly across the two editions.
Gaps: equation (1) of the paper (script 10); intervals: bootstrap of institutions (B, default 1,000).
Course modality and institution: Conceito Enade spreadsheets (script 12).
Usage: python 21_robustez.py presencial | microdados | areas
Outputs: 21_presencial.csv, 21_microdados.csv, 21_areas_comuns.csv, 21_areas_comuns_aumento.csv
"""
import os, sys, importlib.util
import numpy as np
import pandas as pd
from config import RES
aqui = os.path.dirname(os.path.abspath(__file__))
def mod(nome, arq):
    s = importlib.util.spec_from_file_location(nome, os.path.join(aqui, arq)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
p = mod('p', '10_diferencas_pareadas.py'); s12 = mod('s12', '12_serie_historica.py')
B = int(os.environ.get('B', '1000'))
ANOS = (2016, 2017, 2018, 2019, 2021, 2022, 2023)
GRUPOS = {'I': (2016, 2019, 2023), 'II': (2017, 2021), 'III': (2018, 2022)}


def modalidade(ano):
    c = s12.ler(s12.ARQ[ano][0]); num = lambda s: pd.to_numeric(s, errors='coerce')
    m = pd.DataFrame({'curso': num(c[s12.col(c, r'^Código do Curso')]), 'modalidade': c[s12.col(c, r'Modalidade')].astype(str)})
    return m.drop_duplicates('curso')


def cursos(ano, col='idd_novo'):
    d = pd.read_csv(f'{RES}/15_idd_cursos_{ano}.csv', sep=';')
    d['idd_bruto'] = d[col]
    d = d.dropna(subset=['nota_bruta', 'idd_bruto', 'ies'])
    return d[(d['participantes'] > 0) & (d['participantes_com_enem'] > 0)].reset_index(drop=True)


def gap(d, ano, espec, ic=True):
    g, b = d[d['categoria'] == p.FED], d[d['categoria'] == p.BASE]
    dn, di = p.pareada(g, b)
    linha = dict(ano=ano, especificacao=espec, cursos_federais=len(g), cursos_base=len(b), dif_nota=dn, dif_idd=di, parcela_entrada=1 - di / dn)
    if ic:
        icn, ici = p.boot(g.reset_index(drop=True), b.reset_index(drop=True), B=B)
        linha.update(ic_nota_inf=icn[0], ic_nota_sup=icn[1], ic_idd_inf=ici[0], ic_idd_sup=ici[1])
    return linha


def salvar(nome, linhas):
    pd.DataFrame(linhas).to_csv(f'{RES}/{nome}', sep=';', index=False, float_format='%.4f'); print(pd.DataFrame(linhas).round(2).to_string(index=False))


def presencial():
    linhas = []
    for ano in ANOS:
        d = cursos(ano).merge(modalidade(ano), on='curso', how='left')
        b = d[d['categoria'] == p.BASE]
        ead = (b['modalidade'].str.contains('Dist') * b['participantes']).sum() / b['participantes'].sum()
        for espec, x in [('all courses', d), ('in-person only', d[d['modalidade'].str.contains('Presencial', na=False)])]:
            l = gap(x.reset_index(drop=True), ano, espec); l['ead_fins_lucrativos'] = ead; linhas.append(l)
        print(ano, 'ok', flush=True)
    salvar('21_presencial.csv', linhas)


def microdados():
    s15 = mod('s15', '15_idd_microdados.py'); linhas = []
    for ano in (2022, 2023):
        d = cursos(ano)
        linhas.append(gap(d, ano, 'current IDD', ic=False))
        x = cursos(ano).copy(); x = x[x['lambda'] > 0].reset_index(drop=True); x['idd_bruto'] = x['idd_novo'] / x['lambda']
        linhas.append(gap(x, ano, 'no shrinkage (course mean residual)', ic=False))
        m = s15.ler_microdados(ano); m = m[m['curso'].isin(d['curso'])]
        va, nota = [], []
        for a, da in m.groupby('area'):
            g = pd.factorize(da['curso'])[0]; y = da['C'].values.astype(float); X = da[['CN', 'CH', 'LC', 'MT']].values.astype(float)
            def fe(y, X, g):
                n = np.bincount(g); yd = y - (np.bincount(g, weights=y) / n)[g]
                Xd = X - np.column_stack([np.bincount(g, weights=X[:, j]) / n for j in range(X.shape[1])])[g]
                b = np.linalg.lstsq(Xd, yd, rcond=None)[0]; e = yd - Xd @ b
                return b, e, np.sqrt(e @ e / (len(y) - X.shape[1] - g.max() - 1))
            b, e, s = fe(y, X, g); keep = np.abs(e / s) <= 3
            b, _, _ = fe(y[keep], X[keep], pd.factorize(da['curso'].values[keep])[0])
            r = y - X @ b
            va.append(pd.DataFrame({'curso': da['curso'].values, 'r': r}).groupby('curso')['r'].mean())
            nota.append(da.groupby('curso')['C'].mean())
        va = pd.concat(va).rename('idd_fe').reset_index(); nota = pd.concat(nota).rename('nota_com_enem').reset_index()
        x = d.merge(va, on='curso').merge(nota, on='curso')
        linhas.append(gap(x.assign(idd_bruto=x['idd_fe']), ano, 'Enem coefficients within courses', ic=False))
        y2 = x.assign(nota_bruta=x['nota_com_enem'], participantes=x['participantes_com_enem'])
        linhas.append(gap(y2, ano, 'raw score of graduates with an Enem score only', ic=False))
        dv = d['idd_bruto'] - d.groupby('area')['idd_bruto'].transform('mean')
        linhas[-4]['dp_idd_cursos'] = dv.std()
        print(ano, 'ok', flush=True)
    salvar('21_microdados.csv', linhas)


def aumento(xs, anos, seed=1):
    """Increase in the value-added gap between the first and last edition of a group, with a 95% interval from
    resampling institutions jointly across the editions (an institution's courses in both editions together),
    separately for the federal group and the comparison group."""
    a0, a1 = anos[0], anos[-1]
    areas = np.array(sorted(set().union(*[set(xs[a]['area']) for a in anos])))
    def mats(d, ies):
        ii, aa = np.searchsorted(ies, d['ies'].values), np.searchsorted(areas, d['area'].values)
        M = np.zeros((4, len(ies), len(areas)))
        pn, pi = d['participantes'].values.astype(float), d['participantes_com_enem'].values.astype(float)
        for k, v in enumerate([pn, np.nan_to_num(pn * d['nota_bruta'].values), pi, np.nan_to_num(pi * d['idd_bruto'].values)]):
            np.add.at(M[k], (ii, aa), v)
        return M
    def gapM(cg, Mg, cb, Mb):
        tg, tb = np.einsum('i,kia->ka', cg, Mg), np.einsum('i,kia->ka', cb, Mb); ok = (tg[0] > 0) & (tb[0] > 0)
        return np.average(tg[3, ok] / tg[2, ok] - tb[3, ok] / tb[2, ok], weights=tg[2, ok])
    G = {a: xs[a][xs[a]['categoria'] == p.FED] for a in (a0, a1)}; Bs = {a: xs[a][xs[a]['categoria'] == p.BASE] for a in (a0, a1)}
    ig = np.unique(np.concatenate([G[a]['ies'].values for a in (a0, a1)])); ib = np.unique(np.concatenate([Bs[a]['ies'].values for a in (a0, a1)]))
    Mg = {a: mats(G[a], ig) for a in (a0, a1)}; Mb = {a: mats(Bs[a], ib) for a in (a0, a1)}
    est = gapM(np.ones(len(ig)), Mg[a1], np.ones(len(ib)), Mb[a1]) - gapM(np.ones(len(ig)), Mg[a0], np.ones(len(ib)), Mb[a0])
    rng, out = np.random.default_rng(seed), np.empty(B)
    for r in range(B):
        cg = np.bincount(rng.integers(0, len(ig), len(ig)), minlength=len(ig)); cb = np.bincount(rng.integers(0, len(ib), len(ib)), minlength=len(ib))
        out[r] = gapM(cg, Mg[a1], cb, Mb[a1]) - gapM(cg, Mg[a0], cb, Mb[a0])
    return est, np.percentile(out, [2.5, 97.5])


def areas():
    linhas, aum = [], []
    for grupo, anos in GRUPOS.items():
        ds = {a: cursos(a).merge(modalidade(a), on='curso', how='left') for a in anos}
        for rotulo, filtro in [('all courses', lambda d: d),
                               ('in-person only', lambda d: d[d['modalidade'].str.contains('Presencial', na=False)])]:
            xs = {a: filtro(d) for a, d in ds.items()}
            comuns = None
            for a, d in xs.items():
                ok = set(d[d['categoria'] == p.FED]['area']) & set(d[d['categoria'] == p.BASE]['area'])
                comuns = ok if comuns is None else comuns & ok
            xs = {a: d[d['area'].isin(comuns)].reset_index(drop=True) for a, d in xs.items()}
            for a, d in xs.items():
                l = gap(d, a, f'group {grupo}, areas common to {len(anos)} editions')
                l.update(grupo=grupo, cursos=rotulo, areas=len(comuns), areas_na_edicao=ds[a].pipe(filtro)['area'].nunique()); linhas.append(l)
            est, ic = aumento(xs, anos)
            aum.append(dict(grupo=grupo, cursos=rotulo, de=anos[0], ate=anos[-1], aumento_idd=est, ic_inf=ic[0], ic_sup=ic[1]))
            print(grupo, rotulo, sorted(comuns), flush=True)
    salvar('21_areas_comuns.csv', linhas); salvar('21_areas_comuns_aumento.csv', aum)


if __name__ == '__main__':
    {'presencial': presencial, 'microdados': microdados, 'areas': areas}[sys.argv[1]]()
