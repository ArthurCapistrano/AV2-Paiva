# Experimento de classificacao de folhas de feijao

Aplicacao Python 3.11 para comparar uma MobileNetV2 com inicializacao ImageNet
contra a mesma rede com inicializacao aleatoria.

## Ambiente

```bash
uv sync --frozen
uv run experimento-feijao --help
```

## Fluxo

Prepare uma colecao fixa de entradas segmentadas:

```bash
uv run experimento-feijao prepare \
  --config protocol.json \
  --output artifacts/segmented
```

Em um ambiente com um manifesto local do dataset, informe-o com
`--dataset-manifest caminho/do/manifesto.json`.

Execute os 30 pares experimentais:

```bash
uv run experimento-feijao campaign \
  --config protocol.json \
  --segmented-inputs artifacts/segmented \
  --output artifacts/results
```

Analise e apresente os resultados:

```bash
uv run experimento-feijao analyze \
  --results artifacts/results \
  --output artifacts/summary.json
```

A análise apresenta F1 macro, acurácia, médias, desvios-padrão, diferenças
pareadas, estatística do teste t pareado bilateral e valor-p.

O experimento usa as mesmas entradas e configurações nos dois braços. A única
diferença deliberada é a inicialização da base: ImageNet na solução principal e
aleatória na solução contrafactual.
