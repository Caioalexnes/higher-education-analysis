"""Current cost per student of the 69 federal universities (2024) and its relation with the 2023 IDD.

Cost: current expenditure executed (economic category 3) by each university's budget unit in the
Portal da Transparencia (Orcamento da Despesa 2024), excluding functions 09 (social security:
retirement and pensions) and 28 (special charges). University hospitals have their own budget
units and are excluded, as is capital spending.
Denominator: in-person undergraduate enrollments (2024 Higher Education Census).
Value added: 2023 raw IDD of each course minus the area mean, weighted by graduates with an Enem score.

Outputs: 03_custo_federais.csv, 03_validacao_tcu.csv, 03_tercis.csv, 03_correlacao.csv
"""
import csv, io, zipfile, collections, math
import numpy as np
from config import arq, salvar_csv, RES

UO = {'26230':'UNIVASF','26231':'UFAL','26232':'UFBA','26233':'UFC','26234':'UFES','26235':'UFG','26236':'UFF','26237':'UFJF','26238':'UFMG','26239':'UFPA','26240':'UFPB','26241':'UFPR','26242':'UFPE','26243':'UFRN','26244':'UFRGS','26245':'UFRJ','26246':'UFSC','26247':'UFSM','26248':'UFRPE','26249':'UFRRJ','26250':'UFRR','26251':'UFT','26252':'UFCG','26253':'UFRA','26254':'UFTM','26255':'UFVJM','26258':'UTFPR','26260':'UNIFAL-MG','26261':'UNIFEI','26262':'UNIFESP','26263':'UFLA','26264':'UFERSA','26266':'UNIPAMPA','26267':'UNILA','26268':'UNIR','26269':'UNIRIO','26270':'UFAM','26271':'UNB','26272':'UFMA','26273':'FURG','26274':'UFU','26275':'UFAC','26276':'UFMT','26277':'UFOP','26278':'UFPEL','26279':'UFPI','26280':'UFSCAR','26281':'UFS','26282':'UFV','26283':'UFMS','26284':'UFCSPA','26285':'UFSJ','26286':'UNIFAP','26350':'UFGD','26351':'UFRB','26352':'UFABC','26440':'UFFS','26441':'UFOPA','26442':'UNILAB','26447':'UFOB','26448':'UNIFESSPA','26449':'UFCA','26450':'UFSB','26452':'UFCAT','26453':'UFJ','26454':'UFR','26455':'UFDPAR','26456':'UFAPE','26457':'UFNT'}
# Custo corrente sem HU publicado pelas universidades (indicadores do TCU, 2024), R$ milhões
TCU = {'UNB': 1272.9, 'UFPA': 1126.0, 'UFMA': 803.5, 'UFMS': 804.2, 'UFAC': 292.7, 'UFR': 131.8, 'FURG': 511.5}
EXCLUIR = {'UNIVASF'}  # matrícula inconsistente no Censo 2024 (2.128 alunos)


def valor(x):
    return float(x.replace('.', '').replace(',', '.')) if x else 0.0


def custos():
    z = zipfile.ZipFile(arq('orcamento2024'))
    f = io.TextIOWrapper(z.open(z.namelist()[0]), encoding='latin-1', newline='')
    c = collections.defaultdict(collections.Counter)
    for row in csv.DictReader(f, delimiter=';'):
        s = UO.get(row['CÓDIGO UNIDADE ORÇAMENTÁRIA'])
        if not s:
            continue
        v = valor(row['ORÇAMENTO REALIZADO (R$)'])
        fun, cat = row['CÓDIGO FUNÇÃO'], row['CÓDIGO CATEGORIA ECONÔMICA']
        c[s]['total'] += v
        if cat != '3':
            c[s]['capital'] += v
        elif fun == '09':
            c[s]['previdencia'] += v
        elif fun == '28':
            c[s]['encargos_especiais'] += v
        else:
            c[s]['corrente'] += v
            if row['CÓDIGO AÇÃO'] == '09HB':
                c[s]['contrib_patronal'] += v
    return c


def matriculas():
    z = zipfile.ZipFile(arq('censo2024'))
    ies = [n for n in z.namelist() if n.endswith('MICRODADOS_ED_SUP_IES_2024.CSV')][0]
    cur = [n for n in z.namelist() if n.endswith('MICRODADOS_CADASTRO_CURSOS_2024.CSV')][0]
    sig = {}
    for r in csv.DictReader(io.TextIOWrapper(z.open(ies), encoding='latin-1', newline=''), delimiter=';'):
        if r['TP_CATEGORIA_ADMINISTRATIVA'] == '1' and r['TP_ORGANIZACAO_ACADEMICA'] == '1':
            sig[r['SG_IES']] = r['CO_IES']
    cos = set(sig.values())
    mat, pres = collections.Counter(), collections.Counter()
    rr = csv.reader(io.TextIOWrapper(z.open(cur), encoding='latin-1', newline=''), delimiter=';')
    h = next(rr); ix = {k: i for i, k in enumerate(h)}
    for row in rr:
        co = row[ix['CO_IES']]
        if co in cos:
            m = int(row[ix['QT_MAT']] or 0)
            mat[co] += m
            if row[ix['TP_MODALIDADE_ENSINO']] == '1':
                pres[co] += m
    return sig, mat, pres


def idd_por_ies():
    rows = []
    with open(f'{RES}/02_cursos_2023.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter=';'):
            try:
                rows.append(dict(area=r['area'], ies=r['ies'], w=float(r['participantes_com_enem']), idd=float(r['idd_bruto']), nt=float(r['nota_bruta'])))
            except (ValueError, TypeError):
                pass
    rows = [r for r in rows if r['w'] > 0]
    g = collections.defaultdict(list)
    for r in rows:
        g[r['area']].append(r)
    for vs in g.values():
        mi, mn = np.mean([r['idd'] for r in vs]), np.mean([r['nt'] for r in vs])
        for r in vs:
            r['idd_d'], r['nt_d'] = r['idd'] - mi, r['nt'] - mn
    by = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    for r in rows:
        b = by[r['ies']]; b[0] += r['w']; b[1] += r['w'] * r['idd_d']; b[2] += r['w'] * r['nt_d']; b[3] += 1
    return by


def main():
    c = custos(); sig, mat, pres = matriculas(); by = idd_por_ies()
    out, val, dados = [], [], []
    for s in sorted(c):
        co = sig[s]; x = c[s]
        b = by.get(co, [0, 0, 0, 0])
        cpp = x['corrente'] / pres[co] if pres[co] else None
        iddm = b[1] / b[0] if b[0] else None
        ntm = b[2] / b[0] if b[0] else None
        out.append([s, co, round(x['total']), round(x['corrente']), round(x['previdencia']), round(x['contrib_patronal']), round(x['capital']),
                    mat[co], pres[co], round(cpp) if cpp else None, b[3], int(b[0]), round(iddm, 2) if iddm is not None else None, round(ntm, 2) if ntm is not None else None])
        if s in TCU:
            val.append([s, round(x['corrente'] / 1e6, 1), TCU[s], round(x['corrente'] / 1e6 / TCU[s] - 1, 3)])
        if s not in EXCLUIR and cpp and b[0] >= 30:
            dados.append((s, cpp / 1000, iddm, ntm))
    salvar_csv('03_custo_federais.csv', out, ['sigla', 'co_ies', 'despesa_total', 'custo_corrente', 'previdencia', 'contrib_patronal_09HB', 'capital',
                                             'matriculas', 'matriculas_presenciais', 'custo_por_aluno_presencial', 'cursos_com_idd', 'formandos_com_enem', 'idd_bruto_medio_rel_area', 'nota_bruta_media_rel_area'])
    salvar_csv('03_validacao_tcu.csv', val, ['sigla', 'custo_corrente_portal_mi', 'custo_corrente_sem_hu_tcu_mi', 'diferenca_relativa'])
    dados.sort(key=lambda t: t[1])
    k = len(dados) // 3
    terc = []
    for i, (a, b) in enumerate([(0, k), (k, 2 * k), (2 * k, len(dados))]):
        sl = dados[a:b]
        terc.append([i + 1, len(sl), round(np.mean([t[1] for t in sl]), 1), round(np.mean([t[2] for t in sl]), 2), round(np.mean([t[3] for t in sl]), 1),
                     round(float(np.std([t[2] for t in sl], ddof=1)), 3)])
    salvar_csv('03_tercis.csv', terc, ['tercil', 'universidades', 'custo_medio_mil', 'idd_medio', 'nota_bruta_media', 'idd_dp'])
    X = np.array([t[1] for t in dados]); res = []
    for nome, Y in [('idd', np.array([t[2] for t in dados])), ('nota_bruta', np.array([t[3] for t in dados]))]:
        r = float(np.corrcoef(X, Y)[0, 1]); n = len(X); t = r * math.sqrt((n - 2) / (1 - r * r))
        ra, rb = np.argsort(np.argsort(X)), np.argsort(np.argsort(Y)); rs = float(np.corrcoef(ra, rb)[0, 1])
        res.append([nome, n, round(float(np.polyfit(X, Y, 1)[0]), 3), round(r, 3), round(t, 2), round(rs, 3)])
    salvar_csv('03_correlacao.csv', res, ['variavel', 'universidades', 'inclinacao_por_mil_reais', 'pearson_r', 't', 'spearman_rho'])
    print('03 ok', len(dados))


if __name__ == '__main__':
    main()
