"""Diagnostics of the federal value-added gap in 2019 and 2023.

(1) dispersion of the course-level raw IDD in each edition; (2) the gap restricted to the areas
assessed in both editions; (3) the gap in the balanced panel of courses present in both editions;
(4) Enem coverage (share of graduates with a recovered Enem score) by category; (5) distance-learning
share of graduates by category; (6) the gap by Enem coverage band. Depends on scripts 08 and 10.
The 2019 IDD was computed with the method INEP used until 2021, which pulls course effects toward
zero (script 13), so differences between the 2019 and 2023 rows mainly reflect the change of method.
The paper uses only the 2023 gap by Enem coverage band.
Output: results/11_diagnostico.csv (long format: item; ano; grupo; valor)
"""
import numpy as np
import pandas as pd
from config import RES
import importlib.util
spec = importlib.util.spec_from_file_location('p', __file__.replace('11_diagnostico_2019_2023.py', '10_diferencas_pareadas.py'))
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

FED, BASE = p.FED, p.BASE
out = []
put = lambda item, ano, grupo, valor: out.append(dict(item=item, ano=ano, grupo=grupo, valor=valor))
d = {a: p.carrega(a).reset_index(drop=True) for a in (2019, 2023)}
wavg = lambda x, v, w: (x[v] * x[w]).sum() / x[w].sum()

for a, x in d.items():
    put('sd_idd_curso', a, 'all', x['idd_bruto'].std())
    put('sd_nota_curso', a, 'all', x['nota_bruta'].std())
    put('areas', a, 'all', x['area'].nunique())
    for cat in (FED, BASE):
        y = x[x['categoria'] == cat]
        put('cobertura_enem', a, cat, y['participantes_com_enem'].sum() / y['participantes'].sum())
        put('participantes', a, cat, y['participantes'].sum())
        put('pct_ead', a, cat, y.loc[y['modalidade'] == 'Educação a Distância', 'participantes'].sum() / y['participantes'].sum())
    dn, di = p.pareada(x[x['categoria'] == FED], x[x['categoria'] == BASE])
    put('gap_nota', a, 'all areas', dn); put('gap_idd', a, 'all areas', di)
    put('gap_idd_em_dp_curso', a, 'all areas', di / x['idd_bruto'].std())

comuns = set(d[2019]['area']) & set(d[2023]['area'])
painel = set(d[2019]['curso']) & set(d[2023]['curso'])
for a, x in d.items():
    put('areas_comuns', a, 'n', len(comuns))
    for nome, y in [('common areas', x[x['area'].isin(comuns)]), ('balanced course panel', x[x['curso'].isin(painel)])]:
        dn, di = p.pareada(y[y['categoria'] == FED], y[y['categoria'] == BASE])
        put('gap_nota', a, nome, dn); put('gap_idd', a, nome, di)
        put('cursos_federais', a, nome, (y['categoria'] == FED).sum())
    # by Enem coverage band (course level)
    for lo, hi in [(0, 0.5), (0.5, 0.8), (0.8, 1.01)]:
        y = x[(x['prop_com_enem'] >= lo) & (x['prop_com_enem'] < hi)]
        f, b = y[y['categoria'] == FED], y[y['categoria'] == BASE]
        if len(f) > 20 and len(b) > 20:
            dn, di = p.pareada(f, b)
            put('gap_idd_por_cobertura', a, f'{lo:.1f}-{min(hi, 1):.1f}', di)
            put('gap_nota_por_cobertura', a, f'{lo:.1f}-{min(hi, 1):.1f}', dn)
# within-course change, balanced panel: federal minus for-profit, area-matched
m = d[2019][['curso', 'area', 'categoria', 'idd_bruto', 'nota_bruta', 'participantes_com_enem', 'participantes']].merge(
    d[2023][['curso', 'idd_bruto', 'nota_bruta']], on='curso', suffixes=('_19', '_23'))
m['d_idd'] = m['idd_bruto_23'] - m['idd_bruto_19']
m['d_nota'] = m['nota_bruta_23'] - m['nota_bruta_19']
for cat in (FED, BASE):
    y = m[m['categoria'] == cat]
    put('mudanca_idd_mesmo_curso', '2019-2023', cat, wavg(y, 'd_idd', 'participantes_com_enem'))
    put('mudanca_nota_mesmo_curso', '2019-2023', cat, wavg(y, 'd_nota', 'participantes'))
    put('cursos_no_painel', '2019-2023', cat, len(y))
o = pd.DataFrame(out)
o.to_csv(f'{RES}/11_diagnostico.csv', sep=';', index=False, float_format='%.4f')
print(o.round(3).to_string(index=False))
