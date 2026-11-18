"""Within-area (matched) differences between federal and private for-profit courses.

Replaces the comparison of scripts 02 and 06, which subtracted the national mean of the
for-profit courses' area deviations from that of the federal courses. Because federal and
for-profit courses are distributed differently across assessment areas, that comparison
mixes area composition into the gap. Here, for each area, the federal group's mean is
compared with the for-profit mean of the same area, and the area gaps are averaged with
weights equal to the federal group's graduates (participants for the raw score;
participants with an Enem score for the IDD). 95% intervals: bootstrap that resamples
institutions (all courses of an institution together), separately for the federal group and
the comparison group (1,000 replications, as in scripts 12, 13, 15 and 21).
Outputs: results/10_diferencas_pareadas.csv
"""
import numpy as np
import pandas as pd
from config import RES

FED, BASE = 'Pública Federal', 'Privada com fins lucrativos'
SD = pd.read_csv(f'{RES}/02_dp_aluno_2023.csv', sep=';')['dp_nota_geral_dentro_da_area'].iloc[0]


def carrega(ano):
    d = pd.read_csv(f'{RES}/08_base_cursos_{ano}.csv', sep=';', low_memory=False)
    d = d.dropna(subset=['nota_bruta', 'idd_bruto'])
    return d[(d['participantes'] > 0) & (d['participantes_com_enem'] > 0)]


def pareada(g, b):
    wn = lambda x, v, w: (x[v] * x[w]).sum() / x[w].sum()
    rows = []
    for a, ga in g.groupby('area'):
        ba = b[b['area'] == a]
        if len(ba) == 0:
            continue
        rows.append((ga['participantes'].sum(), ga['participantes_com_enem'].sum(),
                     wn(ga, 'nota_bruta', 'participantes') - wn(ba, 'nota_bruta', 'participantes'),
                     wn(ga, 'idd_bruto', 'participantes_com_enem') - wn(ba, 'idd_bruto', 'participantes_com_enem')))
    r = np.array(rows)
    return np.average(r[:, 2], weights=r[:, 0]), np.average(r[:, 3], weights=r[:, 1])


def _somas(d, areas):
    """Per institution and area: participants, participants x raw score, participants with Enem, those x IDD."""
    ies, ii = np.unique(d['ies'].values, return_inverse=True)
    aa = np.searchsorted(areas, d['area'].values)
    M = np.zeros((4, len(ies), len(areas)))
    pn, pi = d['participantes'].values.astype(float), d['participantes_com_enem'].values.astype(float)
    # products with missing scores count as zero, as pandas' sum does in pareada()
    for k, v in enumerate([pn, np.nan_to_num(pn * d['nota_bruta'].values), pi, np.nan_to_num(pi * d['idd_bruto'].values)]):
        np.add.at(M[k], (ii, aa), v)
    return M


def boot(g, b, B=1000, seed=1):
    """Percentile intervals from resampling institutions (column 'ies'), separately in each group.

    Each replication draws, with replacement, as many institutions as the group has and keeps all
    their courses; the gap is then computed exactly as in pareada(), from area totals.
    """
    if g['ies'].isna().any() or b['ies'].isna().any():
        raise ValueError('courses without institution code')
    rng = np.random.default_rng(seed)
    areas = np.unique(np.concatenate([g['area'].values, b['area'].values]))
    Mg, Mb = _somas(g, areas), _somas(b, areas)
    out = np.empty((B, 2))
    for r in range(B):
        cg = np.bincount(rng.integers(0, Mg.shape[1], Mg.shape[1]), minlength=Mg.shape[1])
        cb = np.bincount(rng.integers(0, Mb.shape[1], Mb.shape[1]), minlength=Mb.shape[1])
        tg = np.einsum('i,kia->ka', cg, Mg); tb = np.einsum('i,kia->ka', cb, Mb)
        ok = (tg[0] > 0) & (tb[0] > 0)
        dn = tg[1, ok] / tg[0, ok] - tb[1, ok] / tb[0, ok]
        di = tg[3, ok] / tg[2, ok] - tb[3, ok] / tb[2, ok]
        out[r] = np.average(dn, weights=tg[0, ok]), np.average(di, weights=tg[2, ok])
    return np.percentile(out[:, 0], [2.5, 97.5]), np.percentile(out[:, 1], [2.5, 97.5])


if __name__ == '__main__':
    linhas = []
    for ano in (2019, 2023):
        d = carrega(ano).reset_index(drop=True)
        b = d[d['categoria'] == BASE]
        fed = d[d['categoria'] == FED]
        grupos = [('All federal courses', fed)]
        if ano == 2023:
            iv = fed['inscritos_por_vaga_2018']
            grupos += [('Fewer than 2 applicants per seat (2018)', fed[iv < 2]),
                       ('Fewer than 2 applicants per seat, excluding exactly 1.0', fed[(iv < 2) & ~np.isclose(iv, 1.0)]),
                       ('2 or more applicants per seat', fed[iv >= 2])]
            t = fed[iv.notna()].copy()
            t['tercil'] = t.groupby('area')['inscritos_por_vaga_2018'].transform(
                lambda s: pd.qcut(s.rank(method='first'), 3, labels=False) if len(s) >= 3 else np.nan)
            for k, nome in [(0, 'Lowest demand tercile (within area)'), (1, 'Middle tercile'), (2, 'Highest tercile')]:
                grupos.append((nome, t[t['tercil'] == k]))
        for nome, g in grupos:
            dn, di = pareada(g, b)
            icn, ici = boot(g, b)
            linhas.append(dict(ano=ano, grupo=nome, cursos=len(g), dif_nota=dn, ic_nota_inf=icn[0], ic_nota_sup=icn[1],
                               dif_idd=di, ic_idd_inf=ici[0], ic_idd_sup=ici[1], parcela_selecao=1 - di / dn,
                               idd_em_dp_aluno=di / SD,
                               insc_vaga_mediana=g['inscritos_por_vaga_2018'].median() if 'inscritos_por_vaga_2018' in g else np.nan))
    out = pd.DataFrame(linhas)
    out.to_csv(f'{RES}/10_diferencas_pareadas.csv', sep=';', index=False, float_format='%.4f')
    print(out.round(2).to_string(index=False))
