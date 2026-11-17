# Selection or Teaching? Value Added and Cost in Brazilian Federal Universities

Replication package for the working paper *Selection or Teaching? Value Added and Cost in Brazilian Federal Universities* by Caio A. F. Cunha (draft v0.6, November 2026). The paper is in [`paper/paper.pdf`](paper/paper.pdf).

The paper asks how much of the advantage of Brazilian federal universities in the national graduation exam (Enade) is selection and how much is teaching. It compares federal and private courses of the same assessment area using the raw Enade score and INEP's value-added indicator (IDD). It also shows that the method INEP used to compute the IDD until 2021 pulled course effects toward zero, more so in larger courses, which is why earlier editions show almost no value-added gap between federal and private courses.

All data are public. This repository contains the code, the intermediate results and the LaTeX source of the paper. The raw data must be downloaded from the official sources listed below.

## Repository structure

```
code/        Python scripts 01-19 and config.py
results/     CSV outputs of the scripts (the inputs of the paper's tables and figures)
paper/       paper.tex, refs.bib, build_tables.py, tables/, figures/, paper.pdf
```

## Requirements

- Python 3.10 or later, with `numpy`, `pandas`, `openpyxl`, `xlrd` (for the 2015 `.xls` spreadsheet) and `matplotlib`.
- To compile the paper: XeLaTeX with `fontspec` and the TeX Gyre Pagella font, `natbib` and BibTeX.

## Data

Place the files below in one folder and set the environment variable `DADOS` to that folder (default: the folder that contains this repository). Additional folders can be given in `DADOS_EXTRA`, separated by `:` on Linux and macOS or `;` on Windows.

| File | Source |
|---|---|
| `Conceito_Enade_2019.xlsx`, `IDD_2019.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/resultados/2019/ |
| `conceito_enade_2021.xlsx`, `IDD_2021.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/resultados/2021/ |
| `conceito_enade_2022.xlsx`, `idd_2022.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/resultados/2022/ |
| `conceito_enade_2023.xlsx`, `IDD_2023.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/resultados/2023/ |
| `cpc2014_atualizado_em_04122017.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/enade/planilhas/2014/cpc2014_atualizado_em_04122017.xlsx |
| `cpc_2015_portal_atualizado_03_10_2017.xls` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2017/cpc_2015_portal_atualizado_03_10_2017.xls |
| `resultado_enade2016_portal_06_09_2017.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2017/resultado_enade2016_portal_06_09_2017.xlsx |
| `resultado_IDD2016_portal_06_09_2017.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2017/resultado_IDD2016_portal_06_09_2017.xlsx |
| `resultados_conceito_enade_2017.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2018/resultados_conceito_enade_2017.xlsx |
| `resultados_IDD_2017.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2018/resultados_IDD_2017.xlsx |
| `resultados_conceito_enade_2018.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2019/resultados_conceito_enade_2018.xlsx |
| `resultados_IDD_2018.xlsx` | INEP, https://download.inep.gov.br/educacao_superior/indicadores/legislacao/2019/resultados_IDD_2018.xlsx |
| `microdados_enade_2019_LGPD.zip`, `microdados_enade_2023.zip` | INEP, https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enade |
| `microdados_censo_da_educacao_superior_2018.zip`, `microdados_censo_da_educacao_superior_2024.zip` | INEP, https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior |
| `microdados_enem_2018.zip`, `microdados_enem_2024.zip` | INEP, https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem |
| `microdados_IDD_2014.7z` to `microdados_IDD_2019.7z`, `microdados_IDD_2021.zip`, `microdados_IDD_2022.zip`, `microdados_IDD_2023.zip` | INEP, IDD microdata (student level), https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados. The 7z archives and the 2022 file (a RAR archive despite the extension) must be extracted into the data folder |
| `2024_OrcamentoDespesa.zip` | Portal da Transparência, https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/2024 |
| `br-capes-colsucup-discentes-2024-2025-12-01.csv`, `br-capes-colsucup-prog-2024-2025-12-01.csv` | CAPES open data, https://dadosabertos.capes.gov.br |
| `sinopse_educacao_superior_<ano>.zip`, 2015 to 2018 and 2024 (extracted, script 18) | INEP, https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/sinopses-estatisticas/educacao-superior-graduacao |

File names are those of the downloads. INEP occasionally republishes spreadsheets; the versions used here were downloaded in November 2026. [`DATA_SHA256SUMS.txt`](DATA_SHA256SUMS.txt) lists the SHA-256 checksum of each file, so that a new download can be checked against the version used here: run `sha256sum -c DATA_SHA256SUMS.txt` in the data folder (Linux or macOS), or compare with the output of `Get-FileHash <file>` in PowerShell (Windows).

## How to run

From `code/`, run the scripts in numerical order (each prints a short confirmation and writes its outputs to `results/`):

```
cd code
python 01_censo_origem.py
python 02_enade_idd.py
...
python 19_enem_entrada.py
```

Script 12 accepts editions as arguments (for example `python 12_serie_historica.py 2022 2023`) and merges them into the existing output; script 13 does the same, and the bootstrap intervals of script 13 are computed when the environment variable `B` is set (the paper uses `B=200`). Script 14 is superseded by script 15 and need not be run. Script 15 reads the IDD microdata of 2016 to 2023 (extracted archives or zip files anywhere under `DADOS`) and also accepts `B` for bootstrap intervals. Script 18 reads the Sinopses Estatísticas extracted in folders named `sinopse_educacao_superior_<year>`. Script 19 reads the IDD microdata of 2022 and 2023 and the Enem 2018 microdata (zip or extracted CSV).

Then build the tables and figures and compile the paper:

```
cd ../paper
python build_tables.py
xelatex paper && bibtex paper && xelatex paper && xelatex paper
```

## Scripts

| Script | What it does | Used in the paper |
|---|---|---|
| `01_censo_origem.py` | School origin (public or private secondary school) of undergraduates by category and competition, 2024 Census | No (companion essay) |
| `02_enade_idd.py` | Course-level Enade and IDD files for 2019 and 2023, grades by category, school origin from the Enade questionnaire, student-level standard deviation of the Enade score | Student standard deviation (Table 2); inputs of scripts 03, 06 and 08 |
| `03_custo_federais.py` | Current cost per in-person undergraduate of the federal universities (2024) and its relation with the 2023 IDD | Table 11, Figure 4 |
| `04_bielschowsky_amaral.py` | Recomputes the cost ratios of Bielschowsky and Amaral (2022) | No (companion essay) |
| `05_controle_pesquisa.py` | Cost and value added controlling for graduate-program intensity (CAPES) | Section 6.5 |
| `06_baixa_procura.py` | Competition for seats in 2018 (applicants per seat, seat occupancy) and gaps by competition group | No (superseded by script 10) |
| `07_cauda_direita.py` | Position of a federal university's cut-off scores in the Enem 2024 distribution | No (companion essay) |
| `08_base_regressao.py` | Course-level dataset for 2019 and 2023, with competition for seats and entering-cohort composition from the 2018 Census for 2023 | Table 1; inputs of scripts 09-11 |
| `09_regressoes.py` | Weighted regressions on administrative category with area fixed effects, clustered by institution | Tables 3, 4, 6 and 7, Figure 2 |
| `10_diferencas_pareadas.py` | Within-area gaps between federal and for-profit courses, by competition for seats, with bootstrap intervals | Table 5 |
| `11_diagnostico_2019_2023.py` | Diagnostics of the 2019 and 2023 gaps | Value-added gap by Enem coverage band in 2023 (Section 6.3) |
| `12_serie_historica.py` | Within-area gaps in every edition with course-level IDD, 2014-2023 | Tables 2 and 8 |
| `13_metodo_idd.py` | Dispersion of the IDD and federal gaps by course size, every edition | Table 9 |
| `14_reconstrucao_idd.py` | Approximate conversion of the 2014-2021 IDD to the current method from course-level data; superseded by script 15 | No |
| `15_idd_microdados.py` | Recomputes the IDD of each edition from INEP's student-level IDD microdata with both the old and the current definitions, checks them against the published values (they match exactly) and computes the federal gaps | Table 10, Figure 3 |
| `16_tempo_conclusao.py` | Years between entry and the Enade exam, federal and for-profit graduates of the same area, Enade 2019 and 2023 | No (companion essay) |
| `17_cenarios_custo.py` | Federal current cost per student (with and without university hospitals and the research discount) against median in-person private tuition (with and without taxes on revenue), per year and per graduate, 2024 | Section 7 (cost ratios) |
| `18_evasao_sinopse.py` | Annual share of severed and suspended enrolments and enrolments per graduate, in-person undergraduate courses of federal universities and private for-profit institutions, 2015-2018 and 2024 (INEP Sinopses Estatísticas, table 7.2) | No (companion essay) |
| `19_enem_entrada.py` | Position of 2022 and 2023 graduates (in-person courses) in the national distribution of Enem 2018 scores, federal and for-profit graduates of the same areas | Figure 1 and Section 6.1 |

The comparisons by category in scripts 02 and 06 subtract national means of area deviations and are superseded by the within-area comparison of script 10, which the paper uses.

**IDD method.** INEP changed the definition of the raw IDD in 2022 (Nota Técnica nº 29/2023/CEI/CGGI/DAES). The IDD of 2014 to 2021, including the 2019 files used by scripts 02, 08, 09 and 11, was computed with the earlier method, which pulls course effects toward zero as the number of graduates grows. Results based on those editions should be read with Section 6.4 of the paper. Script 15 recomputes the IDD of 2016 to 2023 with both definitions from INEP's student-level microdata; it finds the extracted microdata files anywhere under the data folder.

## Language of the code

Code comments, variable names and output columns follow INEP's Portuguese terminology. The main terms are:

| Term | Meaning |
|---|---|
| `ano` | Enade edition |
| `area` | Assessment area code |
| `categoria` | Administrative category: `Pública Federal` (federal), `Pública Estadual` (state), `Pública Municipal` (municipal), `Privada com fins lucrativos` (private for-profit), `Privada sem fins lucrativos` (private non-profit), `Comunitária/Confessional` (community/confessional), `Especial` (special) |
| `participantes` | Participating graduates |
| `participantes_com_enem` | Participating graduates with a recovered Enem score |
| `nota_bruta` | Raw Enade score, 0.25 × general education + 0.75 × area-specific component |
| `idd_bruto` | Raw IDD (value added, in Enade points) |
| `dif_nota`, `dif_idd` | Within-area gap in the raw score and in the raw IDD |
| `ic_*_inf`, `ic_*_sup` | Lower and upper limits of the 95% bootstrap interval |
| `parcela_selecao`, `parcela_entrada` | Share of the raw gap present at entry, 1 − `dif_idd`/`dif_nota` |
| `base` | Comparison group (`private for-profit` or `all private`) |
| `faixa` | Size band (graduates with an Enem score in the course) |
| `dp_idd` | Standard deviation of the raw IDD around the area mean |
| `cursos` | Number of courses |
| `inscritos_por_vaga_2018` | Applicants per new seat in the 2018 Census |
| `pct_escola_privada` | Share of graduates who attended a private secondary school |
| `modelo`, `amostra`, `dependente`, `variavel`, `coef`, `ep` | Regression model, sample, dependent variable, regressor, coefficient and standard error |

## Citation

See [`CITATION.cff`](CITATION.cff). A versioned copy will be deposited on Zenodo.

## License

Code: MIT License (see [`LICENSE`](LICENSE)). The data belong to their original publishers.
