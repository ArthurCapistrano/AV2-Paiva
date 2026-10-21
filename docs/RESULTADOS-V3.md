# Resultados da V3

## Referência

A V3 é a campanha oficial para o artigo e para a entrega. Ela contém os 30
pares experimentais, os resultados detalhados, os diagnósticos Grad-CAM e o
resumo estatístico publicados em `artifacts/v3/`.

Os registros V1 e V2 permanecem disponíveis somente como histórico. Eles não
fazem parte da metodologia nem da conclusão da V3.

## Protocolo

- Dataset: `beans:0.1.0`.
- Divisões: 1.034 imagens de treino, 133 de validação e 128 de teste.
- Arquitetura: MobileNetV2, `alpha=1.0`, entrada `160 x 160`.
- Solução principal: base inicializada com pesos ImageNet.
- Solução contrafactual: base inicializada com pesos aleatórios.
- Treinamento: fim a fim, 100 épocas, batch size 32.
- Learning rate: `0.0001`.
- Regularização: L2 `0.0001` e dropout `0.2`.
- Seeds: `1001` a `1030`, formando 30 pares.
- Métrica primária: F1 macro.
- Métrica secundária: acurácia.

As duas soluções usam `momentum=0.9` nas camadas BatchNorm. Após cada época,
as estatísticas móveis são recalibradas usando somente as entradas de treino.
A validação e a seleção do checkpoint acontecem depois dessa calibração. O
teste é usado somente na avaliação final.

## Evidências

```text
artifacts/v3/manifest.json
artifacts/v3/summary.json
artifacts/v3/results/
artifacts/v3/gradcam/
```

Cada par possui o resultado agregado e um resultado detalhado para cada ramo.
Os resultados detalhados incluem histórico, melhor época, perda de validação,
tempo, probabilidades, previsões, métricas por classe e matriz de confusão.

O Grad-CAM contém 60 diagnósticos e 180 painéis PNG, usando os três exemplos
fixos para os dois ramos de cada seed.

Os checkpoints não são publicados. Seus caminhos e hashes permanecem registrados
nos resultados para auditoria local.

## Resultados agregados

| Solução | Acurácia média | Desvio-padrão | F1 macro médio | Desvio-padrão |
| --- | ---: | ---: | ---: | ---: |
| Principal, pesos ImageNet | 0.8378 | 0.0364 | 0.8375 | 0.0367 |
| Contrafactual, pesos aleatórios | 0.5880 | 0.0373 | 0.5880 | 0.0383 |

A diferença pareada é calculada como:

```text
solução principal - solução contrafactual
```

Para F1 macro, a diferença média foi `0.2496`, com intervalo de confiança de
95% `[0.2356, 0.2636]`. O teste t pareado apresentou estatística `36.4909` e
valor-p `8.6521e-26`. Para acurácia, a diferença média foi `0.2497`, com
intervalo de confiança de 95% `[0.2358, 0.2637]` e valor-p `7.8299e-26`.

As diferenças passaram no diagnóstico de normalidade de Shapiro-Wilk para as
duas métricas, com `alpha=0.05`, e por isso foi usado o teste t pareado.

## Grad-CAM

Os painéis são evidências visuais complementares sobre as regiões associadas à
classe predita. Eles não demonstram causalidade nem medem a importância de um
atributo de forma independente.

## Interpretação

Sob o protocolo da V3, a solução principal apresentou desempenho superior à
solução contrafactual nas duas métricas agregadas. A solução contrafactual
apresentou desempenho mensurável nas três classes e não exibiu previsão
constante entre os 30 pares.

Essa conclusão é limitada ao dataset, às divisões, à arquitetura e às
configurações da V3. As 30 execuções reutilizam o mesmo split de teste de 128
imagens; elas medem principalmente a variação do treinamento, e não 30 amostras
independentes de teste.
