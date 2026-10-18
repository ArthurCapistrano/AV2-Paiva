# Indice de evidencias

Este arquivo separa os documentos explicativos dos artefatos produzidos pelas
campanhas. Os resultados versionados sao pequenos o suficiente para serem
consultados diretamente no GitHub; checkpoints e entradas geradas permanecem
locais.

Para o artigo e a entrega final, a V2 e a fonte principal de evidencias. A V1
permanece como baseline historico e referencia do fluxo executavel atual.

## V2: evidencia principal do artigo

```text
artifacts/v2/results/                 Resultados, previsoes e historicos
artifacts/v2/gradcam/                 180 paineis e 60 diagnosticos
artifacts/v2/summary.json             Resumo estatistico da V2
```

Os resultados JSON, o resumo e os paineis Grad-CAM sao as evidencias publicadas
para o artigo e a entrega. Os checkpoints da V2 ficam localmente em
`artifacts/v2/checkpoints/` e nao sao versionados por causa do tamanho.

## V1: baseline historico e referencia executavel

```text
artifacts/v1/results/                 Resultados dos 30 pares
artifacts/v1/summary.json             Resumo estatistico
artifacts/v1/reports/epoch-pilot.json Piloto que fixou o orcamento de epocas
artifacts/v1/reports/gradcam/         Diagnostico visual do seed 1001
```

As entradas segmentadas da V1 ficam localmente em
`artifacts/v1/segmented/`. Elas sao geradas por `make prepare` e nao sao
versionadas.

## Operacao local

Os wrappers shell usados durante a campanha V2 permanecem somente na copia local
do repositorio e sao ignorados pelo Git. A implementacao da V2 nao faz parte do
fluxo executavel atual; os resultados publicados sao a evidencia principal do
artigo, enquanto os checkpoints locais permanecem somente para consulta.
