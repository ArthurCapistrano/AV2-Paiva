# Limitacao: colapso da solucao contrafactual

## Resumo

A solucao contrafactual, cuja base MobileNetV2 foi inicializada com pesos
aleatorios, apresentou exatamente as mesmas metricas em todos os 30 pares:

- acuracia: `0.3359375`;
- F1 macro: `0.16764132553606237`;
- desvio-padrao das duas metricas: `0`.

Esse comportamento e inconsistente com a expectativa de variacao entre 30
inicializacoes aleatorias e exigiu uma auditoria direcionada.

## Evidencia numerica

O split de teste possui:

| Classe | Quantidade |
| --- | ---: |
| `angular_leaf_spot` | 43 |
| `bean_rust` | 43 |
| `healthy` | 42 |

Como `0.3359375 = 43 / 128`, as metricas contrafactuais sao compativeis com
prever uma das classes de 43 imagens para todas as entradas.

## Auditoria direta do `seed 1001`

Foi reexecutado somente o ramo contrafactual do `seed 1001`, com o mesmo
protocolo, para registrar previsoes e matriz de confusao. O resultado foi:

```text
Previsoes:
angular_leaf_spot: 128
bean_rust: 0
healthy: 0

Matriz de confusao:
[[43, 0, 0],
 [43, 0, 0],
 [42, 0, 0]]
```

As metricas desse diagnóstico foram:

- acuracia: `0.3359375`;
- F1 macro: `0.16764132553606237`;
- F1 de `angular_leaf_spot`: `0.5029239766`;
- F1 de `bean_rust`: `0`;
- F1 de `healthy`: `0`;
- melhor perda de validacao: `1.0992578268`.

O valor da perda fica proximo de `ln(3)`, compatível com um comportamento sem
separação útil entre as três classes no diagnóstico. O diagnóstico completo está
em `artifacts/v1/reports/gradcam/seed-1001/diagnostic.json`.

## Causa não determinada na V1

A V1 confirmou o comportamento, mas não foi instrumentada para isolar sua causa.
Não foram coletados, para os 30 pares, as curvas de treinamento, probabilidades,
checkpoints ou previsões completas necessárias para comparar explicações. Esta
entrega não atribui o colapso principalmente à inicialização aleatória, à taxa
de aprendizado, à cabeça classificadora ou a qualquer outro componente.

Essa ausência não invalida o resultado observado. Apenas limita a conclusão à
seguinte afirmação: sob o protocolo executado, o ramo contrafactual colapsou no
diagnóstico direto do `seed 1001`, e a causa do colapso ficou fora da V1.

## O que foi confirmado

- O calculo de acuracia e F1 nao explica sozinho a anomalia.
- O `seed 1001` realmente colapsou para uma classe.
- A auditoria confirma exatamente as metricas salvas para esse seed.
- As metricas agregadas dos 30 pares sao identicas no ramo contrafactual.

Ainda nao foram armazenadas as previsoes dos outros 29 seeds. Portanto, a
afirmacao direta sobre a classe prevista foi confirmada para o `seed 1001`,
enquanto para os demais seeds a evidencia disponivel e a repeticao exata das
metricas agregadas, sem confirmar suas classes previstas.

## Interpretacao correta

O resultado deve ser descrito como uma falha de aprendizagem ou colapso do
ramo aleatorio sob o protocolo fixado. Isso e uma caracteristica observada do
experimento, nao uma razao para apagar ou substituir os resultados.

A conclusao defensavel e:

> Sob o protocolo fixado, a inicializacao ImageNet produziu desempenho muito
> superior a inicializacao aleatoria.

Nao e defensavel concluir que pesos ImageNet sempre sao superiores, nem que a
solucao aleatoria e incapaz de aprender em qualquer protocolo.

## Consequencias para o artigo

- Nao apresentar a diferenca como uma garantia geral de transferencia de
  conhecimento.
- Explicar que o ramo aleatorio colapsou para uma classe no diagnóstico.
- Informar que a campanha final nao armazenou matrizes de confusao dos 30
  pares.
- Tratar o Grad-CAM do `seed 1001` como análise qualitativa exploratoria.
- Se uma nova campanha for feita, definir antes como armazenar previsoes,
  metricas por classe e checkpoints.

Uma nova campanha com ajuste de hiperparametros seria outro experimento e nao
deve ser misturada aos resultados atuais.

## Atualização V2

Esta auditoria preserva o que foi possível confirmar diretamente na V1. A V2
coletou previsões dos 30 pares e confirmou que todos os ramos contrafactuais
previram uma única classe: 14 seeds escolheram `angular_leaf_spot` e 16
escolheram `bean_rust`. A causa do colapso continua não determinada. Consulte
[`RESULTADOS.md`](../HISTORICO-V2/RESULTADOS.md) para os resultados instrumentados.
