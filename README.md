# Experimento de classificacao de folhas de feijao

Aplicacao Python 3.11 para comparar uma MobileNetV2 com inicializacao ImageNet
contra a mesma rede com inicializacao aleatoria.

## Ambiente

Instale as dependencias e veja os comandos disponiveis:

```bash
uv sync --frozen
make help
```

Para entender o projeto sem conhecimento previo, consulte o
[Guia de entendimento do projeto](GUIA-ENTENDIMENTO-PROJETO.md).

## Fluxo principal

O fluxo completo e executado com:

```bash
make all
```

Ele executa, nesta ordem:

1. Prepara as imagens segmentadas.
2. Executa os dois modelos para as 30 seeds.
3. Calcula e apresenta os resultados.

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

### `make prepare`

Carrega o dataset, aplica a segmentacao de silhueta e salva as entradas em:

```text
artifacts/segmented/images/train/
artifacts/segmented/images/validation/
artifacts/segmented/images/test/
```

Os dois modelos usam essa mesma colecao de imagens.

### `make experiment`

Para cada uma das 30 seeds, a aplicacao treina:

- a solucao principal, com pesos ImageNet;
- a solucao contrafactual, com pesos aleatorios.

Os dois modelos usam a mesma arquitetura, dados e configuracao. Cada resultado
e salvo em `artifacts/results/pair-SEED/result.json`.

### `make analyze`

Le os 30 resultados e calcula:

- media e desvio-padrao de F1 macro;
- media e desvio-padrao de acuracia;
- diferencas pareadas de F1 macro e acuracia;
- teste t pareado bilateral sobre F1 macro;
- valor-p.

O resumo tambem e salvo em `artifacts/summary.json`.

## Dataset local

Por padrao, a preparacao carrega o dataset pelo TFDS. Para uma fixture local em
um ambiente controlado, o comando Python tambem aceita um manifesto local:

```bash
uv run experimento-feijao prepare \
  --config protocol.json \
  --dataset-manifest caminho/do/manifesto.json \
  --output artifacts/segmented
```
