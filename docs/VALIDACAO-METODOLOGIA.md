# Validação da metodologia V3

## Escopo

Este documento registra a metodologia usada pela campanha V3, que é a
referência para o artigo e para a entrega. Os registros V1 e V2 permanecem
disponíveis em `docs/HISTORICO-V1/` e `docs/HISTORICO-V2/`, mas não participam
da metodologia ou da conclusão da V3.

## Pergunta de pesquisa

> A inicialização com pesos ImageNet altera o desempenho, medido pelo F1 macro,
> de uma MobileNetV2 na classificação de doenças em folhas de feijão quando
> comparada à inicialização aleatória, mantendo iguais as demais condições?

“Altera” mantém o caráter bilateral da comparação. A diferença por seed é:

```text
F1 macro da solução principal - F1 macro da solução contrafactual
```

## Protocolo

| Componente | Definição |
| --- | --- |
| Dataset | `beans:0.1.0` |
| Splits | 1.034 treino, 133 validação, 128 teste |
| Arquitetura | MobileNetV2, `alpha=1.0`, entrada `160 x 160` |
| Ramos | Pesos ImageNet contra pesos aleatórios |
| Treinamento | Fim a fim, 100 épocas, batch size 32 |
| Learning rate | `0.0001` |
| Regularização | L2 `0.0001` e dropout `0.2` |
| Repetições | 30 pares, seeds `1001` a `1030` |
| Métrica primária | F1 macro |
| Métrica secundária | Acurácia |
| Explicabilidade | Grad-CAM qualitativo |

A segmentação HSV é aplicada uma vez às entradas compartilhadas pelos dois
ramos. Validação e teste não participam do ajuste dos pesos. A calibração da
BatchNorm usa somente entradas de treino e ocorre antes da validação e da
seleção do checkpoint.

## Análise estatística

Para cada métrica, as diferenças pareadas são avaliadas com Shapiro-Wilk e
`alpha=0.05`. Quando a normalidade é compatível, usa-se o teste t pareado;
caso contrário, usa-se Wilcoxon signed-rank. O resumo registra o método, o
diagnóstico, o intervalo de confiança e o valor-p.

As 30 execuções reutilizam o mesmo split de teste de 128 imagens. Elas medem
principalmente a variação do treinamento sob esse split, não 30 amostras
independentes de teste.

## Evidências da V3

```text
artifacts/v3/manifest.json
artifacts/v3/summary.json
artifacts/v3/results/
artifacts/v3/gradcam/
```

Foram concluídos 30 pares, totalizando 60 treinamentos. Cada ramo possui
previsões, probabilidades, métricas por classe, matriz de confusão, histórico,
melhor época e perda de validação. O Grad-CAM possui 60 diagnósticos e 180
painéis.

## Limites

Os resultados não permitem afirmar que pesos ImageNet sempre superam qualquer
inicialização aleatória, que MobileNetV2 é a melhor arquitetura para o dataset
ou que o resultado se aplica a outros splits. Grad-CAM é evidência visual
complementar e não demonstra causalidade.
