# Índice de evidências

## V3: referência principal

```text
artifacts/v3/manifest.json  configuração e proveniência
artifacts/v3/results/       resultados, previsões e históricos
artifacts/v3/gradcam/       60 diagnósticos e 180 painéis
artifacts/v3/summary.json   resumo estatístico
```

Os resultados JSON, o resumo, o manifesto e os diagnósticos Grad-CAM são
publicados para consulta do artigo. Os checkpoints não são versionados por
causa do tamanho; seus hashes permanecem nos resultados detalhados.

## Histórico

```text
artifacts/v1/results/        resultados da V1
artifacts/v1/summary.json    resumo da V1
artifacts/v2/results/        resultados históricos da V2
artifacts/v2/summary.json    resumo histórico da V2
```

A documentação correspondente está em `docs/HISTORICO-V1/` e
`docs/HISTORICO-V2/`. Esses materiais preservam a proveniência, mas não são
usados na metodologia nem na conclusão da V3.

## Operação

Para consultar a V3 sem treinar novamente:

```bash
uv sync --locked
uv run experimento-feijao analyze --results artifacts/v3
```

Para executar uma campanha nova, escolha uma pasta própria e siga o fluxo:

```text
prepare -> experiment -> gradcam -> analyze
```
