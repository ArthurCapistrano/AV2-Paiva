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
- Manter a V1 em `artifacts/results/` e `artifacts/summary.json` sem alterações.
- Salvar somente o melhor checkpoint de cada ramo e seed em armazenamento local.
- Usar `scripts/v2-run.sh` para iniciar processos destacáveis.
- Acompanhar processos com `scripts/v2-status.sh` e os logs em
  `/tmp/av2-paiva-v2/`.

### 2. Piloto

- Executar primeiro somente o `seed 1002`.
- Validar o schema, histórico, previsões, probabilidades, checkpoint, Grad-CAM
  e retomada antes da campanha completa.
- Se o piloto estiver correto, ele permanece como parte da V2 e não é repetido.
- Se houver erro na instrumentação, corrigir e repetir somente o `seed 1002`.
- Após conferir o piloto, executar `scripts/v2-approve-full.sh` para liberar a
  campanha completa.

### 3. Campanha completa

- Reexecutar os 30 seeds, incluindo o `seed 1001`.
- Retomar ramos e pares que já tenham artefatos completos.
- Gravar, por ramo e seed, métricas globais, métricas por classe, matriz de
  confusão, previsões, probabilidades, histórico por época, melhor época,
  melhor perda de validação e tempo de treinamento.

### 4. Grad-CAM

- Usar as mesmas três imagens fixas da V1 para todos os pares.
- Gerar mapas para os dois ramos de cada seed.
- Manter os painéis da V2 localmente; a publicação futura deve selecionar apenas
  exemplos necessários para o artigo.

### 5. Analise

- Consolidar os pares completos disponíveis sem treinar novamente.
- Calcular médias, desvios, diferenças pareadas, teste t e intervalo de
  confiança da diferença de F1 macro.
- Comparar o diagnóstico do `seed 1001` com os demais sem afirmar uma causa que
  os artefatos não sustentem.

### 6. Simplificacao pos-piloto

- Depois de validar o piloto, revisar os scripts e validadores antes de ampliar
  o protocolo.
- Remover controles, campos e caminhos que não tenham sido úteis para a
  auditoria ou retomada.
- Preferir uma execução menor e compreensível a uma infraestrutura genérica
  para cenários que ainda não foram observados.

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

Os checkpoints e a pasta `artifacts/v2/` são locais e não devem ser enviados ao
GitHub. A V1 permanece congelada.

## Execucao sem bloquear o terminal

O piloto será iniciado somente depois da validação da infraestrutura:

```bash
scripts/v2-run.sh experiment --seeds 1002
scripts/v2-status.sh
```

Depois do treinamento do piloto:

```bash
scripts/v2-run.sh gradcam --seeds 1002
scripts/v2-run.sh analyze
```

Depois da revisão manual do piloto:

```bash
scripts/v2-approve-full.sh
scripts/v2-run.sh experiment --full
scripts/v2-run.sh gradcam --full
scripts/v2-run.sh analyze
```

O processo retorna imediatamente ao terminal. Fechar o terminal não encerra o
processo destacável, mas o computador deve permanecer ligado e fora de
suspensão.
