# Resultados V2

## Escopo

A V2 reexecutou o protocolo fixado da V1 com telemetria adicional. A arquitetura,
o dataset, a segmentacao, os hiperparametros, as epocas, o batch size e as 30
seeds foram mantidos. A diferenca entre os ramos continua sendo a inicializacao
da base MobileNetV2:

- `solucao_principal`: pesos ImageNet;
- `solucao_contrafactual`: pesos aleatorios.

A V2 nao apaga nem altera os resultados versionados da V1. Para o artigo, a
entrega final e o fluxo executavel atual, a V3 e a fonte principal de resultados
e interpretacao; este documento permanece somente como registro historico.

## Execucao

- Dataset: `beans:0.1.0`.
- Splits: 1034 treino, 133 validacao e 128 teste.
- Arquitetura: MobileNetV2, `alpha=1.0`, entrada `160 x 160`.
- Epocas: 100.
- Batch size: 32.
- Seeds: `1001` a `1030`.
- Pares: 30.
- Treinamentos: 60.
- Metricas: acuracia, F1 macro, metricas por classe e matriz de confusao.
- Telemetria: historico por epoca, melhor epoca, melhor perda de validacao,
  tempo, previsoes, probabilidades e checkpoints.

Todos os pares foram concluidos. A campanha foi retomada por seed para manter o
uso de memoria sob controle; essa decisao operacional nao alterou o protocolo.

## Evidencias

O resumo consolidado esta em:

```text
artifacts/v2/summary.json
```

Cada par possui:

```text
artifacts/v2/results/pair-SEED/
artifacts/v2/checkpoints/pair-SEED/
```

O Grad-CAM foi gerado para os tres exemplos fixos da V1, nos dois ramos e nos
30 seeds:

- 60 arquivos `diagnostic.json`;
- 180 paineis PNG;
- identidades: `test-0042`, `test-0085` e `test-0000`.

Os resultados JSON, o resumo e os painéis Grad-CAM são publicados em
`artifacts/v2/`. Os checkpoints em `artifacts/v2/checkpoints/` são locais e não
devem ser enviados ao GitHub.

## Resultados agregados

| Solucao | Acuracia media | Desvio-padrao | F1 macro medio | Desvio-padrao |
| --- | ---: | ---: | ---: | ---: |
| Principal, pesos ImageNet | 0.9385 | 0.0220 | 0.9380 | 0.0226 |
| Contrafactual, pesos aleatorios | 0.3359 | 0.0000 | 0.1676 | 0.0000 |

Na solucao principal, a acuracia variou de `0.8750` a `0.9766` e o F1 macro
variou de `0.8723` a `0.9767`. No ramo contrafactual, as duas metricas foram
identicas nos 30 pares.

As diferencas pareadas de F1 macro foram calculadas como:

```text
F1 principal - F1 contrafactual
```

- diferenca media: `0.7704`;
- intervalo de confianca de 95%: `[0.7619, 0.7788]`;
- estatistica t pareada: `186.4706`;
- valor-p: `3.3036e-46`.

O valor-p e descritivo da analise executada. O protocolo nao preregistrou um
nivel de significancia ou uma decisao formal de rejeicao.

## Colapso contrafactual

As previsoes armazenadas na V2 permitem confirmar o padrao nos 30 seeds, e nao
somente no `seed 1001`:

- todos os 30 pares contrafactuais previram uma unica classe no teste;
- 14 seeds previram `angular_leaf_spot` para as 128 imagens;
- 16 seeds previram `bean_rust` para as 128 imagens;
- nenhum seed previu `healthy` como classe constante;
- nenhum dos 30 pares principais apresentou previsao constante.

Isso explica as metricas contrafactuais identicas: o split possui 43 imagens de
`angular_leaf_spot`, 43 de `bean_rust` e 42 de `healthy`. Prever sempre uma das
duas classes com 43 imagens produz acuracia `43/128 = 0.3359375` e F1 macro
`0.1676413`.

O `seed 1001` continua sendo um caso representativo: a solucao contrafactual
previu `angular_leaf_spot` nas 128 imagens. A V2 mostra que esse nao foi um caso
isolado, mas a causa do colapso ainda nao foi isolada experimentalmente.

## Grad-CAM

Os paineis da solucao principal tendem a concentrar a ativacao em regioes das
folhas e de suas estruturas visiveis. Nos paineis contrafactuais, a ativacao e
mais difusa e acompanha o comportamento de previsao constante observado nas
metricas.

Essa leitura e qualitativa. Grad-CAM nao prova causalidade, nao mede importancia
de atributos de forma independente e nao permite afirmar que uma regiao causou
a decisao. Os paineis devem ser usados como evidencia visual complementar aos
resultados numericos.

## Comparacao com a V1

A V1 e a V2 chegam ao mesmo resultado agregado principal: dentro do protocolo
fixado, a inicializacao ImageNet teve desempenho muito superior a inicializacao
aleatoria. A V2 acrescenta:

- previsoes e probabilidades por imagem;
- metricas por classe e matrizes de confusao;
- historicos de treinamento;
- checkpoints locais;
- comparacao sistematica do `seed 1001` com os demais;
- Grad-CAM para todos os pares.

A V2 nao deve ser descrita como uma nova arquitetura, um novo dataset ou um
novo protocolo. Ela e uma reexecucao instrumentada do protocolo da V1.

## Interpretacao e limites

A conclusao defensavel e:

> Sob o protocolo fixado, a inicializacao ImageNet produziu desempenho muito
> superior a inicializacao aleatoria, enquanto o ramo aleatorio colapsou para
> uma unica classe em todos os 30 seeds.

Essa conclusao nao permite afirmar que:

- pesos ImageNet sempre superam qualquer inicializacao aleatoria;
- a causa do colapso foi exclusivamente a inicializacao;
- a arquitetura MobileNetV2 e superior a outras arquiteturas;
- o resultado representa 30 conjuntos de teste independentes;
- os Grad-CAM demonstram uma explicacao causal.

As 30 repeticoes reutilizam o mesmo split de teste de 128 imagens. Elas medem
principalmente a variacao do treinamento sob esse split, e nao a variacao entre
30 amostras independentes de teste.

## Consulta historica

Os resultados da V2 podem ser consultados diretamente neste documento e nos
artefatos publicados em `artifacts/v2/`. Os checkpoints permanecem locais para
consulta; a interface atual oferece `experiment`, `analyze` e `gradcam`.
