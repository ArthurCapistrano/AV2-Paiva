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

A MobileNetV2 foi escolhida porque:

- possui pesos ImageNet oficiais e opção equivalente de inicialização aleatória;
- aceita entrada RGB 160 x 160;
- possui aproximadamente 3,5 milhões de parâmetros;
- tem custo compatível com 60 treinamentos;
- permite Grad-CAM sobre sua última camada convolucional.

Essa é uma escolha pragmática para o experimento, não uma alegação de que a
MobileNetV2 é a melhor arquitetura possível para o Beans.

## 6. Segmentação de silhueta

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
splits foram processados uma única vez; configuração, versões e checksums foram
registrados, e os dois ramos consumiram os mesmos artefatos.

GrabCut não foi usado, para preservar simplicidade, determinismo e facilidade de
explicação. Falhas remanescentes do HSV foram tratadas como limitação; se
forem frequentes ou removerem sintomas, o desenho deverá ser reconsiderado antes
dos experimentos confirmatórios.

## 7. Metodologia experimental

| Componente | Definição |
| --- | --- |
| Linguagem | Python |
| Framework | TensorFlow e Keras |
| Arquitetura | MobileNetV2, `alpha=1.0`, `include_top=False` |
| Entrada | Imagem segmentada RGB, 160 x 160 |
| Saída | Três classes |
| Repetições | 30 pares, 60 treinamentos |
| Orçamento | 100 épocas |
| Métrica primária | F1-score macro |
| Métricas secundárias | Acurácia; métricas por classe e tempo ficaram fora da V1 |
| Explicabilidade | Grad-CAM qualitativo |
| Análise primária | Teste t pareado bilateral |

O piloto com treino e validação estabilizou a perda da solução principal na
época 100 e a da contrafactual na época 15. O orçamento comum foi congelado em
100 épocas. O resumo preserva o número escolhido, a seed, as configurações, a
regra de estabilização e as curvas resumidas; o teste permaneceu intocado.

Cada par usou os mesmos pesos iniciais da cabeça, ordem de lotes, aumentos e
realizações de dropout. Seeds ou geradores separados para base, cabeça, dados,
aumento e dropout evitaram que a criação da base aleatória deslocasse as
sequências dos demais componentes. Somente o ramo contrafactual usou a seed da
base para criar seus pesos; o principal carregou os pesos ImageNet.

### Hipóteses

- **H0:** a média das diferenças pareadas de F1 macro é zero.
- **H1:** a média das diferenças pareadas de F1 macro é diferente de zero.

Seja \(d_i = F1_{ImageNet,i} - F1_{aleatoria,i}\). A análise primária aplicou
um teste t pareado bilateral aos 30 valores \(d_i\). O nível de significância
não foi armazenado no protocolo executado; a V1 publica o valor-p e não deve
apresentar uma decisão confirmatória sem explicitar esse limite. Wilcoxon fica
fora da V1.

## 8. Protocolo Grad-CAM

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

## 10. Entregáveis da V1

- código-fonte em Python com as duas soluções;
- segmentação HSV e artefatos reproduzíveis;
- 30 pares, totalizando 60 execuções;
- métricas agregadas e teste estatístico;
- seis visualizações Grad-CAM do `seed 1001`;
- documentação de resultados e limitações para o artigo.

O artigo IEEE e a apresentação não foram produzidos nesta etapa; esta entrega
fornece a base documental para que a equipe os escreva.

## 11. Critérios de conclusão da V1

- As duas soluções aplicam pelo menos três técnicas?
- A inicialização da base é a única variável experimental deliberada?
- Segmentação, dados, arquitetura e orçamento são idênticos nos dois ramos?
- Foram executados e registrados os 30 pares? Sim.
- O teste permaneceu fora de todas as decisões de ajuste?
- O F1 macro e o teste t pareado foram calculados conforme o protocolo? Sim.
- O Grad-CAM foi apresentado e interpretado somente como análise qualitativa? Sim.

## 12. Decisões e validação detalhada

As justificativas das escolhas estão em
[`docs/decisoes-experimentais/`](docs/decisoes-experimentais/README.md). O
protocolo reproduzível e suas limitações estão em
[`docs/validacao-metodologia.md`](docs/validacao-metodologia.md).
