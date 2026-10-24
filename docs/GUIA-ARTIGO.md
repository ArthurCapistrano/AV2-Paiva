# Guia para o artigo

Este documento orienta o consumo dos resultados da campanha V3. A V3 é a única
fonte de metodologia, números e evidências para o artigo.

## Ordem de leitura

1. `../README.md`: ambiente, comandos e localização dos artefatos.
2. `RESULTADOS-V3.md`: resultados, Grad-CAM e interpretação.
3. `VALIDACAO-METODOLOGIA.md`: pergunta, protocolo e limites.
4. `INDICE-EVIDENCIAS.md`: inventário dos materiais publicados.
5. `GUIA-ENTENDIMENTO-PROJETO.md`: vocabulário e fluxo do projeto.
6. `../protocol.json`: parâmetros fixos do treinamento.

Os registros históricos estão em `HISTORICO-V1/` e `HISTORICO-V2/`. Eles servem
para proveniência e não devem substituir a análise da V3.

## Consultar os resultados

Os materiais já estão publicados no repositório. Para consultar as métricas sem
treinar novamente:

```bash
uv sync --locked
uv run experimento-feijao analyze --results artifacts/v3
```

O resumo consolidado está em `artifacts/v3/summary.json`. Os resultados por
seed estão em `artifacts/v3/results/` e os diagnósticos visuais em
`artifacts/v3/gradcam/`.

## Síntese da V3

A solução principal obteve F1 macro médio `0.8375` e acurácia média `0.8378`. A
solução contrafactual obteve F1 macro médio `0.5880` e acurácia média `0.5880`.
O teste t pareado da diferença de F1 macro apresentou valor-p
`8.6521e-26`.

A conclusão deve permanecer limitada ao protocolo V3. O resultado não demonstra
que pesos ImageNet sempre superam qualquer inicialização aleatória, nem que a
MobileNetV2 é superior a outras arquiteturas.

## Pontos metodológicos

- A comparação é entre inicialização ImageNet e inicialização aleatória.
- O treinamento é fim a fim desde a primeira época.
- O teste t é pareado por seed.
- As 30 execuções reutilizam o mesmo split de teste de 128 imagens.
- A BatchNorm usa `momentum=0.9` e calibração com dados de treino antes da validação.
- Grad-CAM é evidência visual complementar, não uma explicação causal.
