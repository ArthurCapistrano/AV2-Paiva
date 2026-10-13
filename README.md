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

Depois de congelar o protocolo, gere o manifesto normalizado do ambiente com:

```bash
uv run experimento-feijao validate \
  --config protocol.json \
  --manifest artifacts/protocol-manifest.json
```

As demais operacoes aparecem na ajuda como etapas futuras e permanecem na mesma
CLI.
