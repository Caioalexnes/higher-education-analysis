"""Builds LaTeX tables and figures for the paper from the replication outputs."""
import os
import pandas as pd, numpy as np
R = os.environ.get('RESULTS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')) + '/'
CATS = [('Pública Federal', 'Federal'), ('Pública Estadual', 'State'), ('Pública Municipal', 'Municipal'),
        ('Comunitária/Confessional', 'Community/confessional'), ('Privada sem fins lucrativos', 'Private non-profit'),
        ('Privada com fins lucrativos', 'Private for-profit'), ('Especial', 'Special')]
f1 = lambda x: f'{x:,.1f}'.replace(',', '{,}') if pd.notna(x) else '--'
f2 = lambda x: f'{x:.2f}' if pd.notna(x) else '--'
pct = lambda x: f'{100*x:.1f}' if pd.notna(x) else '--'
def save(name, s): open(f'tables/{name}.tex', 'w').write(s)

# Table 2: descriptives by category and year
rows = []
for ano in (2023,):
    d = pd.read_csv(f'{R}08_base_cursos_{ano}.csv', sep=';', low_memory=False)
    d = d.dropna(subset=['nota_bruta', 'idd_bruto']); d = d[(d.participantes > 0) & (d.participantes_com_enem > 0)]
    for c, en in CATS:
        y = d[d.categoria == c]
        if len(y) == 0: continue
        q = y.dropna(subset=['pct_escola_privada']); q = q[q.respondentes_qe > 0]
        rows.append(dict(ano=ano, categoria=en, cursos=len(y), part=int(y.participantes.sum()),
                         cov=y.participantes_com_enem.sum() / y.participantes.sum(),
                         ead=y.loc[y.modalidade == 'Educação a Distância', 'participantes'].sum() / y.participantes.sum(),
                         priv=np.average(q.pct_escola_privada, weights=q.respondentes_qe) if len(q) else np.nan,
                         ipv=y['inscritos_por_vaga_2018'].median() if 'inscritos_por_vaga_2018' in y else np.nan))
T = pd.DataFrame(rows)
s = ['\\begin{tabular}{lrrrrrr}', '\\toprule',
     'Category & Courses & Graduates & With Enem (\\%) & Distance (\\%) & Private HS (\\%) & Applicants/seat \\\\', '\\midrule']
for _, r in T.iterrows():
    s.append(f"{r['categoria']} & {r.cursos:,} & {r.part:,} & {pct(r['cov'])} & {pct(r.ead)} & {pct(r.priv)} & {f1(r.ipv)} \\\\".replace(',', '{,}'))
s.append('\\bottomrule')
s.append('\\end{tabular}')
save('tab_descriptives', '\n'.join(s))

# Table 3: matched gaps, 2022 and 2023 (current IDD method), from the series of script 12
m = pd.read_csv(f'{R}10_diferencas_pareadas.csv', sep=';')
se = pd.read_csv(f'{R}12_serie_historica.csv', sep=';'); se = se[se.categoria == 'Pública Federal']
SDA = pd.read_csv(f'{R}02_dp_aluno_2023.csv', sep=';').iloc[0, 0]
A = lambda ano, base: se[(se.ano == ano) & (se.base == base)].iloc[0]
s = ['\\begin{tabular}{lcc}', '\\toprule', ' & 2022 & 2023 \\\\', '\\midrule', '\\multicolumn{3}{l}{\\textit{Relative to private for-profit courses}} \\\\']
for base_, lab_ in [('private for-profit', ''), ('all private', '')]:
    if base_ == 'all private': s += ['\\midrule', '\\multicolumn{3}{l}{\\textit{Relative to all private courses}} \\\\']
    s.append('Raw Enade score gap (points) & ' + ' & '.join(f"{A(y,base_).dif_nota:.1f} [{A(y,base_).ic_nota_inf:.1f}, {A(y,base_).ic_nota_sup:.1f}]" for y in (2022, 2023)) + ' \\\\')
    s.append('Value-added (IDD) gap (points) & ' + ' & '.join(f"{A(y,base_).dif_idd:.2f} [{A(y,base_).ic_idd_inf:.2f}, {A(y,base_).ic_idd_sup:.2f}]" for y in (2022, 2023)) + ' \\\\')
    s.append('Share of the raw gap present at entry & ' + ' & '.join(f"{100*(1-A(y,base_).dif_idd/A(y,base_).dif_nota):.0f}\\%" for y in (2022, 2023)) + ' \\\\')
s += ['\\midrule', f"Value-added gap in student SD (for-profit) & -- & {A(2023,'private for-profit').dif_idd/SDA:.2f} \\\\",
      'Federal courses & ' + ' & '.join(f"{int(A(y,'private for-profit').cursos):,}".replace(',', '{,}') if A(y,'private for-profit').cursos >= 1000 else f"{int(A(y,'private for-profit').cursos)}" for y in (2022, 2023)) + ' \\\\',
      'Assessment areas & ' + ' & '.join(f"{int(A(y,'private for-profit').areas)}" for y in (2022, 2023)) + ' \\\\']
s += ['\\bottomrule', '\\end{tabular}']
save('tab_matched', '\n'.join(s))

# Table 4: regressions
r = pd.read_csv(f'{R}09_regressoes.csv', sep=';')
def get(mod, am, dep, var):
    x = r[(r.modelo == mod) & (r.amostra == am) & (r.dependente == dep) & (r.variavel == var)]
    return (x.coef.iloc[0], x.ep.iloc[0], int(x.n.iloc[0]), int(x.clusters.iloc[0]), x.r2.iloc[0]) if len(x) else (np.nan,)*5
def star(c, e):
    z = abs(c / e) if e else 0
    return '^{***}' if z > 3.291 else '^{**}' if z > 2.576 else '^{*}' if z > 1.96 else ''
cols = [('M1 area FE', '2023'), ('M2 + modality, organization, size, UF FE', '2023'), ('M3 + entrant composition (Census 2018)', '2023')]
for dep, nome in [('nota_bruta', 'raw'), ('idd_bruto', 'va')]:
    s = ['\\begin{tabular}{l' + 'c' * len(cols) + '}', '\\toprule',
         ' & (1) & (2) & (3) \\\\', '\\midrule']
    for var, en in [('federal', 'Federal'), ('state', 'State'), ('community_confessional', 'Community/confessional'), ('private_nonprofit', 'Private non-profit')]:
        cs = [get(mo, am, dep, var) for mo, am in cols]
        s.append(en + ' & ' + ' & '.join(f'${c[0]:.2f}{star(c[0], c[1])}$' if pd.notna(c[0]) else '' for c in cs) + ' \\\\')
        s.append(' & ' + ' & '.join(f'({c[1]:.2f})' if pd.notna(c[0]) else '' for c in cs) + ' \\\\')
    cs = [get(mo, am, dep, 'federal') for mo, am in cols]
    s.append('\\midrule')
    s.append('Area fixed effects & Yes & Yes & Yes \\\\')
    s.append('Modality, organization, size, UF FE & No & Yes & Yes \\\\')
    s.append('Entering-cohort composition & No & No & Yes \\\\')
    s.append('Courses & ' + ' & '.join(f'{c[2]:,}'.replace(',', '{,}') for c in cs) + ' \\\\')
    s.append('Institutions (clusters) & ' + ' & '.join(f'{c[3]:,}'.replace(',', '{,}') for c in cs) + ' \\\\')
    s.append('$R^2$ & ' + ' & '.join(f'{c[4]:.2f}' for c in cs) + ' \\\\')
    s += ['\\bottomrule', '\\end{tabular}']
    save(f'tab_reg_{nome}', '\n'.join(s))

# Table 5: selectivity
g = m[m.ano == 2023].set_index('grupo')
lab = [('All federal courses', 'All federal courses'), ('2 or more applicants per seat', '2 or more applicants per seat'),
       ('Fewer than 2 applicants per seat (2018)', 'Fewer than 2 applicants per seat'),
       ('Fewer than 2 applicants per seat, excluding exactly 1.0', '\\quad excluding courses reporting exactly 1.0'),
       ('Lowest demand tercile (within area)', 'Lowest-demand tercile (within area)'), ('Middle tercile', 'Middle tercile'), ('Highest tercile', 'Highest-demand tercile')]
s = ['\\begin{tabular}{lrrcc}', '\\toprule', 'Federal courses & Courses & Median applicants/seat & Raw score gap & Value-added gap \\\\', '\\midrule']
for k, en in lab:
    x = g.loc[k]
    s.append(f"{en} & {int(x.cursos):,} & {f1(x.insc_vaga_mediana)} & {x.dif_nota:.1f} [{x.ic_nota_inf:.1f}, {x.ic_nota_sup:.1f}] & {x.dif_idd:.2f} [{x.ic_idd_inf:.2f}, {x.ic_idd_sup:.2f}] \\\\".replace(',', '{,}', 1) if int(x.cursos) >= 1000 else
             f"{en} & {int(x.cursos)} & {f1(x.insc_vaga_mediana)} & {x.dif_nota:.1f} [{x.ic_nota_inf:.1f}, {x.ic_nota_sup:.1f}] & {x.dif_idd:.2f} [{x.ic_idd_inf:.2f}, {x.ic_idd_sup:.2f}] \\\\")
s += ['\\bottomrule', '\\end{tabular}']
save('tab_selectivity', '\n'.join(s))
s = ['\\begin{tabular}{lcccc}', '\\toprule', ' & \\multicolumn{2}{c}{Raw Enade score} & \\multicolumn{2}{c}{Value added (IDD)} \\\\',
     '\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}', ' & Main & Interaction & Main & Interaction \\\\', '\\midrule']
for mod, var, en in [('M4 + log(1+applicants per seat) x federal', ('log1_insc_vaga', 'fed_x_log1_insc_vaga'), 'log(1 + applicants per seat) $\\times$ federal'),
                     ('M5 + low demand (<2 applicants per seat) x federal', ('baixa_procura', 'fed_x_baixa_procura'), 'Low demand ($<$2) $\\times$ federal'),
                     ('M5b low demand x federal, excluding courses reporting exactly 1.0 applicant per seat', ('baixa_procura', 'fed_x_baixa_procura'), '\\quad excluding courses reporting exactly 1.0')]:
    vals = []
    for dep in ('nota_bruta', 'idd_bruto'):
        for v in var:
            c = get(mod, '2023', dep, v); vals.append(f'${c[0]:.2f}{star(c[0], c[1])}$ ({c[1]:.2f})')
    s.append(en + ' & ' + ' & '.join(vals) + ' \\\\')
s += ['\\bottomrule', '\\end{tabular}']
save('tab_interactions', '\n'.join(s))

# Table 6: robustness (federal coefficient)
rb = [('M2 + modality, organization, size, UF FE', '2023', 'Baseline (column 2)'),
      ('M2 robustness', '2023 unweighted', 'Unweighted'), ('M2 robustness', '2023 in-person only', 'In-person courses only'),
      ('M2 robustness', '2023 universities only', 'Universities only'), ('M2 robustness', '2023 >=20 graduates with Enem', '20 or more graduates with an Enem score'),
      ('M2 robustness', '2023 Enem coverage >= 50%', 'Enem coverage of 50\\% or more'), ('M2 + Enem coverage control', '2023', 'Controlling for Enem coverage')]
s = ['\\begin{tabular}{lcccr}', '\\toprule', 'Specification & Raw score & Value added & Share at entry & Courses \\\\', '\\midrule']
for mo, am, en in rb:
    n_ = get(mo, am, 'nota_bruta', 'federal'); v_ = get(mo, am, 'idd_bruto', 'federal')
    s.append(f"{en} & {n_[0]:.2f} ({n_[1]:.2f}) & {v_[0]:.2f} ({v_[1]:.2f}) & {100*(1-v_[0]/n_[0]):.0f}\\% & {n_[2]:,} \\\\".replace(',', '{,}'))
s += ['\\bottomrule', '\\end{tabular}']
save('tab_robustness', '\n'.join(s))

# Table 7: the IDD method, dispersion and federal gaps by course size (script 13)
dp = pd.read_csv(f'{R}13_dispersao_por_tamanho.csv', sep=';'); gp = pd.read_csv(f'{R}13_gap_por_tamanho.csv', sep=';')
ED = (2019, 2021, 2022, 2023)
s = ['\\begin{tabular}{lcccc}', '\\toprule', ' & \\multicolumn{2}{c}{Method until 2021} & \\multicolumn{2}{c}{Method from 2022} \\\\',
     '\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}', 'Graduates with an Enem score in the course & 2019 & 2021 & 2022 & 2023 \\\\', '\\midrule',
     '\\multicolumn{5}{l}{\\textit{A. Standard deviation of the raw IDD around the area mean (points)}} \\\\']
for fx, en in [('1-5', '1 to 5'), ('6-10', '6 to 10'), ('11-20', '11 to 20'), ('21-40', '21 to 40'), ('41-80', '41 to 80'), ('81-1000000', 'More than 80'), ('81+', 'More than 80')]:
    x = dp[dp.faixa == fx]
    if len(x) == 0: continue
    s.append(en + ' & ' + ' & '.join(f"{x[x.ano == a].dp_idd.iloc[0]:.2f}" for a in ED) + ' \\\\')
s += ['\\midrule', '\\multicolumn{5}{l}{\\textit{B. Federal minus private for-profit value-added gap (points)}} \\\\']
G2 = gp[gp.base == 'private for-profit']
for fx, en in [('1-14', '1 to 14'), ('15-39', '15 to 39'), ('40+', '40 or more'), ('all', 'All courses')]:
    x = G2[G2.faixa == fx]
    s.append(en + ' & ' + ' & '.join(f"{x[x.ano == a].dif_idd.iloc[0]:.2f}" for a in ED) + ' \\\\')
    s.append(' & ' + ' & '.join(f"\\scriptsize[{x[x.ano == a].ic_idd_inf.iloc[0]:.2f}, {x[x.ano == a].ic_idd_sup.iloc[0]:.2f}]" for a in ED) + ' \\\\')
s += ['\\midrule', '\\multicolumn{5}{l}{\\textit{C. Share of the raw gap present at entry (\\%)}} \\\\']
for fx, en in [('1-14', '1 to 14'), ('15-39', '15 to 39'), ('40+', '40 or more'), ('all', 'All courses')]:
    x = G2[G2.faixa == fx]
    s.append(en + ' & ' + ' & '.join(f"{100*x[x.ano == a].parcela_entrada.iloc[0]:.0f}" for a in ED) + ' \\\\')
s += ['\\bottomrule', '\\end{tabular}']
s = [__import__('re').sub(r'(?<![-\d])-(\d)', r'$-$\1', r) for r in s]
save('tab_method', '\n'.join(s))
print('method table', G2[G2.ano.isin(ED)][['ano','faixa','dif_nota','dif_idd','parcela_entrada']].round(2).to_string())

# Table 8: cost
cu = pd.read_csv(f'{R}03_custo_federais.csv', sep=';')
tc = pd.read_csv(f'{R}03_tercis.csv', sep=';')
md = pd.read_csv(f'{R}05_modelos.csv', sep=';')
s = ['\\begin{tabular}{lccc}', '\\toprule', 'Cost tercile & Universities & Cost per student (R\\$ thousand) & Value added (IDD) \\\\', '\\midrule']
for _, x in tc.iterrows():
    s.append(f"{['Lowest','Middle','Highest'][int(x.tercil)-1]} & {int(x.universidades)} & {x.custo_medio_mil:.1f} & {x.idd_medio:.2f} \\\\")
s += ['\\bottomrule', '\\end{tabular}']
save('tab_cost_terciles', '\n'.join(s))
print(md.to_string())
# Figure 1: coefficients by category (M1), 2019 and 2023
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax0 = plt.subplots(1, 1, figsize=(5.6, 3.4)); axs = [ax0]
cats = [('federal','Federal'),('state','State'),('community_confessional','Community/conf.'),('private_nonprofit','Private non-profit'),('municipal','Municipal')]
for ax, ano in zip(axs, ('2023',)):
    yy = np.arange(len(cats))
    for k, (dep, lab_, col, off) in enumerate([('nota_bruta','Raw score','#9aa4b1',0.18),('idd_bruto','Value added (IDD)','#2A78D6',-0.18)]):
        cs = [get('M1 area FE', ano, dep, v) for v, _ in cats]
        ax.barh(yy+off, [c[0] if pd.notna(c[0]) else 0 for c in cs], height=0.34, color=col, label=lab_,
                xerr=[1.96*c[1] if pd.notna(c[1]) else 0 for c in cs], error_kw=dict(lw=0.8))
    ax.set_yticks(yy); ax.set_yticklabels([c[1] for c in cats]); ax.axvline(0,color='k',lw=0.6)
    ax.set_title(f'Enade {ano}', fontsize=10); ax.set_xlabel('Points relative to private for-profit courses (same area)', fontsize=8)
    ax.invert_yaxis(); ax.tick_params(labelsize=8)
axs[0].legend(fontsize=8, loc='lower right', frameon=False)
plt.tight_layout(); plt.savefig('figures/fig_gaps.pdf'); plt.savefig('figures/fig_gaps.png', dpi=200)
# Figure 2: cost vs IDD
fig, ax = plt.subplots(figsize=(5.2, 3.6))
c2 = cu.dropna(subset=['idd_bruto_medio_rel_area'])
c2 = c2[(c2.sigla != 'UNIVASF') & (c2.formandos_com_enem >= 30)]
ax.scatter(c2.custo_por_aluno_presencial/1000, c2.idd_bruto_medio_rel_area, s=14, color='#2A78D6')
b = np.polyfit(c2.custo_por_aluno_presencial/1000, c2.idd_bruto_medio_rel_area, 1, w=None)
xs = np.linspace(c2.custo_por_aluno_presencial.min()/1000, c2.custo_por_aluno_presencial.max()/1000, 10); ax.plot(xs, np.polyval(b, xs), color='#52514E', lw=1)
ax.set_xlabel('Current cost per in-person undergraduate, 2024 (R$ thousand)', fontsize=8); ax.set_ylabel('Mean course IDD relative to area mean', fontsize=8)
ax.tick_params(labelsize=8); plt.tight_layout(); plt.savefig('figures/fig_cost.pdf'); plt.savefig('figures/fig_cost.png', dpi=200)
print('n universities in fig2', len(c2), 'slope', b[0])

# Table and figure: series across editions
s = pd.read_csv(f'{R}12_serie_historica.csv', sep=';')
f = s[s.categoria == 'Pública Federal']
grp = {2014: 'II', 2017: 'II', 2021: 'II', 2015: 'III', 2018: 'III', 2022: 'III', 2016: 'I', 2019: 'I', 2023: 'I'}
rows = ['\\begin{tabular}{ccrcccc}', '\\toprule',
        ' & & & \\multicolumn{2}{c}{vs.\\ private for-profit} & \\multicolumn{2}{c}{vs.\\ all private} \\\\',
        '\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}',
        'Edition & Area group & Federal courses & Raw score & Value added & Raw score & Value added \\\\', '\\midrule']
for ano in sorted(f.ano.unique()):
    a_ = f[(f.ano == ano) & (f.base == 'private for-profit')]; b_ = f[(f.ano == ano) & (f.base == 'all private')]
    fp = (f"{a_.dif_nota.iloc[0]:.1f} & {a_.dif_idd.iloc[0]:.2f} [{a_.ic_idd_inf.iloc[0]:.2f}, {a_.ic_idd_sup.iloc[0]:.2f}]") if len(a_) else '-- & --'
    ap = f"{b_.dif_nota.iloc[0]:.1f} & {b_.dif_idd.iloc[0]:.2f} [{b_.ic_idd_inf.iloc[0]:.2f}, {b_.ic_idd_sup.iloc[0]:.2f}]"
    rows.append(f"{ano} & {grp[ano]} & {int(b_.cursos.iloc[0]):,} & {fp} & {ap} \\\\".replace(',', '{,}', 1) if int(b_.cursos.iloc[0]) >= 1000 else f"{ano} & {grp[ano]} & {int(b_.cursos.iloc[0])} & {fp} & {ap} \\\\")
rows = [__import__('re').sub(r'(?<![-\d])-(\d)', r'$-$\1', r) for r in rows]
rows += ['\\bottomrule', '\\end{tabular}']
save('tab_series', '\n'.join(rows))
# Table: IDD recomputed from the student-level microdata (script 15)
rc = pd.read_csv(f'{R}15_comparacao.csv', sep=';').set_index('ano')
rows = ['\\begin{tabular}{cccccc}', '\\toprule',
        ' & & & \\multicolumn{2}{c}{Value-added gap} & Share of raw gap \\\\', '\\cmidrule(lr){4-5}',
        'Edition & Area group & Raw score gap & Published IDD & Current method & present at entry \\\\', '\\midrule']
for base_, lab_ in [('private for-profit', 'A. Relative to private for-profit courses'), ('all private', 'B. Relative to all private courses')]:
    rows.append(f'\\multicolumn{{6}}{{l}}{{\\textit{{{lab_}}}}} \\\\')
    for ano in rc.index:
        x = rc.loc[ano]; k = lambda c: x[f'{base_}: {c}']
        rows.append(f"{ano} & {grp[ano]} & {k('dif_nota'):.1f} & {k('dif_idd_bruto'):.2f} & {k('dif_idd_novo'):.2f} [{k('ic_idd_novo_inf'):.2f}, {k('ic_idd_novo_sup'):.2f}] & {100*(1-k('dif_idd_novo')/k('dif_nota')):.0f}\\% \\\\")
    if base_ == 'private for-profit': rows.append('\\midrule')
rows = [__import__('re').sub(r'(?<![-\d])-(\d)', r'$-$\1', r) for r in rows]
rows += ['\\bottomrule', '\\end{tabular}']
save('tab_recomputed', '\n'.join(rows))
# Figure 2: published and recomputed value-added gaps by group of areas (for-profit base)
fig, ax = plt.subplots(figsize=(6.4, 3.6))
cores = {'I': '#2A78D6', 'II': '#E07B39', 'III': '#3A9E5F'}
nomes = {'I': 'Group I (mainly health, agrarian)', 'II': 'Group II (mainly sciences, teacher training)', 'III': 'Group III (mainly applied social sciences)'}
for g_, cor in cores.items():
    anos = [a for a in rc.index if grp[a] == g_]
    y = [rc.loc[a, 'private for-profit: dif_idd_novo'] for a in anos]
    lo = [y[j] - rc.loc[a, 'private for-profit: ic_idd_novo_inf'] for j, a in enumerate(anos)]
    hi = [rc.loc[a, 'private for-profit: ic_idd_novo_sup'] - y[j] for j, a in enumerate(anos)]
    ax.errorbar(anos, y, yerr=[lo, hi], marker='o', color=cor, label=nomes[g_] + ', current method', capsize=2, lw=1.4)
    ax.plot(anos, [rc.loc[a, 'private for-profit: dif_idd_bruto'] for a in anos], marker='o', mfc='white', color=cor, ls='--', lw=1)
ax.plot([], [], color='0.4', ls='--', marker='o', mfc='white', label='Published IDD')
ax.axhline(0, color='k', lw=0.6); ax.axvspan(2019.6, 2020.4, color='0.9', zorder=0)
ax.axvline(2021.5, color='#52514E', lw=0.9, ls=':')
ax.set_xticks([2016, 2017, 2018, 2019, 2021, 2022, 2023]); ax.tick_params(labelsize=8)
ax.set_ylabel('Federal minus for-profit, IDD points', fontsize=8); ax.legend(fontsize=6.5, frameon=False, loc='upper left')
plt.tight_layout(); plt.savefig('figures/fig_series.pdf'); plt.savefig('figures/fig_series.png', dpi=200)
