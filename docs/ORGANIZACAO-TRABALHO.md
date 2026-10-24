# Organização do trabalho

## Referência atual

A campanha V3 é a única base de resultados e metodologia para o artigo e para a
entrega. O resumo, os resultados detalhados e os diagnósticos visuais estão em
`artifacts/v3/`. V1 e V2 são registros históricos separados.

## Objetivo

Avaliar se a inicialização da MobileNetV2 com pesos ImageNet altera o desempenho
da classificação de doenças em folhas de feijão quando comparada à inicialização
aleatória, mantendo iguais as demais condições experimentais.

## Dataset e entrada

O experimento usa `beans:0.1.0` nos splits oficiais:

| Split | Imagens |
| --- | ---: |
| Treino | 1.034 |
| Validação | 133 |
| Teste | 128 |

As classes são `angular_leaf_spot`, `bean_rust` e `healthy`. A segmentação HSV
remove o fundo, preserva a silhueta e as regiões internas da folha e produz
entradas RGB em `160 x 160`.

## Ramos comparados

| Ramo | Inicialização da base |
| --- | --- |
| Solução principal | Pesos ImageNet |
| Solução contrafactual | Pesos aleatórios |

Os dois ramos usam a mesma arquitetura, entradas, cabeça, hiperparâmetros e
seeds. A diferença deliberada é a inicialização da base MobileNetV2.

## Treinamento e BatchNorm

Cada seed produz um par experimental com dois treinamentos fim a fim. O protocolo
usa 100 épocas, batch size 32, learning rate `0.0001`, L2 `0.0001` e dropout
`0.2`.

As camadas BatchNorm usam `momentum=0.9`. Ao final de cada época, suas estatísticas
móveis são recalibradas com entradas de treino antes da validação e da seleção do
melhor checkpoint. O teste é usado somente para a avaliação final.

## Resultados e evidências

Os resultados consolidados estão em [Resultados V3](RESULTADOS-V3.md). A
estrutura publicada é:

```text
artifacts/v3/manifest.json
artifacts/v3/summary.json
artifacts/v3/results/
artifacts/v3/gradcam/
```

O Grad-CAM usa três exemplos fixos por ramo e por seed. A interpretação é
qualitativa; os mapas não demonstram causalidade.

## Histórico

Os documentos V1 e V2 foram preservados em `docs/HISTORICO-V1/` e
`docs/HISTORICO-V2/`. Eles registram estados anteriores e não devem ser usados
para substituir a metodologia, os números ou a conclusão da V3.
