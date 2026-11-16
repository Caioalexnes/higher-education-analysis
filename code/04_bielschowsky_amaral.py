"""Recomputes the cost ratios from Tables 9, 10, 11 and 12 of
Bielschowsky and Amaral (2022), Educacao & Sociedade 43, e243866.
Values in reais of January 2019. Output: 04_bielschowsky_amaral.csv
"""
from config import salvar_csv

# Tabela 9: despesa total, despesa sem aposentados (col. a), despesa com ensino; Tabela 10: alunos
T9_10 = {
    'Universidades federais': (51081694765, 38851832853, 26157038225, 1328482),
    'Universidades privadas': (22432058113, 22432058113, 21165763519, 2542501),
    'Universidades confessionais': (5228823931, 5228823931, 4219805965, 234633),
    'Centros universitários privados': (15977327035, 15977327035, 15726358562, 1883606),
    'Faculdades privadas': (16323361115, 16323361115, 16002907430, 1722929),
}
T11 = {'Universidades federais': 19766, 'Universidades privadas': 13105, 'Universidades confessionais': 18010,
       'Centros universitários privados': 12274, 'Faculdades privadas': 10933}
T12_SEM_EAD = 15839  # universidades privadas sem alunos a distância (25 IES)


def main():
    out = []
    for k, (tot, sem_apos, ensino, n) in T9_10.items():
        out.append([k, T11[k], round(ensino / n), round(sem_apos / n), round(tot / n), round(100 * (1 - ensino / sem_apos), 1)])
    salvar_csv('04_bielschowsky_amaral.csv', out, ['segmento', 'tabela11_media_simples', 'total_por_aluno_com_desconto', 'total_por_aluno_sem_desconto', 'total_por_aluno_com_aposentados', 'pct_descontado_pesquisa'])
    f, p = T9_10['Universidades federais'], T9_10['Universidades privadas']
    raz = [['média simples (artigo)', round(T11['Universidades federais'] / T11['Universidades privadas'], 2)],
           ['total ÷ total, com desconto', round((f[2] / f[3]) / (p[2] / p[3]), 2)],
           ['total ÷ total, sem desconto', round((f[1] / f[3]) / (p[1] / p[3]), 2)],
           ['total ÷ total, com aposentados', round((f[0] / f[3]) / (p[1] / p[3]), 2)],
           ['média simples, privadas sem EaD', round(T11['Universidades federais'] / T12_SEM_EAD, 2)]]
    salvar_csv('04_razoes.csv', raz, ['medida', 'federal_sobre_privada'])
    print('04 ok')


if __name__ == '__main__':
    main()
