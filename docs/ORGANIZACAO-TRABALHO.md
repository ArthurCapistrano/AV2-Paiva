# Registro do projeto de Visão Computacional

## 1. Objetivo e pergunta

**Título:** Avaliação do impacto da inicialização ImageNet na
classificação de doenças em folhas de feijão com pré-processamento por
segmentação.

**Problema:** a identificação de doenças em plantações pode depender de inspeção
visual, que demanda tempo e conhecimento especializado. Modelos de Visão
Computacional podem auxiliar na classificação de doenças a partir de fotografias
das folhas, mas o treinamento de redes profundas é difícil quando existem poucos
exemplos rotulados.

**Objetivo:** avaliar se a inicialização da MobileNetV2 com pesos ImageNet altera
o desempenho da classificação quando comparada à inicialização aleatória, sob o
mesmo protocolo experimental.

**Pergunta de pesquisa:**

> A inicialização com pesos ImageNet altera o F1-score macro da MobileNetV2 na
> classificação de doenças em folhas de feijão quando comparada à inicialização
> aleatória, mantendo iguais as demais condições experimentais?

“Altera” foi usado em vez de “melhora” porque o teste de hipóteses foi bilateral.

## 2. Técnicas utilizadas

| Técnica | Aplicação |
| --- | --- |
| Segmentação | Isolar a silhueta completa da folha e remover somente o fundo |
| Classificação (CNN) | Classificar a folha em uma das três categorias |
| Explainable AI (Grad-CAM) | Mostrar regiões associadas à classe predita |
| Transfer Learning | Iniciar a base da solução principal com pesos ImageNet |

Segmentação, Classificação e Grad-CAM são comuns às duas soluções e atendem ao
requisito mínimo de três técnicas por solução. Transfer Learning aparece somente
na solução principal.

## 3. Dataset

Foi usado o `beans:0.1.0`, disponível no
[espelho oficial do Beans no Hugging Face](https://huggingface.co/datasets/AI-Lab-Makerere/beans),
com 1.295 imagens RGB 500 x 500 nos splits oficiais:

| Split | Imagens |
| --- | ---: |
| Treino | 1.034 |
| Validação | 133 |
| Teste | 128 |

As três classes são `angular_leaf_spot`, `bean_rust` e `healthy`. O tamanho
reduzido do conjunto permite investigar o valor do conhecimento transferido e
torna viáveis as 30 repetições pareadas exigidas.

## 4. Soluções comparadas

### Solução principal

1. Aplicou a segmentação de silhueta.
2. Instanciou MobileNetV2 sem a cabeça original e com pesos ImageNet.
3. Acrescentou a cabeça de classificação para três classes.
4. Treinou todas as camadas desde a primeira época.
5. Gerou Grad-CAM para o par auditado segundo o protocolo fixado.

### Solução contrafactual

1. Consumiu exatamente as mesmas entradas segmentadas.
2. Instanciou a mesma MobileNetV2 sem a cabeça original e com pesos aleatórios.
3. Usou a mesma cabeça de classificação, com os mesmos pesos iniciais do par.
4. Treinou todas as camadas desde a primeira época.
5. Gerou Grad-CAM para o par auditado segundo o mesmo protocolo.

A única variável experimental deliberada foi o estado inicial dos pesos da base
MobileNetV2. O estudo é descrito como **treinamento fim a fim com inicialização
ImageNet versus aleatória**, e não como fine-tuning canônico em duas fases.

## 5. Justificativa da MobileNetV2

A MobileNetV2 é a arquitetura da rede de classificação. ImageNet não é uma
arquitetura: é um dataset grande usado para pré-treinar pesos. Portanto,
“MobileNetV2 com pesos ImageNet” significa a mesma arquitetura começando com
pesos aprendidos anteriormente no ImageNet. A comparação também usa a mesma
MobileNetV2 com pesos aleatórios.

A MobileNetV2 foi escolhida porque:

- possui pesos ImageNet oficiais e opção equivalente de inicialização aleatória;
- é uma CNN compacta, com aproximadamente 3,5 milhões de parâmetros;
- tem custo compatível com 60 treinamentos em um dataset pequeno;
- aceita entrada RGB 160 x 160, adequada ao pré-processamento definido;
- permite Grad-CAM sobre sua última camada convolucional.

Na configuração usada, `alpha=1.0` mantém a largura padrão da MobileNetV2, ou
seja, a quantidade usual de canais das camadas. Valores menores deixariam a
rede mais estreita e barata; valores maiores a deixariam mais larga e custosa.

Essa é uma escolha pragmática para responder à pergunta com uma arquitetura
leve, reprodutível e compatível com as técnicas do trabalho. Não é uma alegação
de que a MobileNetV2 é a melhor arquitetura possível para o Beans.

## 6. Segmentação de silhueta

HSV significa matiz, saturação e valor. Em vez de comparar diretamente os três
valores RGB, esse espaço separa a família da cor, a intensidade da cor e o
brilho. Isso facilita procurar a região colorida da folha e tratar o fundo com
uma regra simples.

Na configuração registrada, `lower=[20,20,20]` e `upper=[100,255,255]` são os
limites inferior e superior dos três componentes HSV. Pixels dentro desses
limites são candidatos a pertencer à folha. Os limites foram escolhidos na
amostra de ajuste do treino para localizar a folha sem depender de uma correção
manual por imagem.

A segmentação HSV removeu apenas o fundo. O verde foi usado para localizar a
folha, mas a máscara final preencheu o contorno externo, preservando regiões
internas amarelas e marrons que podem representar sintomas.

Os parâmetros globais foram ajustados em 30 imagens do treino, dez por classe,
selecionadas por uma seed pré-fixada. A rubrica foi definida para verificar
continuidade da folha, preservação das bordas e sintomas, remoção da maior parte
do fundo e ausência de correções manuais. Validação e teste não participaram
desse ajuste.

Depois do piloto, o procedimento foi congelado: limites HSV, operações
morfológicas, maior componente, preenchimento do contorno, fundo RGB
`(127, 127, 127)` e redimensionamento para 160 x 160 não poderão mais mudar. Os
splits foram processados uma única vez, e os dois ramos consumiram os mesmos
artefatos. A V1 não preservou um inventário separado de versões e checksums.

O fundo `(127, 127, 127)` é um cinza médio neutro. Ele evita introduzir um fundo
preto ou branco que poderia parecer uma característica da imagem e fica próximo
de zero depois da normalização usada pela MobileNetV2.

GrabCut não foi usado porque normalmente exige uma inicialização por imagem,
como um retângulo ou uma máscara aproximada, e executa uma segmentação
iterativa. Isso acrescentaria parâmetros, decisões específicas por imagem e
mais dificuldade para reproduzir e explicar o procedimento. A escolha do HSV é
mais simples e determinística. Falhas remanescentes do HSV foram tratadas como
limitação. Se forem frequentes ou removerem sintomas, o desenho deverá ser
reconsiderado antes dos experimentos confirmatórios.

## 7. Metodologia experimental

| Componente | Definição |
| --- | --- |
| Linguagem | Python |
| Framework | TensorFlow e Keras |
| Arquitetura | MobileNetV2, `alpha=1.0` (largura padrão), `include_top=False` |
| Entrada | Imagem segmentada RGB, 160 x 160 |
| Saída | Três classes |
| Repetições | 30 pares, 60 treinamentos |
| Orçamento | 100 épocas |
| Métrica primária | F1-score macro |
| Métricas secundárias | Acurácia; métricas por classe e tempo ficaram fora da V1 |
| Explicabilidade | Grad-CAM qualitativo |
| Análise primária | Teste t pareado bilateral |

Esses valores definem o protocolo comum da V1 e da V2. A V2 não alterou a
arquitetura, o dataset, os splits, os hiperparâmetros, o orçamento de épocas ou
as seeds; ela acrescentou telemetria e auditoria aos mesmos treinamentos.

O piloto com treino e validação estabilizou a perda da solução principal na
época 100 e a da contrafactual na época 15. O orçamento comum foi congelado em
100 épocas. O resumo preserva o número escolhido, a seed, as configurações, a
regra de estabilização e as curvas resumidas; o teste permaneceu intocado.

Cada par usou os mesmos pesos iniciais da cabeça, ordem de lotes, aumentos e
realizações de dropout. A seed do par é transformada em seeds determinísticas
separadas para `base`, `head`, `data`, `augmentation` e `dropout`. Assim, a
criação da base aleatória não desloca as sequências dos demais componentes.
Somente o ramo contrafactual usou a seed da base para criar seus pesos; o
principal carregou os pesos ImageNet. A implementação está em
`src/experimento_feijao/experiment.py`, nas funções `_derive_seed`,
`_build_model`, `_epoch_training_data` e `run_experiment`.

### Hipóteses

- **H0:** a média das diferenças pareadas de F1 macro é zero.
- **H1:** a média das diferenças pareadas de F1 macro é diferente de zero.

Seja \(d_i = F1_{ImageNet,i} - F1_{aleatoria,i}\). A análise primária aplicou
um teste t pareado bilateral aos 30 valores \(d_i\). O nível de significância
não foi armazenado no protocolo executado; a V1 publica o valor-p e não deve
apresentar uma decisão confirmatória sem explicitar esse limite. Wilcoxon fica
fora da V1.

## 8. Protocolo Grad-CAM da V1

Para a análise qualitativa, foi fixado o par `seed 1001` e selecionada uma
imagem de teste por classe. A seleção usou a primeira entrada de cada classe na
ordem de `test.zip`, em vez do sorteio aleatório previsto no protocolo original.
Para cada ramo, o Grad-CAM foi calculado para a classe predita na última camada
convolucional da MobileNetV2.

Foram produzidos seis mapas, três por ramo. Cada caso mostra a imagem
original, a entrada segmentada e o mapa sobreposto a essa entrada. Escala, mapa
de cores e transparência foram iguais. A análise é qualitativa; destaques nas
bordas são tratados como possível dependência da segmentação, não como
evidência automática de atenção a sintomas.

## 9. Resultados observados na V1

Os resultados agregados mostram desempenho superior da inicialização ImageNet
sob o protocolo fixado:

- F1 macro médio principal: `0.9380`;
- F1 macro médio contrafactual: `0.1676`;
- acurácia média principal: `0.9385`;
- acurácia média contrafactual: `0.3359`;
- valor-p do teste t pareado: `3.3036e-46`.

O diagnóstico do `seed 1001` mostrou que a solução contrafactual previu
`angular_leaf_spot` para todas as 128 imagens de teste. Os demais pares não
possuem previsões individuais versionadas.

Na V1, o estudo respondeu à primeira pergunta sob o protocolo fixado e mostrou
as regiões destacadas no diagnóstico qualitativo. A magnitude da diferença foi
calculada, mas seu intervalo de confiança não foi coletado.

As perguntas ficam registradas assim:

1. A inicialização ImageNet altera o F1-score macro? Sim, sob o protocolo V1.
2. Qual é a magnitude e a incerteza da diferença observada? A magnitude foi
   calculada; a incerteza por intervalo de confiança ficou fora da V1.
3. Quais regiões das entradas segmentadas aparecem nos mapas Grad-CAM? Os seis
   paineis do `seed 1001` mostram essa evidência qualitativa.

## 10. Atualização da V2

A V2 reexecutou o mesmo protocolo com telemetria adicional. Ela não introduziu
uma nova arquitetura, dataset ou divisão dos dados.

### Metodologia preservada

| Elemento | V1 e V2 |
| --- | --- |
| Arquitetura | MobileNetV2, `alpha=1.0`, sem a cabeça ImageNet original |
| Inicializações comparadas | Pesos ImageNet contra pesos aleatórios |
| Dataset e splits | `beans:0.1.0`, com 1034 treino, 133 validação e 128 teste |
| Treinamento | Fim a fim, 100 épocas, batch size 32, learning rate `0.0001` |
| Regularização | L2 `0.0001`, dropout `0.2` e os mesmos aumentos no treino |
| Repetições | Seeds `1001` a `1030`, formando 30 pares |
| Métrica primária | F1 macro no mesmo split de teste |

O que mudou na V2 foi a observabilidade: cada ramo passou a guardar previsões,
probabilidades, métricas por classe, matrizes de confusão, histórico por época,
melhor época, checkpoints locais e diagnósticos Grad-CAM. A retomada por seed e
os comandos de retomada e análise permitiram concluir a campanha sem transformar a operação
em uma nova condição experimental.

- Foram concluídos 30 pares, totalizando 60 treinamentos.
- A solução principal teve F1 macro médio `0.9380` e acurácia média `0.9385`.
- A solução contrafactual teve F1 macro médio `0.1676` e acurácia média `0.3359`.
- A diferença pareada média de F1 macro foi `0.7704`, com IC 95%
  `[0.7619, 0.7788]`.
- O teste t pareado produziu estatística `186.4706` e valor-p
  `3.3036e-46`.
- Todos os 30 pares contrafactuais previram uma única classe no teste: 14
  escolheram `angular_leaf_spot` e 16 escolheram `bean_rust`.
- Foram coletados históricos, probabilidades, métricas por classe, matrizes de
  confusão e checkpoints locais.
- O Grad-CAM foi produzido para os 30 pares, com 60 diagnósticos e 180 painéis.

As 30 execuções reutilizaram o mesmo split de teste de 128 imagens. Portanto,
medem principalmente a variação estocástica do treinamento sob esse split, e
não a variação entre 30 conjuntos de teste independentes. A causa do colapso
contrafactual também não foi isolada experimentalmente.

Os resultados detalhados da V2 estão em `RESULTADOS-V2.md`. Os resultados JSON,
o resumo e os painéis Grad-CAM são publicados em `artifacts/v2/`; somente os
checkpoints permanecem locais.

## 11. Entregáveis da V1

- código-fonte em Python com as duas soluções;
- segmentação HSV e artefatos reproduzíveis;
- 30 pares, totalizando 60 execuções;
- métricas agregadas e teste estatístico;
- seis visualizações Grad-CAM do `seed 1001`;
- documentação de resultados e limitações para o artigo.

O artigo IEEE e a apresentação não foram produzidos nesta etapa; esta entrega
fornece a base documental para que a equipe os escreva.

## 12. Critérios de conclusão da V1

- As duas soluções aplicam pelo menos três técnicas?
- A inicialização da base é a única variável experimental deliberada?
- Segmentação, dados, arquitetura e orçamento são idênticos nos dois ramos?
- Foram executados e registrados os 30 pares? Sim.
- O teste permaneceu fora de todas as decisões de ajuste?
- O F1 macro e o teste t pareado foram calculados conforme o protocolo? Sim.
- O Grad-CAM foi apresentado e interpretado somente como análise qualitativa? Sim.

## 13. Decisões e validação detalhada

As justificativas das escolhas estão em
[`decisoes-experimentais/`](decisoes-experimentais/INDICE.md). O
protocolo reproduzível e suas limitações estão em
[`VALIDACAO-METODOLOGIA.md`](VALIDACAO-METODOLOGIA.md).
