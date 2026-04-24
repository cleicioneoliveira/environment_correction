# Environment Correction Utility

Utilitário para corrigir variáveis ambientais do arquivo de monitoramento usando o `heat_stress_report` como fonte de verdade.

O objetivo é substituir, de forma auditável e reproduzível, apenas as variáveis ambientais do monitoramento:

- `temperatura_compost_1`
- `humidade_compost_1`
- `thi_compost1`
- `temperatura_compost_2`
- `humidade_compost_2`
- `thi_compost2`

Todas as demais colunas do monitoramento são preservadas exatamente na mesma estrutura e ordem do arquivo original.

---

## 1. Problema resolvido

Em alguns arquivos de monitoramento, as variáveis ambientais podem estar truncadas, arredondadas, desalinhadas ou menos confiáveis. O arquivo `heat_stress_report` contém medições ambientais por dispositivo em resolução sub-horária, normalmente a cada poucos minutos.

Este utilitário:

1. lê o `heat_stress_report`;
2. agrega temperatura e umidade por hora e por dispositivo;
3. compara cada dispositivo com os campos ambientais existentes no monitoramento;
4. testa diferentes lags horários;
5. escolhe automaticamente o dispositivo e o lag mais compatíveis com `compost_1` e `compost_2`;
6. recalcula o THI a partir da temperatura e umidade corrigidas;
7. substitui somente as seis colunas ambientais finais;
8. gera arquivos de auditoria, qualidade, cobertura, inconsistências e resumo JSON.

---

## 2. Estrutura do pacote

```text
environment_correction/
├── corrigir_ambiente_monitoramento.py      # wrapper compatível com o script antigo
├── README.md                               # documentação completa
├── requirements.txt                        # dependências mínimas
├── pyproject.toml                          # configuração opcional de pacote
└── environment_correction/
    ├── __init__.py
    ├── __main__.py                         # permite python -m environment_correction
    ├── alignment.py                        # inferência de dispositivo e lag
    ├── cli.py                              # interface de linha de comando
    ├── columns.py                          # nomes de colunas e validações
    ├── config.py                           # configuração centralizada
    ├── correction.py                       # aplicação da correção
    ├── io.py                               # leitura, escrita e validações de I/O
    ├── logging_utils.py                    # logging
    ├── metrics.py                          # correlação, MAE, score, match rate
    ├── pipeline.py                         # orquestração principal
    ├── preprocessing.py                    # agregação horária e auditoria inicial
    ├── quality.py                          # qualidade, cobertura e resumo
    └── thi.py                              # cálculo do THI
```

---

## 3. Instalação simples

Entre no diretório do utilitário:

```bash
cd environment_correction
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Ou, se quiser instalar como pacote editável:

```bash
pip install -e .
```

---

## 4. Uso básico

### Opção A — usando o wrapper compatível com o nome antigo

```bash
python corrigir_ambiente_monitoramento.py \
  --heat /media/extra/wrk/CONFORTO/dataset/raw/heat_stress_report_f1293.csv \
  --monitoramento /media/extra/wrk/CONFORTO/dataset/processed/monitoramento_1293_full.csv \
  --output-dir /media/extra/wrk/CONFORTO/dataset/processed
```

### Opção B — usando o pacote como módulo

```bash
python -m environment_correction \
  --heat /media/extra/wrk/CONFORTO/dataset/raw/heat_stress_report_f1293.csv \
  --monitoramento /media/extra/wrk/CONFORTO/dataset/processed/monitoramento_1293_full.csv \
  --output-dir /media/extra/wrk/CONFORTO/dataset/processed
```

---

## 5. Saídas geradas

Por padrão, os arquivos são salvos no diretório informado em `--output-dir`. Se `--output-dir` não for informado, será criado um diretório `processado` ao lado do arquivo de monitoramento.

| Arquivo | Função |
|---|---|
| `monitoramento_full_corrigido.csv` | Arquivo final corrigido, com a mesma estrutura do monitoramento original |
| `device_lag_audit.csv` | Todos os candidatos testados: compost, dispositivo, lag, correlação, MAE e score |
| `device_pair_candidates.csv` | Pares candidatos para compost_1 e compost_2 |
| `quality_summary.csv` | Métricas do mapeamento escolhido |
| `environment_inconsistencies.csv` | Inconsistências ambientais no monitoramento antes da correção |
| `correction_coverage.csv` | Cobertura da correção por compost |
| `correction_summary.json` | Resumo completo da execução em JSON |

---

## 6. Como o mapeamento é escolhido

Para cada lag horário no intervalo configurado, o utilitário desloca os horários do `heat_stress_report` e compara os dispositivos com os campos ambientais existentes no monitoramento.

Por padrão, o intervalo testado é de `-6` a `+6` horas.

Para cada combinação de:

```text
compost × dispositivo × lag
```

são calculados:

- correlação da temperatura;
- correlação da umidade;
- erro absoluto médio da temperatura;
- erro absoluto médio da umidade;
- número de horas sobrepostas;
- score final.

A fórmula do score é:

```text
score = ((corr_temp + corr_hum) / 2) - 0.01 * (mae_temp + mae_hum)
```

Ou seja, o score favorece candidatos com alta correlação e penaliza candidatos com erro absoluto maior.

---

## 7. Interpretação do lag

Um lag positivo significa que o timestamp do `heat_stress_report` é movido para frente antes da comparação.

Exemplo:

```text
heat 10:00 com lag +3h → comparado como 13:00
```

Um lag negativo significa que o timestamp do `heat_stress_report` é movido para trás.

Exemplo:

```text
heat 10:00 com lag -3h → comparado como 07:00
```

Importante: o lag inferido deve ser interpretado como correção operacional de alinhamento temporal. Ele pode representar diferença de fuso, atraso de sincronização, defasagem de exportação, arredondamento temporal ou outro desalinhamento entre sistemas. Ele não deve ser interpretado automaticamente como atraso físico do sensor.

---

## 8. Opções importantes de execução

### Definir intervalo de lag

```bash
--lag-min -6 --lag-max 6
```

### Exigir mínimo de horas sobrepostas

```bash
--min-overlap-hours 72
```

Esse parâmetro evita aceitar candidatos baseados em poucas horas de coincidência.

### Forçar lag compartilhado entre composts

```bash
--lag-mode shared
```

Use quando você acredita que o problema seja sistemático no arquivo inteiro, como diferença de fuso horário ou deslocamento global dos timestamps.

### Permitir lag independente

```bash
--lag-mode independent
```

Esse é o padrão. Permite que compost_1 e compost_2 tenham lags diferentes.

### Controlar unidade da umidade

```bash
--humidity-unit auto
--humidity-unit pct
--humidity-unit fraction
```

- `auto`: tenta detectar se a umidade está em fração `[0,1]` ou porcentagem `[0,100]`;
- `pct`: assume porcentagem;
- `fraction`: assume fração e converte para porcentagem.

### Escolher método de agregação horária

```bash
--aggregation mean
--aggregation median
```

Use `median` se houver suspeita de outliers nos dados sub-horários.

### Detectar mapeamento incerto

```bash
--min-score-margin 0.05
```

Esse parâmetro define a margem mínima desejável entre o melhor e o segundo melhor candidato.

### Interromper em caso de baixa qualidade

```bash
--fail-on-low-quality
```

Com essa opção, o pipeline para se o mapeamento escolhido tiver margem de score baixa.

---

## 9. Exemplo recomendado para uso científico

```bash
python -m environment_correction \
  --heat /media/extra/wrk/CONFORTO/dataset/raw/heat_stress_report_f1293.csv \
  --monitoramento /media/extra/wrk/CONFORTO/dataset/processed/monitoramento_1293_full.csv \
  --output-dir /media/extra/wrk/CONFORTO/dataset/processed/correcao_ambiental \
  --lag-min -6 \
  --lag-max 6 \
  --min-overlap-hours 72 \
  --lag-mode shared \
  --humidity-unit auto \
  --aggregation mean \
  --min-score-margin 0.05 \
  --log-level INFO
```

Esse comando é mais conservador porque exige pelo menos 72 horas sobrepostas e força um lag compartilhado entre os dois composts.

---

## 10. Como auditar o resultado

Após executar, revise principalmente estes arquivos:

### `device_lag_audit.csv`

Verifique os melhores candidatos por compost:

```python
import pandas as pd

audit = pd.read_csv("device_lag_audit.csv")
print(audit.sort_values(["compost", "score"], ascending=[True, False]).groupby("compost").head(10))
```

### `device_pair_candidates.csv`

Verifique se o par escolhido tem vantagem clara sobre os demais:

```python
pairs = pd.read_csv("device_pair_candidates.csv")
print(pairs.head(10))
```

### `quality_summary.csv`

Verifique correlação, MAE e taxa de coincidência após arredondamento:

```python
quality = pd.read_csv("quality_summary.csv")
print(quality)
```

### `correction_coverage.csv`

Verifique quantas linhas foram efetivamente corrigidas:

```python
coverage = pd.read_csv("correction_coverage.csv")
print(coverage)
```

### `environment_inconsistencies.csv`

Se esse arquivo tiver linhas, significa que havia mais de um valor ambiental distinto para o mesmo horário no monitoramento. Isso não impede a correção, mas deve ser revisado.

---

## 11. Cuidados metodológicos

### Correlação alta não prova identidade física

Dois sensores no mesmo ambiente podem apresentar correlação alta por seguirem o mesmo ciclo diário. Por isso o utilitário também calcula MAE, score, margem de score e relatórios de auditoria.

### O mapeamento automático precisa ser conferido

O utilitário escolhe automaticamente o melhor par, mas o resultado deve ser conferido quando:

- a margem entre primeiro e segundo candidato for pequena;
- compost_1 e compost_2 tiverem sensores muito parecidos;
- a cobertura da correção for baixa;
- houver muitas inconsistências ambientais no monitoramento;
- o lag escolhido for inesperado.

### O THI é recalculado

O THI final é recalculado a partir da temperatura e umidade corrigidas. Portanto, mesmo que o THI original do monitoramento esteja truncado ou inconsistente, o novo THI será derivado diretamente da fonte ambiental corrigida.

---

## 12. Fluxo interno do pipeline

```text
CLI
 ↓
AppConfig
 ↓
load_inputs()
 ↓
normalize_humidity()
 ↓
build_hourly_environment()
 ↓
infer_mapping()
 ↓
build_corrected_environment()
 ↓
apply_correction()
 ↓
build_quality_summary()
 ↓
build_coverage_summary()
 ↓
build_summary()
 ↓
save_outputs()
```

---

## 13. API Python

Também é possível usar o utilitário diretamente em Python:

```python
from pathlib import Path

from environment_correction import AppConfig, run

config = AppConfig(
    heat_path=Path("heat_stress_report_f1293.csv"),
    monitoramento_path=Path("monitoramento_1293_full.csv"),
    output_monitoramento=Path("processado/monitoramento_full_corrigido.csv"),
    output_audit=Path("processado/device_lag_audit.csv"),
    output_pair_candidates=Path("processado/device_pair_candidates.csv"),
    output_summary=Path("processado/correction_summary.json"),
    output_quality=Path("processado/quality_summary.csv"),
    output_inconsistencies=Path("processado/environment_inconsistencies.csv"),
    output_coverage=Path("processado/correction_coverage.csv"),
    log_level="INFO",
    lag_min=-6,
    lag_max=6,
    min_overlap_hours=72,
    lag_mode="shared",
    humidity_unit="auto",
    aggregation="mean",
    min_score_margin=0.05,
    fail_on_low_quality=False,
)

summary = run(config)
print(summary)
```

---

## 14. Dependências

Dependências mínimas:

```text
pandas
```

Para uso normal com CSV, isso é suficiente.

---

## 15. Versão

Versão modular: `2.0.0`.

Principais melhorias em relação ao script original:

- separação em módulos;
- validação segura de correlação;
- rejeição de candidatos com baixa sobreposição temporal;
- suporte a lag compartilhado ou independente;
- validação/conversão de umidade em porcentagem;
- auditoria de inconsistências ambientais por horário;
- relatório de cobertura da correção;
- relatório de margem de score;
- opção de falhar em baixa qualidade;
- documentação completa;
- compatibilidade com o nome antigo do script.
