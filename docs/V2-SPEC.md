# Especificacao da V2

## Objetivo

Reexecutar o protocolo da V1 com telemetria suficiente para auditar o
comportamento dos dois ramos, especialmente o colapso observado na solucao
contrafactual. A V2 nao altera o protocolo de treinamento na primeira rodada.

## Etapas

### 1. Infraestrutura

- Usar `protocol.json` sem alterar arquitetura, hiperparametros, dataset ou
  seeds.
- Escrever todos os artefatos em `artifacts/v2/`.
- Manter a V1 em `artifacts/v1/results/` e `artifacts/v1/summary.json` sem alterações.
- Salvar somente o melhor checkpoint de cada ramo e seed em armazenamento local.
- Usar a CLI `experimento-feijao` para iniciar as etapas da V2.
- Se a execução precisar continuar após o fechamento do terminal, usar o
  mecanismo de sessão do ambiente (por exemplo, `tmux`); isso não faz parte do
  protocolo experimental.

### 2. Piloto

- Executar primeiro somente o `seed 1002`.
- Validar o schema, histórico, previsões, probabilidades, checkpoint, Grad-CAM
  e retomada antes da campanha completa.
- Se o piloto estiver correto, ele permanece como parte da V2 e não é repetido.
- Se houver erro na instrumentação, corrigir e repetir somente o `seed 1002`.
- Após conferir o piloto, definir `V2_PILOT_APPROVED=1` para liberar a campanha
  completa.

### 3. Campanha completa

- Reexecutar os 30 seeds, incluindo o `seed 1001`.
- Retomar ramos e pares que já tenham artefatos completos.
- Gravar, por ramo e seed, métricas globais, métricas por classe, matriz de
  confusão, previsões, probabilidades, histórico por época, melhor época,
  melhor perda de validação e tempo de treinamento.

### 4. Grad-CAM

- Usar as mesmas três imagens fixas da V1 para todos os pares.
- Gerar mapas para os dois ramos de cada seed.
- Versionar os diagnósticos e painéis compactos da V2; os checkpoints continuam
  restritos ao armazenamento local.

### 5. Analise

- Consolidar os pares completos disponíveis sem treinar novamente.
- Calcular médias, desvios, diferenças pareadas, teste t e intervalo de
  confiança da diferença de F1 macro.
- Comparar o diagnóstico do `seed 1001` com os demais sem afirmar uma causa que
  os artefatos não sustentem.

### 6. Simplificacao pos-piloto

- Depois de validar o piloto, revisar a implementação e os validadores antes de ampliar
  o protocolo.
- Remover controles, campos e caminhos que não tenham sido úteis para a
  auditoria ou retomada.
- Preferir uma execução menor e compreensível a uma infraestrutura genérica
  para cenários que ainda não foram observados.

## Estado final

- Os 30 pares, dos seeds `1001` a `1030`, foram concluídos.
- Todos os resultados possuem telemetria, previsões, probabilidades e
  checkpoints locais.
- O Grad-CAM foi concluído para os 30 pares, com três imagens por ramo.
- A análise estatística foi consolidada em `artifacts/v2/summary.json`.
- A interpretação final está em `RESULTADOS-V2.md`.
- A V1 permanece congelada em `artifacts/v1/results/` e `artifacts/v1/summary.json`.
- Os resultados, o resumo e os diagnósticos Grad-CAM da V2 podem ser
  versionados; os checkpoints permanecem locais e não devem ser versionados.

## Formato local

```text
artifacts/v2/
  results/pair-SEED/solucao_principal/result.json
  results/pair-SEED/solucao_contrafactual/result.json
  results/pair-SEED/result.json
  checkpoints/pair-SEED/*.weights.h5
  gradcam/pair-SEED/<ramo>/<classe>.png
  summary.json
```

Os checkpoints em `artifacts/v2/checkpoints/` são locais e não devem ser
enviados ao GitHub. Os resultados, o resumo e os diagnósticos Grad-CAM são
artefatos compactos de auditoria e podem ser publicados. A V1 permanece
congelada.

## Execucao por etapas

O piloto será iniciado somente depois da validação da infraestrutura:

```bash
uv run experimento-feijao v2-experiment \
  --config protocol.json \
  --segmented-inputs artifacts/v1/segmented \
  --output artifacts/v2 \
  --seeds 1002
```

Depois do treinamento do piloto:

```bash
uv run experimento-feijao v2-gradcam \
  --config protocol.json \
  --segmented-inputs artifacts/v1/segmented \
  --output artifacts/v2 \
  --seeds 1002
uv run experimento-feijao v2-analyze \
  --results artifacts/v2 \
  --output artifacts/v2/summary.json
```

Depois da revisão manual do piloto:

```bash
V2_PILOT_APPROVED=1 uv run experimento-feijao v2-experiment \
  --config protocol.json \
  --segmented-inputs artifacts/v1/segmented \
  --output artifacts/v2 \
  --seeds all
uv run experimento-feijao v2-gradcam \
  --config protocol.json \
  --segmented-inputs artifacts/v1/segmented \
  --output artifacts/v2 \
  --seeds all
uv run experimento-feijao v2-analyze \
  --results artifacts/v2 \
  --output artifacts/v2/summary.json
```

Cada comando permanece no terminal até concluir. Para uma execução longa,
inicie a sessão dentro de `tmux` ou outro mecanismo equivalente; isso não
altera os artefatos nem o protocolo experimental.

Os comandos acima foram executados com sucesso. Os achados e a interpretacao
final estao registrados em `RESULTADOS-V2.md`.
