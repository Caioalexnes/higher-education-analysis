"""Right tail: where a federal university's cut-off scores fall in the Enem distribution.

Distribution of the simple mean of the five Enem 2024 scores (participants present in the four
objective tests and with an essay score) and position of the general-competition cut-off scores of
the Federal University of Ceara in Sisu 2025, which used Enem 2024 with weight 1 on every test
(Sisu 2025 adhesion term), so that the cut-off is a simple mean comparable to the chart.
For each cut-off: share of participants with an equal or higher mean and, among 2024
secondary-school graduates (who report their school), the school network.
Sources: Enem 2024 microdata (INEP), file RESULTADOS_2024.csv;
UFC, Notas de corte Sisu 2025, https://sisu.ufc.br/wp-content/uploads/2025/12/notas-de-corte-sisu-ufc-2025.pdf
Outputs: 07_enem2024_histograma.csv, 07_cortes_ufc.csv, 07_resumo.csv, 07_figura_cauda_direita.pdf
Usage: python 07_cauda_direita.py            (computes from the microdata and draws)
       python 07_cauda_direita.py --figura   (draws only, from the CSVs)
"""
import os, sys, csv, zipfile
import numpy as np
from config import arq, salvar_csv, RES, BASE

# Ampla concorrência, chamada regular do Sisu 2025 (UFC, PDF citado acima)
CORTES_UFC = [
    ('Medicina', 'Fortaleza', 804.14),
    ('Direito (integral)', 'Fortaleza', 774.00),
    ('Engenharia Civil', 'Fortaleza', 707.28),
    ('Agronomia', 'Fortaleza', 641.76),
    ('Engenharia de Minas', 'Crateús', 619.86),
]
REDE = {1: 'federal', 2: 'estadual', 3: 'municipal', 4: 'privada'}


def ler_enem():
    import pandas as pd
    z = zipfile.ZipFile(arq('enem2024'))
    n = [x for x in z.namelist() if x.endswith('RESULTADOS_2024.csv')][0]
    pres = ['TP_PRESENCA_CN', 'TP_PRESENCA_CH', 'TP_PRESENCA_LC', 'TP_PRESENCA_MT']
    notas = ['NU_NOTA_LC', 'NU_NOTA_CH', 'NU_NOTA_CN', 'NU_NOTA_MT', 'NU_NOTA_REDACAO']
    med, rede = [], []
    for ch in pd.read_csv(z.open(n), sep=';', encoding='latin-1', usecols=pres + notas + ['TP_DEPENDENCIA_ADM_ESC'],
                          chunksize=1_000_000, dtype='float32'):
        ok = (ch[pres] == 1).all(axis=1) & ch['NU_NOTA_REDACAO'].notna()
        c = ch[ok]
        med.append(c[notas].mean(axis=1).to_numpy()); rede.append(c['TP_DEPENDENCIA_ADM_ESC'].fillna(0).to_numpy())
    return np.concatenate(med), np.concatenate(rede)


def calcular():
    m, rede = ler_enem()
    conc = rede > 0
    bins = np.arange(200, 900, 10)
    h, _ = np.histogram(m, bins=bins)
    salvar_csv('07_enem2024_histograma.csv', [[int(b), int(x), round(100 * x / len(m), 4)] for b, x in zip(bins[:-1], h)],
               ['inicio_faixa', 'participantes', 'pct_participantes'])
    out = []
    for curso, campus, c in CORTES_UFC:
        a = m >= c; ac = a & conc
        sh = {k: round(100 * (ac & (rede == k)).sum() / ac.sum(), 1) for k in REDE}
        out.append([curso, campus, c, round(100 * a.mean(), 2), int(a.sum()), int(ac.sum()), sh[4], sh[1], round(sh[2] + sh[3], 1)])
    salvar_csv('07_cortes_ufc.csv', out, ['curso', 'campus', 'nota_corte_ac', 'pct_participantes_acima', 'participantes_acima',
                                           'concluintes_acima', 'pct_privada', 'pct_federal', 'pct_estadual_municipal'])
    sh = {k: round(100 * (conc & (rede == k)).sum() / conc.sum(), 1) for k in REDE}
    salvar_csv('07_resumo.csv', [[len(m), round(float(m.mean()), 1), round(float(m.std()), 1), *[round(float(np.percentile(m, q)), 1) for q in (50, 75, 90, 99)],
                                  int(conc.sum()), sh[4], sh[1], round(sh[2] + sh[3], 1)]],
               ['participantes', 'media', 'dp', 'p50', 'p75', 'p90', 'p99', 'concluintes', 'pct_privada_concluintes', 'pct_federal_concluintes', 'pct_estadual_municipal_concluintes'])


def ler(nome):
    with open(os.path.join(RES, nome), encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter=';'))


def br(x, d=1):
    return f'{x:.{d}f}'.replace('.', ',')


def figura(saida=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if 'pagella' in f.lower():
            font_manager.fontManager.addfont(f)
    if any('Pagella' in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams['font.family'] = 'TeX Gyre Pagella'
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#52514e', 'axes.labelcolor': '#0b0b0b',
                         'xtick.color': '#52514e', 'ytick.color': '#52514e'})
    hist = ler('07_enem2024_histograma.csv'); cortes = ler('07_cortes_ufc.csv'); res = ler('07_resumo.csv')[0]
    x = np.array([int(r['inicio_faixa']) for r in hist]); y = np.array([float(r['pct_participantes']) for r in hist])
    AZUL, CINZA, TINTA, TINTA2 = '#2a78d6', '#b9b8b2', '#0b0b0b', '#52514e'
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.1, 6.0), gridspec_kw={'height_ratios': [1.35, 1], 'hspace': 0.55})
    a1.bar(x + 5, y, width=9.2, color=AZUL, linewidth=0)
    a1.set_xlim(250, 860); a1.set_ylim(0, y.max() * 1.55)
    a1.set_xlabel('Média simples das cinco notas do Enem 2024')
    a1.set_ylabel('% dos participantes\n(faixas de 10 pontos)')
    a1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v, 0)))
    for s in ('top', 'right'):
        a1.spines[s].set_visible(False)
    marcar = [c for c in cortes if c['curso'] in ('Medicina', 'Engenharia Civil', 'Agronomia')]
    alturas = {'Agronomia': 0.97, 'Engenharia Civil': 0.70, 'Medicina': 0.97}
    for c in marcar:
        v = float(c['nota_corte_ac']); top = a1.get_ylim()[1]
        a1.axvline(v, color=TINTA2, linewidth=1, linestyle=(0, (3, 2)))
        pct = float(c['pct_participantes_acima'])
        nome = c['curso'].replace('Engenharia', 'Eng.')
        txt = f"{nome}\ncorte {br(v, 0)}\nacima: {br(pct, 2 if pct < 1 else 1)}%"
        direita = c['curso'] == 'Engenharia Civil'
        a1.text(v + 4 if direita else v - 4, top * alturas[c['curso']], txt, ha='left' if direita else 'right', va='top',
                fontsize=7.5, color=TINTA, linespacing=1.15)
    a1.set_title('A. Onde ficam as notas de corte da UFC (Sisu 2025, ampla concorrência)', loc='left', fontsize=9.5, color=TINTA)
    nomes = [c['curso'] for c in marcar] + ['Todos os concluintes']
    vals = [float(c['pct_privada']) for c in marcar] + [float(res['pct_privada_concluintes'])]
    cores = [AZUL] * len(marcar) + [CINZA]
    ys = np.arange(len(nomes))[::-1]
    a2.barh(ys, vals, color=cores, height=0.62)
    for yy, v in zip(ys, vals):
        a2.text(v + 1.5, yy, br(v) + '%', va='center', fontsize=8.5, color=TINTA)
    a2.set_yticks(ys); a2.set_yticklabels(['Acima do corte de ' + n if n != 'Todos os concluintes' else n for n in nomes])
    a2.set_xlim(0, 100); a2.set_xlabel('% vindos de escola particular, entre os que terminavam o ensino médio em 2024')
    for s in ('top', 'right'):
        a2.spines[s].set_visible(False)
    a2.set_title('B. Quem fica acima da linha', loc='left', fontsize=9.5, color=TINTA)
    saida = saida or os.path.join(RES, '07_figura_cauda_direita.pdf')
    fig.savefig(saida, bbox_inches='tight'); fig.savefig(saida.replace('.pdf', '.png'), dpi=200, bbox_inches='tight')
    print('figura:', saida)


if __name__ == '__main__':
    if '--figura' not in sys.argv:
        calcular()
    figura(sys.argv[sys.argv.index('--saida') + 1] if '--saida' in sys.argv else None)
