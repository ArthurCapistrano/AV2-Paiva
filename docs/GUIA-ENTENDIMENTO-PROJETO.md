# Guia de entendimento do projeto

## Referência

A V3 é a campanha oficial do projeto. Ela compara duas inicializações da mesma
MobileNetV2 e publica todos os resultados em `artifacts/v3/`.

## Pergunta

O projeto avalia se começar a MobileNetV2 com pesos aprendidos no ImageNet altera
o desempenho da classificação de doenças em folhas de feijão quando comparado a
começar com pesos aleatórios.

## Vocabulário

### Solução principal

Ramo cuja base MobileNetV2 começa com pesos ImageNet.

### Solução contrafactual

Ramo cuja base MobileNetV2 começa com pesos aleatórios.

### Par experimental

Dupla de treinamentos associada a uma seed: um treinamento de cada solução sob
as mesmas condições.

### Entrada segmentada

Imagem em que o fundo foi substituído por cinza, preservando a folha e suas
regiões internas.

## Fluxo

```text
protocol.json
      |
      v
   prepare
      |
      v
artifacts/v1/segmented/
      |
      v
  experiment
      |
      v
artifacts/campaigns/campaign-nova/
      |
      +--> gradcam
      |
      +--> analyze
```

Os artefatos publicados da campanha oficial ficam em:

```text
artifacts/v3/manifest.json
artifacts/v3/summary.json
artifacts/v3/results/
artifacts/v3/gradcam/
```

## Protocolo

O dataset é `beans:0.1.0`, com 1.034 imagens de treino, 133 de validação e 128
de teste. A entrada tem resolução `160 x 160`. A MobileNetV2 usa `alpha=1.0`,
sem a cabeça original de mil classes, e recebe uma cabeça para as três classes
do dataset.

Cada seed gera dois treinamentos de 100 épocas com batch size 32, learning rate
`0.0001`, L2 `0.0001` e dropout `0.2`.

As camadas BatchNorm usam `momentum=0.9`. Depois de cada época, suas estatísticas
móveis são recalibradas com entradas de treino antes da validação. Essa
calibração não atualiza pesos por gradiente nem usa validação ou teste.

## Evidências

Cada resultado de ramo contém a avaliação final, métricas por classe, matriz de
confusão, previsões, probabilidades, histórico, melhor época e o SHA-256 do
checkpoint local. O caminho completo do checkpoint existe somente nas campanhas
locais; o Grad-CAM publicado possui três exemplos fixos por ramo e por seed.

Para consultar sem executar novos treinamentos:

```bash
uv sync --locked
uv run experimento-feijao analyze --results artifacts/v3
```

V1 e V2 permanecem disponíveis como histórico em `docs/HISTORICO-V1/`,
`docs/HISTORICO-V2/` e nos seus artefatos correspondentes.
