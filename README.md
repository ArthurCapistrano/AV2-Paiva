# Experimento de classificacao de folhas de feijao

Aplicacao Python 3.11 para comparar uma MobileNetV2 com inicializacao ImageNet
contra a mesma rede com inicializacao aleatoria.

## Estado atual da entrega

A V2 e a campanha que deve ser usada como base para o artigo e para a entrega
final. Ela reexecutou o protocolo da V1 com telemetria completa e publicou os
resultados, previsoes, metricas por classe, matrizes de confusao e Grad-CAM.

A V1 permanece preservada como historico e baseline. O fluxo executavel atual
usa os mesmos nomes de comandos, mas grava e analisa os artefatos no layout da
V2. As entradas segmentadas continuam compartilhadas em `artifacts/v1/`.

## Ambiente

Instale as dependencias e veja os comandos disponiveis:

```bash
uv sync --locked
make help
```

Para entender o projeto sem conhecimento previo, consulte o
[Guia de entendimento do projeto](docs/GUIA-ENTENDIMENTO-PROJETO.md).

Para iniciar o trabalho do artigo, consulte primeiro os
[resultados da V2](docs/RESULTADOS-V2.md), a
[validacao da metodologia](docs/VALIDACAO-METODOLOGIA.md) e o
[guia para o artigo](docs/GUIA-ARTIGO.md). Os documentos do
[historico V1](docs/HISTORICO-V1/) preservam o baseline e a proveniencia da
campanha original.

## Documentação

### Projeto e metodologia

- [Resultados V2: base do artigo](docs/RESULTADOS-V2.md)
- [Indice de evidencias](docs/INDICE-EVIDENCIAS.md)
- [Guia de entendimento](docs/GUIA-ENTENDIMENTO-PROJETO.md)
- [Guia para o artigo](docs/GUIA-ARTIGO.md)
- [Organização do trabalho](docs/ORGANIZACAO-TRABALHO.md)
- [Validação da metodologia](docs/VALIDACAO-METODOLOGIA.md)
- [Decisões experimentais](docs/decisoes-experimentais/INDICE.md)
- [Glossário](docs/decisoes-experimentais/GLOSSARIO.md)

### Histórico e referência executável V1

- [Entrega V1](docs/HISTORICO-V1/ENTREGA-V1.md)
- [Resultados V1](docs/HISTORICO-V1/RESULTADOS-EXPERIMENTO.md)
- [Limitação contrafactual](docs/HISTORICO-V1/LIMITACAO-COLAPSO-CONTRAFACTUAL.md)
- [Relatório Grad-CAM V1](docs/RELATORIO-GRADCAM-V1-SEED-1001.md)

## Fluxo executável atual: V2

O fluxo executável mantido no código atual e executado com:

```bash
make all
```

Ele executa, nesta ordem:

1. Prepara as imagens segmentadas compartilhadas.
2. Executa os dois modelos e registra a telemetria V2.
3. Calcula e apresenta os resultados V2.

O Grad-CAM e executado separadamente com `make gradcam`, usando os checkpoints
V2 ja existentes.

As etapas tambem podem ser executadas separadamente:

```bash
make prepare
make experiment
make analyze
```

## `protocol.json`

O arquivo define os valores fixos do experimento. Ele apenas configura a
execucao; os comandos do `Makefile` definem os caminhos de entrada e saida.

### Dataset

`dataset.version` identifica o conjunto usado. O valor esperado e
`beans:0.1.0`.

### Segmentacao

`segmentation.hsv.lower` e `segmentation.hsv.upper` definem os limites usados
para separar a folha do fundo.

`segmentation.morphology.kernel_size` define o tamanho do filtro morfologico.
`open_iterations` remove pequenos ruidos e `close_iterations` preenche pequenos
buracos na mascara.

Depois da segmentacao, o fundo recebe a cor `(127, 127, 127)` e a imagem e
redimensionada para `160 x 160`.

### Treinamento

`training.epochs` define quantas epocas cada modelo executa.

`training.batch_size` define quantas imagens sao processadas por vez.

`training.learning_rate` define a velocidade de atualizacao dos pesos.

`training.l2` define a regularizacao aplicada a camada classificadora.

`training.dropout` define a proporcao de neuronios desligados durante o
treinamento.

`training.augmentation.horizontal_flip` permite espelhamento horizontal.
`brightness_delta` define a variacao maxima do brilho.

### Seeds

`seeds` contem as 30 seeds fixas do protocolo. Cada seed gera um par
experimental: uma execucao da solucao principal e uma execucao da solucao
contrafactual.

## O que acontece em cada etapa

### `make prepare` (referência V1)

Carrega o dataset, aplica a segmentacao de silhueta e salva as entradas em:

```text
artifacts/v1/segmented/images/train/
artifacts/v1/segmented/images/validation/
artifacts/v1/segmented/images/test/
```

Os dois modelos usam essa mesma colecao de imagens.

### `make experiment` (V2)

Para cada uma das 30 seeds, a aplicacao treina:

- a solucao principal, com pesos ImageNet;
- a solucao contrafactual, com pesos aleatorios.

Os dois modelos usam a mesma arquitetura, dados e configuracao. Cada resultado
e salvo em `artifacts/v2/results/pair-SEED/`, com um resultado por ramo e um
resultado agregado do par.

### `make analyze` (V2)

Le os 30 resultados e calcula:

- media e desvio-padrao de F1 macro;
- media e desvio-padrao de acuracia;
- diferencas pareadas de F1 macro;
- teste t pareado bilateral sobre F1 macro;
- valor-p.

O resumo e salvo em `artifacts/v2/summary.json`.

## Evidencias publicadas

Os resultados principais para o artigo sao os 30 pares da V2. O resumo esta em
`artifacts/v2/summary.json`, os resultados detalhados estao em
`artifacts/v2/results/` e os diagnósticos Grad-CAM estao em
`artifacts/v2/gradcam/`. Esses artefatos sao publicados; somente os checkpoints
da V2 permanecem locais.

A V1 tambem possui 30 pares versionados em `artifacts/v1/results/`, com resumo
em `artifacts/v1/summary.json`. Esses arquivos sao mantidos como baseline
historico e nao fazem parte do fluxo V2 atual.

Para consultar os resultados da V2 sem treinar novamente:

```text
docs/RESULTADOS-V2.md
artifacts/v2/summary.json
artifacts/v2/results/
artifacts/v2/gradcam/
```

Para consultar o baseline historico da V1:

```text
artifacts/v1/summary.json
artifacts/v1/results/
```

`make analyze` consulta os resultados V2 sem iniciar treinamento. `make
experiment` e `make all` executam o treinamento dos pares quando chamados.
