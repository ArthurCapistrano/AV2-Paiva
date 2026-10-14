# Guia de entendimento do projeto

Este documento foi escrito para quem precisa revisar o projeto sem ter
acompanhado sua construção. A ordem recomendada de leitura é:

1. Ler a pergunta experimental abaixo.
2. Ler o `protocol.json` e a seção correspondente neste guia.
3. Executar `make help`.
4. Acompanhar o fluxo `prepare -> experiment -> analyze`.
5. Consultar o mapa de arquivos e funções quando surgir uma dúvida.

## 1. Pergunta do experimento

O projeto investiga uma pergunta simples:

> A inicialização com pesos do ImageNet muda o desempenho de uma MobileNetV2 na
> classificação de doenças em folhas de feijão quando todo o restante do
> treinamento é mantido igual?

Para responder, o projeto compara dois ramos:

| Ramo | Inicialização da base | Papel |
| --- | --- | --- |
| Solução principal | Pesos ImageNet | Representa o uso de conhecimento transferido. |
| Solução contrafactual | Pesos aleatórios | Mostra o que acontece sem esse conhecimento inicial. |

Os dois ramos usam a mesma arquitetura, as mesmas imagens, os mesmos
hiperparâmetros e as mesmas seeds. A única diferença deliberada é a
inicialização da base da rede.

## 2. A ideia em uma frase

O projeto prepara as imagens uma vez, treina os dois ramos para cada uma das
30 seeds e compara os resultados de F1 macro e acurácia.

## 3. Vocabulário essencial

### Solução principal

É o modelo cuja base MobileNetV2 começa com pesos aprendidos no ImageNet.

### Solução contrafactual

É o modelo usado como comparação. Sua base MobileNetV2 começa com pesos
aleatórios.

### Entrada segmentada

É a imagem depois que o fundo foi substituído por cinza. A folha permanece na
imagem, inclusive suas regiões amarelas ou marrons.

### Par experimental

É a dupla de treinamentos associada a uma seed: um treinamento da solução
principal e um treinamento da solução contrafactual sob as mesmas condições.

Por exemplo, o par da seed `1001` contém:

```text
solução principal, seed 1001
solução contrafactual, seed 1001
```

### Experimento

É a execução dos 30 pares experimentais. O comando público é `experiment`.
Internamente, a função `run_experiment` percorre os 30 pares e salva os
resultados. Essa é a operação executada pelo comando público `experiment`.

## 4. Fluxo completo

```text
protocol.json
      |
      v
  prepare
      |
      v
artifacts/segmented/
      |
      v
  experiment
      |
      v
artifacts/results/pair-1001/result.json
...
artifacts/results/pair-1030/result.json
      |
      v
   analyze
      |
      v
artifacts/summary.json
```

### Etapa 1: preparação

`prepare` carrega o dataset, aplica a segmentação de silhueta e salva uma
coleção de imagens organizada por divisão e classe.

```text
artifacts/segmented/images/train/<classe>/
artifacts/segmented/images/validation/<classe>/
artifacts/segmented/images/test/<classe>/
```

Essa coleção é compartilhada pelos dois ramos. Assim, a diferença observada
não pode ser explicada por uma preparação diferente das imagens.

### Etapa 2: experimento

`experiment` lê as 30 seeds do `protocol.json`. A função `run_experiment` treina
os dois ramos para cada seed e salva somente as métricas necessárias.

Cada resultado tem este formato conceitual:

```json
{
  "seed": 1001,
  "solucao_principal": {
    "macro_f1": 0.80,
    "accuracy": 0.85
  },
  "solucao_contrafactual": {
    "macro_f1": 0.60,
    "accuracy": 0.70
  }
}
```

### Etapa 3: análise

`analyze` lê os 30 resultados e calcula:

- média e desvio-padrão de F1 macro para cada ramo;
- média e desvio-padrão de acurácia para cada ramo;
- diferença entre os ramos em cada seed;
- teste t pareado bilateral sobre as diferenças de F1 macro;
- valor-p do teste.

O teste t usa os pares, e não duas listas tratadas como independentes. Para cada
seed, a diferença é calculada assim:

```text
F1 da solução principal - F1 da solução contrafactual
```

## 5. Como executar

Instale o ambiente:

```bash
uv sync --locked
```

O `--locked` faz o ambiente usar o `uv.lock` versionado e interrompe a
instalação se ele estiver incompatível com o `pyproject.toml`.

Veja os comandos disponíveis:

```bash
make help
```

Execute o fluxo completo:

```bash
make all
```

Ou execute cada etapa separadamente:

```bash
make prepare
make experiment
make analyze
```

O `Makefile` apenas organiza os comandos. A lógica científica continua nos
módulos Python.

## 6. Entendendo o `protocol.json`

O `protocol.json` é a receita fixa do experimento. Ele não executa o código e
não define os diretórios de saída. Os diretórios são definidos pelo `Makefile`.

### `dataset`

```json
"dataset": {
  "version": "beans:0.1.0"
}
```

Identifica qual versão do dataset Beans deve ser usada.

### `segmentation.hsv`

```json
"hsv": {
  "lower": [20, 20, 20],
  "upper": [100, 255, 255]
}
```

Define os limites usados para criar uma máscara da folha no espaço de cores
HSV. Pixels dentro dos limites são candidatos a pertencer à folha.

### `segmentation.morphology`

```json
"morphology": {
  "kernel_size": 11,
  "open_iterations": 2,
  "close_iterations": 2
}
```

Controla a limpeza da máscara:

- `kernel_size`: tamanho do elemento usado pelas operações morfológicas;
- `open_iterations`: ajuda a remover ruídos pequenos;
- `close_iterations`: ajuda a preencher pequenos buracos.

Depois disso, o código seleciona o maior componente, preenche seu contorno
externo, mantém os pixels internos e troca apenas o exterior pelo fundo
`(127, 127, 127)`. A imagem final é redimensionada para `160 x 160`.

### `training`

```json
"training": {
  "epochs": 100,
  "batch_size": 32,
  "learning_rate": 0.0001,
  "l2": 0.0001,
  "dropout": 0.2,
  "augmentation": {
    "horizontal_flip": true,
    "brightness_delta": 0.05
  }
}
```

- `epochs`: número de épocas de cada treinamento;
- `batch_size`: quantidade de imagens processadas em cada lote;
- `learning_rate`: tamanho dos passos de atualização dos pesos;
- `l2`: regularização da camada classificadora;
- `dropout`: proporção de ativações desligadas na cabeça classificadora;
- `horizontal_flip`: permite espelhamento horizontal;
- `brightness_delta`: controla a variação de brilho.

Os mesmos valores são usados pelos dois ramos.

### `seeds`

A lista contém exatamente 30 seeds. Cada seed identifica um par experimental e
é usada para controlar componentes como ordem dos dados, aumentos, dropout e
inicialização da cabeça classificadora.

## 7. Mapa dos arquivos

| Arquivo ou diretório | Responsabilidade |
| --- | --- |
| `README.md` | Instruções rápidas de instalação e execução. |
| `Makefile` | Atalhos para o fluxo público. |
| `protocol.json` | Valores fixos do desenho experimental. |
| `src/experimento_feijao/cli.py` | Interface de linha de comando e coordenação. |
| `src/experimento_feijao/preparation.py` | Carregamento e segmentação das imagens. |
| `src/experimento_feijao/experiment.py` | Construção, treinamento e avaliação dos modelos. |
| `src/experimento_feijao/analysis.py` | Consolidação e análise estatística. |
| `src/experimento_feijao/__init__.py` | Identificação do pacote Python. |
| `tests/` | Verificações da CLI e do fluxo principal. |
| `docs/decisoes-experimentais/GLOSSARIO.md` | Vocabulário oficial do domínio. |
| `docs/decisoes-experimentais/0001-isolar-inicializacao-dos-pesos.md` | Decisão sobre os dois ramos. |
| `docs/decisoes-experimentais/0002-segmentacao-hsv-da-silhueta.md` | Decisão sobre a segmentação. |
| `reports/epoch-pilot.json` | Registro histórico usado para fixar o orçamento de épocas. |

## 8. Funções por módulo

As funções privadas abaixo são explicadas porque ajudam a acompanhar o fluxo.
Funções pequenas de conversão e leitura são auxiliares diretas e não mudam o
desenho do experimento.

### `cli.py`

| Função | O que faz |
| --- | --- |
| `_configuration` | Lê o JSON da configuração. |
| `_prepare` | Recebe os argumentos da operação `prepare` e chama `prepare`. |
| `_experiment` | Valida o protocolo e chama `run_experiment`. |
| `_analyze` | Chama `analyze` e apresenta o resumo no terminal. |
| `_parser` | Define os comandos e argumentos da CLI. |
| `main` | Lê os argumentos e executa a operação escolhida. |

O `cli.py` não deve conter a lógica de segmentação, treinamento ou estatística.
Ele apenas recebe parâmetros, chama o módulo responsável e mostra mensagens.

### `preparation.py`

| Função ou tipo | O que faz |
| --- | --- |
| `ImageRecord` | Representa uma imagem carregada, sua identidade e sua classe. |
| `_load_tfds` | Carrega os três splits oficiais pelo TensorFlow Datasets. |
| `_load_manifest` | Carrega uma fixture local para execução controlada. |
| `_read_image` | Lê uma imagem e converte BGR para RGB. |
| `_segment` | Cria a máscara HSV, limpa a máscara e produz a entrada segmentada. |
| `prepare` | Coordena o carregamento, a segmentação e a gravação das imagens. |

O ponto mais importante é `_segment`: ele não tenta segmentar apenas a cor verde.
Ele busca a silhueta da folha para preservar sintomas internos.

### `experiment.py`

| Função ou tipo | O que faz |
| --- | --- |
| `SegmentedRecord` | Representa uma imagem segmentada e seu rótulo numérico. |
| `_derive_seed` | Gera seeds determinísticas para componentes do treinamento. |
| `_read_configuration` | Lê os hiperparâmetros e confirma a seed do par. |
| `_load_segmented_inputs` | Encontra as imagens preparadas por split e classe. |
| `_epoch_training_data` | Ordena e aplica os aumentos de uma época. |
| `_build_model` | Cria a MobileNetV2 e sua cabeça classificadora. |
| `_run_branch` | Treina um ramo e calcula suas métricas. |
| `_metrics` | Calcula F1 macro e acurácia. |
| `run_experiment` | Executa os 30 pares e salva cada resultado. |

Em `_build_model`, a diferença central está nesta escolha:

```text
solucao_principal      -> weights="imagenet"
solucao_contrafactual  -> weights=None
```

Em `_run_branch`, o melhor estado conforme a perda de validação é mantido em
memória. O teste só é usado depois do treinamento para calcular as métricas.

### `analysis.py`

| Função | O que faz |
| --- | --- |
| `_read_results` | Lê e confere os 30 resultados esperados. |
| `_values` | Extrai uma métrica de um ramo para todas as seeds. |
| `_summary` | Calcula média e desvio-padrão. |
| `analyze` | Calcula métricas, diferenças e teste t pareado. |

Este módulo não treina modelos. Ele trabalha somente com os `result.json` já
produzidos pelo experimento.

## 9. Como revisar o projeto

Uma pessoa nova pode revisar o projeto nesta ordem:

1. Ler este guia e entender a pergunta experimental.
2. Conferir os valores do `protocol.json`.
3. Ler as decisões 0001 e 0002 para entender a inicialização e a segmentação.
4. Ler `preparation.py` e acompanhar como uma imagem vira uma entrada segmentada.
5. Ler `_build_model` e `_run_branch` em `experiment.py`.
6. Ler `run_experiment` e `_experiment` para entender a repetição das 30 seeds.
7. Ler `analysis.py` para conferir como os resultados são comparados.
8. Executar `make help` e, quando houver dados e tempo disponíveis, `make all`.

Durante a revisão, as perguntas mais importantes são:

- Os dois ramos realmente recebem as mesmas entradas?
- A única diferença entre eles continua sendo a inicialização da base?
- As 30 seeds são executadas e associadas corretamente?
- F1 macro e acurácia são calculados sobre o teste?
- O teste estatístico usa diferenças pareadas?
- O código continua simples o suficiente para ser explicado?

## 10. O que não faz parte do fluxo

Os itens abaixo foram retirados do fluxo principal para evitar complexidade que
não ajuda a responder à pergunta do trabalho:

- execução pública de apenas um par;
- Grad-CAM;
- inventário de GPU, CUDA e sistema operacional;
- manifests de auditoria e checksums;
- persistência de históricos, probabilidades e checkpoints;
- piloto automático de épocas;
- retries e execução concorrente;
- busca de hiperparâmetros;
- comparação com outras arquiteturas.

Essas ausências são intencionais. O projeto prioriza uma comparação funcional,
reproduzível e explicável no ambiente controlado da disciplina.
