# Resultados do experimento

## Pergunta

O estudo pergunta se a inicializacao da base MobileNetV2 com pesos ImageNet
altera o desempenho da classificacao de doencas em folhas de feijao quando
comparada a inicializacao aleatoria, mantendo as demais condicoes iguais.

## Protocolo executado

- Dataset: `beans:0.1.0`.
- Classes: `angular_leaf_spot`, `bean_rust` e `healthy`.
- Splits oficiais: 1034 treino, 133 validacao e 128 teste.
- Arquitetura: MobileNetV2, `alpha=1.0`, entrada `160 x 160`.
- Epocas: 100.
- Batch size: 32.
- Seeds: 1001 a 1030.
- Pares: 30.
- Treinamentos: 60.
- Metrica primaria: F1 macro.
- Teste estatistico: t pareado bilateral.

## Resumo agregado

| Solucao | F1 macro medio | Desvio-padrao | Acuracia media | Desvio-padrao |
| --- | ---: | ---: | ---: | ---: |
| Principal, pesos ImageNet | 0.9380 | 0.0226 | 0.9385 | 0.0220 |
| Contrafactual, pesos aleatorios | 0.1676 | 0.0000 | 0.3359 | 0.0000 |

As diferencas pareadas foram calculadas como principal menos contrafactual:

- diferenca media de F1 macro: `0.7704`;
- diferenca media de acuracia: `0.6026`;
- estatistica t pareada: `186.4706`;
- valor-p: `3.3036e-46`.

O valor-p é publicado como resultado descritivo da análise executada. O nível de
significância não foi armazenado no protocolo desta campanha, portanto a V1 não
trata uma decisão de rejeição como pré-registrada.

O arquivo completo esta em `artifacts/summary.json`. Cada par individual esta
em `artifacts/results/pair-SEED/result.json`.

## Interpretacao

Dentro do protocolo fixado, a inicializacao ImageNet esteve associada a um
desempenho muito superior ao ramo aleatorio. O resultado responde a pergunta
sob estas escolhas de dataset, segmentacao, arquitetura, hiperparametros,
epocas e seeds.

O resultado nao deve ser apresentado como prova de superioridade geral de
ImageNet. Tambem nao deve ser descrito como uma comparacao de fine-tuning
canonico: os dois ramos foram treinados fim a fim desde a primeira epoca.

## Limitacoes imediatas

As metricas finais armazenam somente F1 macro e acuracia. A campanha nao
armazenou previsoes, matrizes de confusao, metricas por classe ou checkpoints
dos 30 pares. Por isso, nao e possivel reconstruir essas informacoes para a
campanha completa sem novos treinamentos.

O teste reutiliza as mesmas 128 imagens em todos os pares. As 30 repeticoes
medem principalmente a variacao do treinamento condicionada a esse split; nao
representam 30 conjuntos de teste independentes.

O comportamento anomalo da solucao contrafactual esta detalhado em
`LIMITACAO-COLAPSO-CONTRAFACTUAL.md`.
