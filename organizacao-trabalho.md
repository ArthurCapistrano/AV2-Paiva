# Proposta de projeto de Visão Computacional

## 1. Proposta

**Título provisório:** Avaliação do impacto da inicialização ImageNet na
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

“Altera” é usado em vez de “melhora” porque o teste de hipóteses será bilateral.

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

Será usado o `beans:0.1.0`, disponível no
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

1. Aplicar a segmentação de silhueta.
2. Instanciar MobileNetV2 sem a cabeça original e com pesos ImageNet.
3. Acrescentar a cabeça de classificação para três classes.
4. Treinar todas as camadas desde a primeira época.
5. Gerar Grad-CAM segundo o protocolo pré-fixado.

### Solução contrafactual

1. Consumir exatamente as mesmas entradas segmentadas.
2. Instanciar a mesma MobileNetV2 sem a cabeça original e com pesos aleatórios.
3. Usar a mesma cabeça de classificação, com os mesmos pesos iniciais do par.
4. Treinar todas as camadas desde a primeira época.
5. Gerar Grad-CAM segundo o mesmo protocolo.

A única variável experimental deliberada será o estado inicial dos pesos da base
MobileNetV2. O estudo será descrito como **treinamento fim a fim com inicialização
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

A segmentação HSV removerá apenas o fundo. O verde será usado para localizar a
folha, mas a máscara final preencherá o contorno externo, preservando regiões
internas amarelas e marrons que possam representar sintomas.

Os parâmetros globais serão ajustados em 30 imagens do treino, dez por classe,
selecionadas por uma seed pré-fixada. A rubrica verificará continuidade da folha,
preservação das bordas e sintomas, remoção da maior parte do fundo e ausência de
correções manuais. Validação e teste não participarão desse ajuste.

Depois do piloto, o procedimento será congelado: limites HSV, operações
morfológicas, maior componente, preenchimento do contorno, fundo RGB
`(127, 127, 127)` e redimensionamento para 160 x 160 não poderão mais mudar. Os
splits serão processados uma única vez; configuração, versões e checksums serão
registrados, e os dois ramos consumirão os mesmos artefatos.

GrabCut não será usado, para preservar simplicidade, determinismo e facilidade de
explicação. Falhas remanescentes do HSV serão contabilizadas como limitação; se
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
| Métricas secundárias | Acurácia, métricas por classe e tempo de treinamento |
| Explicabilidade | Grad-CAM qualitativo |
| Análise primária | Teste t pareado bilateral |

O piloto com treino e validação estabilizou a perda da solução principal na
época 100 e a da contrafactual na época 15. O orçamento comum foi congelado em
100 épocas. O resumo preserva o número escolhido, a seed, as configurações, a
regra de estabilização e as curvas resumidas; o teste permaneceu intocado.

Cada par usará os mesmos pesos iniciais da cabeça, ordem de lotes, aumentos e
realizações de dropout. Seeds ou geradores separados para base, cabeça, dados,
aumento e dropout evitarão que a criação da base aleatória desloque as sequências
dos demais componentes. Somente o ramo contrafactual usará a seed da base para
criar seus pesos; o principal carregará os pesos ImageNet.

### Hipóteses

- **H0:** a média das diferenças pareadas de F1 macro é zero.
- **H1:** a média das diferenças pareadas de F1 macro é diferente de zero.

Seja \(d_i = F1_{ImageNet,i} - F1_{aleatoria,i}\). A análise primária aplicará
um teste t pareado bilateral aos 30 valores \(d_i\), com nível de significância
pré-fixado. Wilcoxon poderá aparecer apenas como análise de sensibilidade, com a
interpretação própria de sua hipótese.

## 8. Protocolo Grad-CAM

Antes dos resultados, será fixado um dos 30 pares por sua seed. Também será
sorteada uma imagem de teste por classe. Para cada ramo, o Grad-CAM será
calculado para a classe predita na última camada convolucional da MobileNetV2.

Serão produzidos seis mapas, três por ramo. Cada caso mostrará a imagem
original, a entrada segmentada e o mapa sobreposto a essa entrada. Escala, mapa
de cores e transparência serão iguais. A análise será qualitativa; destaques nas
bordas serão tratados como possível dependência da segmentação, não como
evidência automática de atenção a sintomas.

## 9. Resultados esperados

A expectativa, ainda não comprovada, é que a inicialização ImageNet produza
melhor desempenho. Um resultado sem diferença estatisticamente significativa
também será válido. O estudo deverá responder:

1. A inicialização ImageNet altera o F1-score macro?
2. Qual é a magnitude e a incerteza da diferença observada?
3. Quais regiões das entradas segmentadas aparecem nos mapas Grad-CAM?

## 10. Entregáveis desta etapa

- código-fonte em Python com as duas soluções;
- segmentação HSV e artefatos reproduzíveis;
- 30 execuções por abordagem;
- métricas, teste estatístico e gráficos comparativos;
- visualizações Grad-CAM.

O artigo IEEE e a apresentação não serão produzidos nesta etapa.

## 11. Critérios de conclusão

- As duas soluções aplicam pelo menos três técnicas?
- A inicialização da base é a única variável experimental deliberada?
- Segmentação, dados, arquitetura e orçamento são idênticos nos dois ramos?
- Foram executados e registrados os 30 pares?
- O teste permaneceu fora de todas as decisões de ajuste?
- O F1 macro e o teste t pareado foram calculados conforme o protocolo?
- O Grad-CAM foi apresentado e interpretado somente como análise qualitativa?

## 12. Decisões e validação detalhada

As justificativas das escolhas estão em
[`docs/decisoes-experimentais/`](docs/decisoes-experimentais/README.md). O
protocolo reproduzível e suas limitações estão em
[`docs/validacao-metodologia.md`](docs/validacao-metodologia.md).
