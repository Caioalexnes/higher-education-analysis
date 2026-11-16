"""Federal versus for-profit gaps in raw Enade score and raw IDD, every edition with course-level IDD.

Reads the Conceito Enade and IDD spreadsheets of each edition (file names as published by INEP),
harmonizes column names and administrative categories, and computes the within-area gaps of
script 10 (federal and other categories versus private for-profit), with bootstrap intervals.
Output: results/12_serie_historica.csv
"""
import os, re, sys
import numpy as np
import pandas as pd
from config import DADOS, RES
import importlib.util
spec = importlib.util.spec_from_file_location('p', os.path.join(os.path.dirname(os.path.abspath(__file__)), '10_diferencas_pareadas.py'))
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

ARQ = {  # edition: (Conceito Enade file, IDD file); ('cpc', file) when the IDD is only published in the CPC spreadsheet
    2014: ('cpc', 'cpc2014_atualizado_em_04122017.xlsx'),
    2015: ('cpc', 'cpc_2015_portal_atualizado_03_10_2017.xls'),
    2016: ('resultado_enade2016_portal_06_09_2017.xlsx', 'resultado_IDD2016_portal_06_09_2017.xlsx'),
    2017: ('resultados_conceito_enade_2017.xlsx', 'resultados_IDD_2017.xlsx'),
    2018: ('resultados_conceito_enade_2018.xlsx', 'resultados_IDD_2018.xlsx'),
    2019: ('Conceito_Enade_2019.xlsx', 'IDD_2019.xlsx'),
    2021: ('conceito_enade_2021.xlsx', 'IDD_2021.xlsx'),
    2022: ('conceito_enade_2022.xlsx', 'idd_2022.xlsx'),
    2023: ('conceito_enade_2023.xlsx', 'IDD_2023.xlsx'),
}


def ler(arquivo):
    caminho = os.path.join(DADOS, arquivo)
    padrao = 'Código do Curso|Cód. do Curso|Código Curso|Nota Bruta - IDD'
    for aba in pd.ExcelFile(caminho).sheet_names:
        bruto = pd.read_excel(caminho, sheet_name=aba, header=None, nrows=15)
        linhas = [i for i in range(len(bruto)) if bruto.iloc[i].astype(str).str.contains(padrao, regex=True).any()]
        if linhas:
            d = pd.read_excel(caminho, sheet_name=aba, header=linhas[0])
            break
    else:
        raise ValueError(f'no course table in {arquivo}')
    d.columns = [re.sub(r'\s+', ' ', re.sub(r'\*', '', str(c))).strip() for c in d.columns]
    return d


def col(d, *padroes):
    for pd_ in padroes:
        for c in d.columns:
            if re.search(pd_, c, re.I):
                return c
    raise KeyError(f'{padroes} not in {list(d.columns)}')


def categoria(s):
    s = str(s)
    if 'Federal' in s: return 'Pública Federal'
    if 'Estadual' in s: return 'Pública Estadual'
    if 'Municipal' in s: return 'Pública Municipal'
    if 'com fins' in s.lower() or 'particular' in s.lower(): return 'Privada com fins lucrativos'
    if 'sem fins' in s.lower(): return 'Privada sem fins lucrativos'
    if 'comunit' in s.lower() or 'confessional' in s.lower(): return 'Comunitária/Confessional'
    if 'especial' in s.lower(): return 'Especial'
    if s.strip() == 'Privada': return 'Privada (não separada)'
    return s


def base(ano):
    fc, fi = ARQ[ano]
    num = lambda s: pd.to_numeric(s, errors='coerce')
    if fc == 'cpc':
        c = ler(fi)
        d = pd.DataFrame({'area': num(c[col(c, r'^Código da Área')]), 'categoria': c[col(c, r'Categoria Administrativa')].map(categoria),
                          'participantes': num(c[col(c, r'^Concluintes Participantes$')]),
                          'fg': num(c[col(c, r'Nota Bruta - FG')]), 'ce': num(c[col(c, r'Nota Bruta - CE')]),
                          'participantes_com_enem': num(c[col(c, r'Participantes com nota no Enem$')]),
                          'idd_bruto': num(c[col(c, r'Nota Bruta - IDD')])})
        d['nota_bruta'] = 0.25 * d['fg'] + 0.75 * d['ce']
        d = d.dropna(subset=['nota_bruta', 'idd_bruto'])
        return d[(d['participantes'] > 0) & (d['participantes_com_enem'] > 0)].reset_index(drop=True)
    c, i = ler(fc), ler(fi)
    a = pd.DataFrame({'curso': num(c[col(c, r'^Código do Curso')]), 'area': num(c[col(c, r'^Código da Área', r'Cód.*Área')]),
                      'categoria': c[col(c, r'Categoria Administrativa')].map(categoria),
                      'participantes': num(c[col(c, r'Concluintes Participantes$', r'Nº +de Concluintes Participantes')]),
                      'fg': num(c[col(c, r'Nota Bruta - FG')]), 'ce': num(c[col(c, r'Nota Bruta - CE')])})
    a['nota_bruta'] = 0.25 * a['fg'] + 0.75 * a['ce']
    b = pd.DataFrame({'curso': num(i[col(i, r'^Código do Curso')]),
                      'participantes_com_enem': num(i[col(i, r'Participantes com nota no Enem$')]),
                      'idd_bruto': num(i[col(i, r'Nota Bruta - IDD')])})
    d = a.merge(b, on='curso', how='inner').dropna(subset=['nota_bruta', 'idd_bruto'])
    return d[(d['participantes'] > 0) & (d['participantes_com_enem'] > 0)].reset_index(drop=True)


if __name__ == '__main__':
    anos = [int(a) for a in sys.argv[1:]] or sorted(ARQ)
    linhas = []
    PRIV = {'Privada com fins lucrativos', 'Privada sem fins lucrativos', 'Comunitária/Confessional', 'Privada (não separada)'}
    for ano in anos:
        d = base(ano)
        for nome_base, cats_base in [('private for-profit', {p.BASE}), ('all private', PRIV)]:
            b = d[d['categoria'].isin(cats_base)]
            if len(b) < 30:
                continue
            for cat in ['Pública Federal', 'Pública Estadual', 'Privada sem fins lucrativos', 'Comunitária/Confessional']:
                g = d[d['categoria'] == cat]
                if len(g) < 30 or cat in cats_base:
                    continue
                dn, di = p.pareada(g, b)
                icn, ici = p.boot(g, b, B=200)
                linhas.append(dict(ano=ano, base=nome_base, categoria=cat, cursos=len(g), areas=d['area'].nunique(), dif_nota=dn, ic_nota_inf=icn[0], ic_nota_sup=icn[1],
                                   dif_idd=di, ic_idd_inf=ici[0], ic_idd_sup=ici[1], parcela_selecao=1 - di / dn,
                                   sd_idd_cursos=d['idd_bruto'].std(),
                                   cobertura_enem_cat=g['participantes_com_enem'].sum() / g['participantes'].sum(),
                                   cobertura_enem_base=b['participantes_com_enem'].sum() / b['participantes'].sum()))
        print(ano, len(d), 'cursos', d['categoria'].value_counts().to_dict(), flush=True)
    out = pd.DataFrame(linhas)
    destino = f'{RES}/12_serie_historica.csv'
    if os.path.exists(destino) and sys.argv[1:]:
        old = pd.read_csv(destino, sep=';'); out = pd.concat([old[~old['ano'].isin(anos)], out]).sort_values(['base', 'ano', 'categoria'])
    out.to_csv(destino, sep=';', index=False, float_format='%.3f')
    print(out[['base', 'ano', 'categoria', 'cursos', 'dif_nota', 'dif_idd', 'parcela_selecao', 'sd_idd_cursos', 'cobertura_enem_cat', 'cobertura_enem_base']].round(2).to_string(index=False))
