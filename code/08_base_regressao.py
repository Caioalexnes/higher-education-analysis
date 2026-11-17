"""Course-level dataset for the regressions (script 09).

Merges, for each Enade cycle (2019 and 2023), the Conceito Enade and IDD spreadsheets
(scores, value added, Enem coverage, category, modality, academic organization, UF),
the share of graduates from private high schools (Enade questionnaire, from script 02)
and, for 2023, course characteristics of the entering cohort from the 2018 Higher
Education Census (applicants per seat, entrants' school origin, age, shift, ProUni/Fies,
quotas, enrollment size).
The 2019 IDD was computed with the method INEP used until 2021 (see script 13).
Outputs: results/08_base_cursos_2019.csv, results/08_base_cursos_2023.csv
"""
import re, zipfile
import numpy as np
import pandas as pd
from config import arq, RES


def limpa(cols):
    return [re.sub(r'\s+', ' ', re.sub(r'\*', '', c)).strip() for c in cols]


def planilhas(ano):
    ce = pd.read_excel(arq(f'conceito{ano}'))
    ce.columns = limpa(ce.columns)
    idd = pd.read_excel(arq(f'idd{ano}'))
    idd.columns = limpa(idd.columns)
    num = lambda s: pd.to_numeric(s, errors='coerce')
    a = pd.DataFrame({
        'curso': num(ce['Código do Curso']).astype('Int64'),
        'area': num(ce['Código da Área']).astype('Int64'),
        'area_nome': ce['Área de Avaliação'],
        'ies': num(ce['Código da IES']).astype('Int64'),
        'organizacao': ce['Organização Acadêmica'],
        'categoria': ce['Categoria Administrativa'],
        'modalidade': ce['Modalidade de Ensino'],
        'uf': ce['Sigla da UF'].astype(str).str.strip(),
        'municipio': num(ce['Código do Município']).astype('Int64'),
        'inscritos_enade': num(ce['Nº de Concluintes Inscritos']),
        'participantes': num(ce['Nº de Concluintes Participantes']),
        'fg': num(ce['Nota Bruta - FG']),
        'ce': num(ce['Nota Bruta - CE']),
        'conceito_continuo': num(ce['Conceito Enade (Contínuo)']),
    })
    a['nota_bruta'] = 0.25 * a['fg'] + 0.75 * a['ce']
    b = pd.DataFrame({
        'curso': num(idd['Código do Curso']).astype('Int64'),
        'participantes_com_enem': num(idd['Nº de Concluintes Participantes com nota no Enem']),
        'prop_com_enem': num(idd['Proporção de Concluintes participantes com nota no Enem']),
        'idd_bruto': num(idd['Nota Bruta - IDD']),
        'idd_continuo': num(idd['IDD (Contínuo)']),
    })
    d = a.merge(b, on='curso', how='left')
    q = pd.read_csv(f'{RES}/02_cursos_{ano}.csv', sep=';', usecols=['curso', 'respondentes_qe', 'pct_escola_privada'])
    q['curso'] = q['curso'].astype('Int64')
    return d.merge(q, on='curso', how='left')


def censo2018():
    z = zipfile.ZipFile(arq('censo2018'))
    n = [x for x in z.namelist() if x.upper().endswith('CURSOS_2018.CSV')][0]
    qt = ['QT_VG_NOVA', 'QT_INSC_VG_NOVA', 'QT_ING_VG_NOVA', 'QT_ING', 'QT_MAT', 'QT_ING_NOTURNO',
          'QT_ING_25_29', 'QT_ING_30_34', 'QT_ING_35_39', 'QT_ING_40_49', 'QT_ING_50_59', 'QT_ING_60_MAIS',
          'QT_ING_PROCESCPUBLICA', 'QT_ING_PROCESCPRIVADA', 'QT_ING_FIES', 'QT_ING_PROUNII', 'QT_ING_PROUNIP',
          'QT_ING_RESERVA_VAGA']
    c = pd.read_csv(z.open(n), sep=';', encoding='latin-1', usecols=['CO_CURSO', 'NO_REGIAO', 'IN_CAPITAL'] + qt,
                    low_memory=False)
    for k in qt:
        c[k] = pd.to_numeric(c[k], errors='coerce').fillna(0)
    g = c.groupby('CO_CURSO').agg({**{k: 'sum' for k in qt}, 'NO_REGIAO': 'first', 'IN_CAPITAL': 'max'}).reset_index()
    div = lambda x, y: np.where(y > 0, x / y.where(y > 0, 1), np.nan)
    out = pd.DataFrame({
        'curso': g['CO_CURSO'].astype('Int64'),
        'regiao': g['NO_REGIAO'],
        'capital': g['IN_CAPITAL'],
        'vagas_novas_2018': g['QT_VG_NOVA'],
        'inscritos_por_vaga_2018': div(g['QT_INSC_VG_NOVA'], g['QT_VG_NOVA']),
        'ocupacao_vagas_2018': div(g['QT_ING_VG_NOVA'], g['QT_VG_NOVA']),
        'ingressantes_2018': g['QT_ING'],
        'matriculas_2018': g['QT_MAT'],
        'ing_noturno_2018': div(g['QT_ING_NOTURNO'], g['QT_ING']),
        'ing_25mais_2018': div(g[['QT_ING_25_29', 'QT_ING_30_34', 'QT_ING_35_39', 'QT_ING_40_49', 'QT_ING_50_59',
                                  'QT_ING_60_MAIS']].sum(axis=1), g['QT_ING']),
        'ing_escola_privada_2018': div(g['QT_ING_PROCESCPRIVADA'], g['QT_ING_PROCESCPUBLICA'] + g['QT_ING_PROCESCPRIVADA']),
        'ing_fies_2018': div(g['QT_ING_FIES'], g['QT_ING']),
        'ing_prouni_2018': div(g['QT_ING_PROUNII'] + g['QT_ING_PROUNIP'], g['QT_ING']),
        'ing_reserva_2018': div(g['QT_ING_RESERVA_VAGA'], g['QT_ING']),
    })
    return out


if __name__ == '__main__':
    d19 = planilhas(2019)
    d19.to_csv(f'{RES}/08_base_cursos_2019.csv', sep=';', index=False)
    d23 = planilhas(2023).merge(censo2018(), on='curso', how='left')
    d23.to_csv(f'{RES}/08_base_cursos_2023.csv', sep=';', index=False)
    for nome, d in [('2019', d19), ('2023', d23)]:
        print(nome, len(d), 'cursos;', d['idd_bruto'].notna().sum(), 'com IDD;', d['categoria'].value_counts().to_dict())
    print('2023 com Censo 2018:', d23['inscritos_por_vaga_2018'].notna().sum())
