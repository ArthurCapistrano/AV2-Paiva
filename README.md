# Experimento de classificacao de folhas de feijao

Aplicacao Python 3.11 para executar o protocolo experimental pela unica
interface publica `experimento-feijao`.

## Ambiente

Instale o ambiente bloqueado e execute os checks com:

```bash
uv sync --frozen
uv run pytest
uv run ruff check .
uv run mypy
```

Abra a ajuda da CLI com:

```bash
uv run experimento-feijao --help
```

## Validacao do protocolo

A configuracao JSON deve registrar, no minimo:

- `dataset.version`: exatamente `beans:0.1.0`;
- `segmentation`: estado `frozen`, limites HSV inferior e superior e referencia
  para a evidencia do piloto;
- `training`: numero positivo de epocas e referencia para a evidencia do piloto;
- `seeds`: lista pre-fixada de 30 inteiros distintos;
- `checkpoint.rule`: regra comum de selecao por validacao;
- `failure.policy`: regra pre-definida para falhas do par experimental.

Antes de observar as curvas do piloto de epocas, foi definida a seguinte regra
de estabilizacao para cada braco: dividir a curva de
`validation_loss` em janelas consecutivas de cinco epocas e comparar o menor
valor da janela atual com o da anterior. A curva estabiliza no fim da segunda
comparacao consecutiva cuja melhora relativa seja de no maximo 1%. O orcamento
comum e a maior epoca de estabilizacao entre os dois bracos.

O piloto foi executado com a seed 1001 usando exclusivamente treino e validacao.
O horizonte precisou ser estendido ate 150 epocas. A solucao principal
estabilizou na epoca 100 e a contrafactual na epoca 15; portanto, o protocolo
confirmatorio em `protocol.json` congela um orcamento comum de 100 epocas. O
resumo auditavel em `reports/epoch-pilot.json` preserva seeds, configuracao,
regra, extensoes e curvas resumidas, e registra que o teste nao foi acessado. A
CLI recalcula a estabilizacao e exige que o orcamento configurado corresponda a
evidencia.

Depois de congelar o protocolo, gere o manifesto normalizado do ambiente com:

```bash
uv run experimento-feijao validate \
  --config protocol.json \
  --manifest artifacts/protocol-manifest.json
```

Depois de materializar as entradas segmentadas, execute um par cuja seed esteja
na lista congelada:

```bash
uv run experimento-feijao run \
  --config protocol.json \
  --segmented-inputs artifacts/segmented \
  --seed 1001 \
  --output artifacts/pair-1001
```

Cada braço produz checkpoint, histórico, duração restrita ao `model.fit`,
predições, métricas e manifesto. `consolidate`, `analyze` e `grad-cam` aparecem na
ajuda como etapas futuras e permanecem na mesma CLI.
