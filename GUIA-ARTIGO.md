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
6. `RESULTADOS-V2.md`: resultados instrumentados, Grad-CAM e interpretacao final.
7. `docs/validacao-metodologia.md`: auditoria do que foi e não foi executado.
8. `reports/epoch-pilot.json`: evidencia do orçamento de 100 epocas.
9. `reports/gradcam/seed-1001/README.md`: análise qualitativa de Grad-CAM da V1.

## Estado da entrega

- `main` e o snapshot estavel para consulta e para o artigo.
- `develop` e a branch para novas auditorias e melhorias.
- A V1 continua congelada em `artifacts/results/` e `artifacts/summary.json`.
- A V2 concluiu os 30 pares e as 60 execucoes instrumentadas.
- O resumo da V2 esta em `artifacts/v2/summary.json`.
- Os resultados e checkpoints da V2 estao em `artifacts/v2/` localmente.
- O Grad-CAM da V2 foi produzido para os 30 pares; os mapas nao sao
  versionados.
- A interpretacao consolidada esta em `RESULTADOS-V2.md`.

## Como consultar sem refazer os treinamentos

```bash
uv sync --locked
make analyze
```

O `make analyze` usa os 30 `result.json` versionados da V1. Nao e necessario
baixar o dataset para consultar esses resultados.

Para consultar a analise final da V2 sem treinar novamente:

```bash
uv run experimento-feijao v2-analyze \
  --results artifacts/v2 \
  --output artifacts/v2/summary.json
```

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
- A solucao contrafactual apresentou colapso para uma classe nos 30 seeds da V2;
  a classe constante foi `angular_leaf_spot` em 14 seeds e `bean_rust` em 16.
- Na V1, o Grad-CAM disponivel e exploratorio e limitado ao `seed 1001`.

O Grad-CAM da V2 amplia a evidencia visual para todos os pares, mas continua
sendo uma analise qualitativa e nao uma explicacao causal.

## Trabalho posterior em `develop`

- Avaliar se o artigo precisa de tabelas ou figuras derivadas dos artefatos V2.
- Decidir se uma nova campanha com outro protocolo e cientificamente desejada.
- Simplificar a infraestrutura V2 depois de confirmar quais controles foram uteis.

Esses trabalhos nao devem alterar silenciosamente os resultados da campanha
atual.
