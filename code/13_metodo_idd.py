"""How the IDD method affects comparisons between institution types.

Up to the 2021 edition, INEP computed the raw IDD of a course as the mean, over its graduates,
of the observed Enade score minus a predicted score that already included the course's estimated
random intercept (NT 34/2020, NT 8/2022; ter Haar 2021). From 2022 on, the raw IDD is the course's
estimated random intercept itself (NT 29/2023). In a random-intercept model, the first quantity is
(1 - lambda_c) times the course's mean residual and the second is lambda_c times it, where lambda_c
grows with the number of graduates. The old IDD therefore shrinks toward zero as courses grow, and
the new one shrinks toward zero as courses get smaller.

This script documents the consequence in every edition with course-level IDD:
  (a) dispersion of the raw IDD (relative to the area mean) by number of graduates with an Enem score;
  (b) within-area federal minus private gaps (script 10) by the same size bands.
Outputs: results/13_dispersao_por_tamanho.csv, results/13_gap_por_tamanho.csv
"""
import os, sys
import numpy as np
import pandas as pd
from config import RES
import importlib.util
aqui = os.path.dirname(os.path.abspath(__file__))
def mod(nome, arq):
    s = importlib.util.spec_from_file_location(nome, os.path.join(aqui, arq)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
p = mod('p', '10_diferencas_pareadas.py')
s12 = mod('s12', '12_serie_historica.py')

FAIXAS_SD = [(1, 5), (6, 10), (11, 20), (21, 40), (41, 80), (81, 10**6)]
FAIXAS_GAP = [(1, 14), (15, 39), (40, 10**6)]
PRIV = {'Privada com fins lucrativos', 'Privada sem fins lucrativos', 'Comunitária/Confessional', 'Privada (não separada)'}
B = int(os.environ.get('B', '0'))

if __name__ == '__main__':
    anos = [int(a) for a in sys.argv[1:]] or sorted(s12.ARQ)
    disp, gaps = [], []
    for ano in anos:
        d = s12.base(ano)
        d['desvio'] = d['idd_bruto'] - d.groupby('area')['idd_bruto'].transform('mean')
        n = d['participantes_com_enem']
        for lo, hi in FAIXAS_SD:
            x = d.loc[(n >= lo) & (n <= hi), 'desvio']
            disp.append(dict(ano=ano, faixa=f'{lo}-{hi}' if hi < 10**6 else f'{lo}+', cursos=len(x), dp_idd=x.std()))
        for nome_base, cats in [('private for-profit', {p.BASE}), ('all private', PRIV)]:
            b0 = d[d['categoria'].isin(cats)]
            if len(b0) < 30:
                continue
            for lo, hi in FAIXAS_GAP + [(1, 10**6)]:
                sel = (n >= lo) & (n <= hi)
                g, b = d[sel & (d['categoria'] == p.FED)], d[sel & d['categoria'].isin(cats)]
                if len(g) < 10:
                    continue
                dn, di = p.pareada(g, b)
                linha = dict(ano=ano, base=nome_base, faixa='all' if hi == 10**6 and lo == 1 else (f'{lo}-{hi}' if hi < 10**6 else f'{lo}+'),
                             cursos_federais=len(g), dif_nota=dn, dif_idd=di, parcela_entrada=1 - di / dn)
                if B:
                    icn, ici = p.boot(g, b, B=B)
                    linha.update(ic_idd_inf=ici[0], ic_idd_sup=ici[1])
                gaps.append(linha)
        print(ano, 'ok', flush=True)
    for nome, linhas in [('13_dispersao_por_tamanho.csv', disp), ('13_gap_por_tamanho.csv', gaps)]:
        out = pd.DataFrame(linhas); destino = f'{RES}/{nome}'
        if os.path.exists(destino) and sys.argv[1:]:
            old = pd.read_csv(destino, sep=';'); out = pd.concat([old[~old['ano'].isin(anos)], out])
        out.sort_values(['ano'] + (['base'] if 'base' in out else []), kind='stable').to_csv(destino, sep=';', index=False, float_format='%.3f')
