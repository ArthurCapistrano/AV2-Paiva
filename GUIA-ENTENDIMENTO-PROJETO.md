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

### Arquitetura e pesos

MobileNetV2 é a arquitetura da rede. ImageNet é um dataset usado para
pré-treinar pesos, não outra arquitetura. Assim, a solução principal usa uma
MobileNetV2 que começa com pesos aprendidos no ImageNet; a solução contrafactual
usa a mesma arquitetura começando com pesos aleatórios.

A MobileNetV2 foi escolhida por ser compacta, ter pesos ImageNet oficiais e uma
inicialização aleatória equivalente, aceitar imagens `160 x 160`, permitir
Grad-CAM e tornar viáveis os 60 treinamentos. `alpha=1.0` significa a largura
padrão da rede: a quantidade usual de canais em suas camadas. Isso não indica
uma taxa de aprendizado.

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

## 4.1 Estado da entrega V1

Os 30 pares foram executados. A solução principal teve F1 macro médio de
`0.9380` e acurácia média de `0.9385`. A solução contrafactual teve F1 macro
médio de `0.1676` e acurácia média de `0.3359`.

O teste t pareado resultou em estatística `186.4706` e valor-p
`3.3036e-46`. Esses valores estão consolidados em `artifacts/summary.json` e
explicados em `RESULTADOS-EXPERIMENTO.md`.

Uma auditoria adicional foi feita para o `seed 1001`. Nesse caso, a solução
contrafactual previu `angular_leaf_spot` para todas as 128 imagens de teste. A
matriz de confusão e as métricas por classe estão em
`reports/gradcam/seed-1001/diagnostic.json`. Essa auditoria não foi feita para
os outros 29 pares.

Os mapas Grad-CAM disponíveis também se limitam ao `seed 1001`. Eles são uma
análise qualitativa e não alteram a análise estatística dos 30 pares.

## 4.2 Estado da V2

A V2 reexecutou o mesmo protocolo com telemetria completa. Os 30 pares possuem
previsoes, probabilidades, metricas por classe, matrizes de confusao,
historicos, checkpoints locais e Grad-CAM para os tres exemplos fixos. Os
resultados e limites de interpretacao estao em `RESULTADOS-V2.md`.

Na V2, o ramo contrafactual previu uma unica classe em todos os 30 seeds. A
classe constante foi `angular_leaf_spot` em 14 seeds e `bean_rust` em 16. Esse
resultado confirma o colapso sob o protocolo fixado, mas nao isola sua causa.

O Grad-CAM da V2 usa os três exemplos fixos da V1 para os 30 pares, nos dois
ramos. Foram produzidos 60 diagnósticos e 180 painéis. A leitura continua
qualitativa e não demonstra causalidade.

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
HSV. HSV separa matiz, saturação e valor: família da cor, intensidade da cor e
brilho. Pixels dentro dos limites são candidatos a pertencer à folha.

`lower=[20,20,20]` é o limite inferior de matiz, saturação e valor; `upper` é o
limite superior. Os valores foram ajustados em uma amostra do treino para
localizar a folha e foram congelados antes de processar validação e teste. Eles
não são uma seleção feita olhando os resultados dos modelos.

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
`(127, 127, 127)`. Esse cinza médio evita introduzir um fundo preto ou branco
com uma característica forte e fica próximo de zero após a normalização da
MobileNetV2. A imagem final é redimensionada para `160 x 160`.

As imagens de validação e teste também passam por essa transformação. Isso é
esperado: o modelo precisa receber entradas no mesmo formato em todos os
splits. Não há leakage dos parâmetros de pré-processamento porque os limites e
as operações foram definidos usando somente imagens do treino, congelados e
então aplicados sem reajuste aos outros splits. Isso não prova, por si só, que
não existam imagens relacionadas entre os splits; essa independência biológica
não foi auditada pelo dataset.

GrabCut não foi usado porque normalmente exige uma inicialização por imagem,
como um retângulo ou uma máscara aproximada, e uma segmentação iterativa. Isso
traria mais parâmetros e decisões específicas por imagem, dificultando a
reprodução e a explicação. A segmentação HSV é mais simples e determinística.

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
inicialização da cabeça classificadora. No código, a seed do par é transformada
em seeds determinísticas separadas para `base`, `head`, `data`, `augmentation` e
`dropout`. Os dois ramos compartilham as seeds dos componentes comuns; somente
o ramo contrafactual usa a seed da base para criar pesos aleatórios. Isso mantém
as condições do par comparáveis sem transformar a seed em um novo conjunto de
teste.

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
| `docs/decisoes-experimentais/0003-protocolo-grad-cam.md` | Protocolo e aplicação do Grad-CAM na V1 e na V2. |
| `reports/epoch-pilot.json` | Registro histórico usado para fixar o orçamento de épocas. |
| `GUIA-ARTIGO.md` | Roteiro de leitura e uso dos resultados pelos autores. |
| `RESULTADOS-EXPERIMENTO.md` | Resultados agregados e limites de interpretação. |
| `LIMITACAO-COLAPSO-CONTRAFACTUAL.md` | Auditoria do colapso contrafactual no seed 1001. |
| `reports/gradcam/seed-1001/` | Seis painéis Grad-CAM e diagnóstico do seed 1001. |
| `RESULTADOS-V2.md` | Resultados instrumentados, Grad-CAM e interpretação final da V2. |

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
| `_load_beans_mirror` | Carrega os três splits oficiais pelo espelho do Beans. |
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
3. Ler as decisões 0001, 0002 e 0003 para entender a inicialização, a
   segmentação e o Grad-CAM.
4. Ler `preparation.py` e acompanhar como uma imagem vira uma entrada segmentada.
5. Ler `_build_model` e `_run_branch` em `experiment.py`.
6. Ler `run_experiment` e `_experiment` para entender a repetição das 30 seeds.
7. Ler `analysis.py` para conferir como os resultados são comparados.
8. Ler `v2.py` e os comandos `v2-*` para entender a auditoria instrumentada.
9. Executar `make help` e `make analyze` para consultar a V1 sem treinar.
10. Consultar `RESULTADOS-V2.md` para interpretar a V2 sem treinar.

Durante a revisão, as perguntas mais importantes são:

- Os dois ramos realmente recebem as mesmas entradas?
- A única diferença entre eles continua sendo a inicialização da base?
- As 30 seeds são executadas e associadas corretamente?
- F1 macro e acurácia são calculados sobre o teste?
- O teste estatístico usa diferenças pareadas?
- O código continua simples o suficiente para ser explicado?

## 10. O que não faz parte do fluxo V1

Os itens abaixo foram retirados do fluxo principal `make all` da V1 para evitar
complexidade que não ajuda a responder à pergunta do trabalho:

- execução pública de apenas um par;
- Grad-CAM não faz parte do fluxo principal `make all`; a V1 possui uma análise
  qualitativa separada em `reports/gradcam/seed-1001/`;
- inventário de GPU, CUDA e sistema operacional;
- manifests de auditoria adicionais;
- persistência de históricos, probabilidades e checkpoints na campanha V1;
- piloto automático de épocas;
- retries e execução concorrente;
- busca de hiperparâmetros;
- comparação com outras arquiteturas.

Essas ausências são intencionais. O projeto prioriza uma comparação funcional,
reproduzível e explicável no ambiente controlado da disciplina.

A V2 manteve o fluxo principal separado, mas criou uma campanha complementar
com históricos, probabilidades, checkpoints, métricas por classe, matrizes de
confusão e Grad-CAM para auditoria. Ela é consultada pelos comandos `v2-*` e
pelos artefatos locais em `artifacts/v2/`; não substitui o fluxo V1 nem deve ser
confundida com uma nova pergunta experimental.
