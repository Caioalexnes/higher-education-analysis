"""Low-demand federal courses: does the advantage over private institutions persist where
the federal course does not select?

Competition for each course in the typical entry year of the Enade 2023 cohort (2018 Census):
applicants per new seat and seat occupancy (entrants through new seats divided by new seats).
Federal courses are divided into three competition groups within each assessment area. For each
group, the difference relative to private for-profit courses in the raw score and in the raw IDD
(points, relative to the area mean) is computed as in script 02. The within-area comparison used
in the paper is in script 10.
Outputs: 06_disputa_por_categoria.csv, 06_por_concorrencia.csv, 06_por_ocupacao.csv, 06_por_area.csv
Depends on results/02_cursos_2023.csv.
"""
import csv, io, zipfile, collections, random
import numpy as np
from config import arq, salvar_csv, RES

FED, BASE = 'Pública Federal', 'Privada com fins lucrativos'


def censo2018():
    z = zipfile.ZipFile(arq('censo2018'))
    n = [x for x in z.namelist() if x.upper().endswith('CURSOS_2018.CSV')][0]
    r = csv.reader(io.TextIOWrapper(z.open(n), encoding='latin-1', newline=''), delimiter=';')
    h = next(r); ix = {k: i for i, k in enumerate(h)}
    g = lambda row, k: int(row[ix[k]]) if row[ix[k]].strip().isdigit() else 0
    d = collections.defaultdict(lambda: [0, 0, 0])
    for row in r:
        c = d[row[ix['CO_CURSO']]]
        c[0] += g(row, 'QT_VG_NOVA'); c[1] += g(row, 'QT_INSC_VG_NOVA'); c[2] += g(row, 'QT_ING_VG_NOVA')
    return d


def cursos():
    out = []
    with open(f'{RES}/02_cursos_2023.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter=';'):
            try:
                out.append(dict(curso=r['curso'], area=r['area'], cat=r['categoria'], wn=float(r['participantes']), nt=float(r['nota_bruta']),
                                wi=float(r['participantes_com_enem']), idd=float(r['idd_bruto'])))
            except (ValueError, TypeError):
                pass
    out = [c for c in out if c['wn'] > 0 and c['wi'] > 0]
    g = collections.defaultdict(list)
    for c in out:
        g[c['area']].append(c)
    for vs in g.values():
        mn = sum(c['wn'] * c['nt'] for c in vs) / sum(c['wn'] for c in vs)
        mi = sum(c['wi'] * c['idd'] for c in vs) / sum(c['wi'] for c in vs)
        for c in vs:
            c['nt_d'], c['idd_d'] = c['nt'] - mn, c['idd'] - mi
    return out


def media(L, k, w):
    sw = sum(c[w] for c in L)
    return sum(c[w] * c[k] for c in L) / sw if sw else float('nan')


def dif(grupo, base):
    return media(grupo, 'nt_d', 'wn') - media(base, 'nt_d', 'wn'), media(grupo, 'idd_d', 'wi') - media(base, 'idd_d', 'wi')


def ic(grupo, base, B=300):
    random.seed(1); a, b = [], []
    for _ in range(B):
        g2 = [random.choice(grupo) for _ in grupo]; b2 = [random.choice(base) for _ in base]
        x, y = dif(g2, b2); a.append(x); b.append(y)
    return [round(float(np.percentile(a, q)), 1) for q in (2.5, 97.5)], [round(float(np.percentile(b, q)), 2) for q in (2.5, 97.5)]


def main():
    c18 = censo2018(); cs = cursos()
    for c in cs:
        v = c18.get(c['curso'])
        if v and v[0] > 0:
            c['insc_vaga'] = v[1] / v[0]; c['ocup'] = v[2] / v[0]
    # disputa por categoria administrativa (cursos do Enade 2023 com vagas novas em 2018)
    out = []
    for cat in sorted(set(c['cat'] for c in cs)):
        r = [c['insc_vaga'] for c in cs if c['cat'] == cat and 'insc_vaga' in c]
        if r:
            out.append([cat, len(r), round(float(np.median(r)), 1), round(100 * sum(x < 2 for x in r) / len(r), 1)])
    salvar_csv('06_disputa_por_categoria.csv', out, ['categoria', 'cursos', 'insc_vaga_mediana_2018', 'pct_cursos_menos_de_2_insc_vaga'])
    fed = [c for c in cs if c['cat'] == FED and 'insc_vaga' in c]
    base = [c for c in cs if c['cat'] == BASE]
    areas_fed = set(c['area'] for c in fed)
    base = [c for c in base if c['area'] in areas_fed]
    # tercis de concorrência dentro da área
    g = collections.defaultdict(list)
    for c in fed:
        g[c['area']].append(c)
    for vs in g.values():
        vs.sort(key=lambda c: c['insc_vaga'])
        n = len(vs)
        for i, c in enumerate(vs):
            c['tercil'] = min(2, int(3 * i / n)) if n >= 3 else None
    out = []
    for t, nome in [(0, 'Menor concorrência'), (1, 'Concorrência média'), (2, 'Maior concorrência'), (None, 'Todas as federais')]:
        grupo = [c for c in fed if (t is None or c.get('tercil') == t)]
        dn, di = dif(grupo, base); icn, ici = ic(grupo, base)
        out.append([nome, len(grupo), round(float(np.median([c['insc_vaga'] for c in grupo])), 1), round(float(np.median([c['ocup'] for c in grupo])) * 100, 0),
                    round(dn, 1), *icn, round(di, 2), *ici, round(100 * (1 - di / dn), 0) if dn > 0 else None])
    salvar_csv('06_por_concorrencia.csv', out, ['grupo', 'cursos', 'insc_vaga_mediana_2018', 'ocupacao_mediana_pct', 'dif_nota_bruta', 'ic_inf', 'ic_sup', 'dif_idd', 'ic_inf', 'ic_sup', 'pct_da_diferenca_que_vem_da_entrada'])
    out = []
    for nome, sel in [('Vagas sobrando (ocupação < 90%)', lambda c: c['ocup'] < 0.9), ('Vagas preenchidas (ocupação >= 90%)', lambda c: c['ocup'] >= 0.9),
                      ('Menos de 2 inscritos por vaga', lambda c: c['insc_vaga'] < 2)]:
        grupo = [c for c in fed if sel(c)]
        dn, di = dif(grupo, base); icn, ici = ic(grupo, base)
        out.append([nome, len(grupo), round(dn, 1), *icn, round(di, 2), *ici])
    salvar_csv('06_por_ocupacao.csv', out, ['grupo', 'cursos', 'dif_nota_bruta', 'ic_inf', 'ic_sup', 'dif_idd', 'ic_inf', 'ic_sup'])
    out = []
    for a, vs in sorted(g.items()):
        baixa = [c for c in vs if c.get('tercil') == 0]; ba = [c for c in base if c['area'] == a]
        if len(baixa) >= 5 and len(ba) >= 5:
            dn = media(baixa, 'nt_d', 'wn') - media(ba, 'nt_d', 'wn'); di = media(baixa, 'idd_d', 'wi') - media(ba, 'idd_d', 'wi')
            out.append([a, len(baixa), round(float(np.median([c['insc_vaga'] for c in baixa])), 1), len(ba), round(dn, 1), round(di, 2)])
    salvar_csv('06_por_area.csv', out, ['area', 'cursos_federais_menor_concorrencia', 'insc_vaga_mediana', 'cursos_privados_fins_lucrativos', 'dif_nota_bruta', 'dif_idd'])
    print('06 ok', len(fed), len(base))


if __name__ == '__main__':
    main()
