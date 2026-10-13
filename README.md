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

Enquanto os pilotos nao tiverem sido executados, use `state: "pending"` e nao
informe valores HSV ou epocas como determinados. A validacao recusara essa
configuracao ate que os valores e suas evidencias sejam registrados.

O piloto de epocas permanece planejado. Antes de observar suas curvas, fica
definida a seguinte regra de estabilizacao para cada braco: dividir a curva de
`validation_loss` em janelas consecutivas de cinco epocas e comparar o menor
valor da janela atual com o da anterior. A curva estabiliza no fim da segunda
comparacao consecutiva cuja melhora relativa seja de no maximo 1%. O orcamento
comum sera a maior epoca de estabilizacao entre os dois bracos. Se algum braco
nao estabilizar dentro do horizonte piloto, o piloto devera ser estendido sem
consultar o teste.

Depois da execucao real, `training.pilot_evidence` deve apontar, relativamente ao
arquivo de configuracao, para um JSON com `status: "executed"`,
`dataset_splits: ["train", "validation"]`, `test_data_accessed: false`, o
`selected_epochs`, as `pilot_seeds`, a `training_configuration`, a regra
pre-declarada e um `curve_summary` para `solucao_principal` e
`solucao_contrafactual`. Cada resumo registra `epochs_observed`,
`stabilized_at_epoch`, `window_minimum_validation_loss` e os valores inicial,
minimo e final de `validation_loss`. A CLI recalcula a estabilizacao pelos
minimos de cada janela e exige que o orcamento seja a estabilizacao mais tardia
dos dois bracos e igual ao valor congelado na configuracao.

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
