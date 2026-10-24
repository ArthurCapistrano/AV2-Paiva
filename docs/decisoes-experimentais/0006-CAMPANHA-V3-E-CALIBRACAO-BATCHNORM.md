# Campanha V3 e calibração da BatchNorm

## Decisão

A V3 é a campanha oficial para a metodologia, os resultados e a entrega. Seus
artefatos compactos são publicados em `artifacts/v3/`.

As duas soluções usam `momentum=0.9` nas camadas BatchNorm. Ao final de cada
época, as estatísticas móveis são recalibradas usando somente as entradas de
treino. A validação e a seleção do melhor checkpoint ocorrem depois da
calibração; o teste permanece reservado para a avaliação final.

## Escopo experimental

A comparação continua sendo entre a mesma MobileNetV2 com inicialização ImageNet
e com inicialização aleatória. O dataset, os splits, a arquitetura, os
hiperparâmetros, o orçamento de épocas e as 30 seeds são os definidos em
`protocol.json`.

A calibração atualiza somente as estatísticas móveis da BatchNorm durante uma
passagem sem gradiente. Ela não usa rótulos, validação ou teste e não altera os
pesos aprendidos pelo otimizador.

## Evidências

A campanha possui 30 pares, resultados detalhados, previsões, probabilidades,
métricas por classe, matrizes de confusão, históricos e Grad-CAM para os três
exemplos fixos de cada par. O resumo consolidado está em
`artifacts/v3/summary.json`.

Os checkpoints permanecem locais. Os resultados publicados registram o SHA-256
de cada checkpoint; o caminho completo existe somente no ambiente de execução.

## Limites

Os resultados da V3 devem ser interpretados dentro do protocolo registrado. A
campanha não demonstra que uma inicialização é superior em qualquer dataset,
arquitetura ou divisão diferente. Grad-CAM permanece uma evidência qualitativa.
