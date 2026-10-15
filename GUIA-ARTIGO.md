# Guia para o artigo

Este documento e o ponto de entrada para a equipe que vai iniciar o artigo.
Ele descreve o que ja foi feito, onde estao as evidencias e quais pontos ainda
precisam de trabalho.

## Ordem de leitura

1. `ENTREGA-V1.md`: checklist, evidencias e caminhos das imagens.
2. `README.md`: comandos e fluxo geral.
3. `GUIA-ENTENDIMENTO-PROJETO.md`: pergunta, desenho e vocabulário.
4. `RESULTADOS-EXPERIMENTO.md`: resultados agregados dos 30 pares.
5. `LIMITACAO-COLAPSO-CONTRAFACTUAL.md`: auditoria do ramo aleatorio.
6. `docs/validacao-metodologia.md`: auditoria do que foi e não foi executado.
7. `reports/epoch-pilot.json`: evidencia do orçamento de 100 epocas.
8. `reports/gradcam/seed-1001/README.md`: análise qualitativa de Grad-CAM.

## Estado da entrega

- `main` e o snapshot estavel para consulta e para o artigo.
- `develop` e a branch para novas auditorias e melhorias.
- Os 30 pares e as 60 execucoes foram concluidos.
- O sumario estatistico esta em `artifacts/summary.json`.
- Os resultados individuais estao em `artifacts/results/`.
- O Grad-CAM foi produzido somente para o par `seed 1001`.
- A limitacao do colapso da solucao contrafactual esta documentada.

## Como consultar sem refazer os treinamentos

```bash
uv sync --locked
make analyze
```

O `make analyze` usa os 30 `result.json` versionados. Nao e necessario
baixar o dataset para consultar os resultados.

Para reproduzir as entradas segmentadas localmente:

```bash
make prepare
```

Esse comando baixa os tres arquivos oficiais do Beans pelo espelho fixado,
confere os checksums e gera `artifacts/segmented/`. As imagens geradas nao sao
versionadas. Ele exige que `artifacts/segmented/` ainda nao exista; nao o
execute durante a leitura se as entradas ja estiverem preparadas.

Nao executar `make experiment` novamente como parte da leitura do projeto. O
comando ignora pares com `result.json`, mas pode iniciar treinamentos ausentes;
a campanha completa ja esta registrada no repositorio.

## Pergunta e conclusao atual

O experimento compara a mesma MobileNetV2 treinada fim a fim com duas
inicializacoes da base:

- pesos ImageNet;
- pesos aleatorios.

Sob o protocolo fixado, a solucao principal teve desempenho muito superior. A
interpretacao deve ser limitada a este protocolo. Ela nao prova que ImageNet
sempre supera qualquer inicializacao aleatoria, nem que a MobileNetV2 e a
melhor arquitetura para o Beans.

## Pontos que devem aparecer no artigo

- A comparacao e de inicializacao ImageNet contra aleatoria, nao de um fluxo
  canonico de fine-tuning em duas fases.
- O teste t e pareado por seed.
- As 30 execucoes reutilizam o mesmo split de teste de 128 imagens.
- A solucao contrafactual apresentou colapso para uma classe no diagnóstico do
  `seed 1001` e metricas agregadas identicas nos 30 pares.
- O Grad-CAM disponivel e exploratorio e limitado ao `seed 1001`.

## Trabalho posterior em `develop`

- Repetir o diagnóstico de previsoes para todas as seeds, se necessario.
- Armazenar matrizes de confusao e metricas por classe em uma nova campanha.
- Avaliar intervalos de confianca e graficos das diferencas pareadas.
- Decidir se uma nova campanha com outro protocolo e cientificamente desejada.

Esses trabalhos nao devem alterar silenciosamente os resultados da campanha
atual.
