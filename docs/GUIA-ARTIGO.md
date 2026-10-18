# Guia para o artigo

Este documento e o ponto de entrada para a equipe que vai iniciar o artigo.
Ele descreve o que ja foi feito, onde estao as evidencias e quais pontos ainda
precisam de trabalho.

A V2 e a base de evidencias do artigo, da entrega final e do fluxo executavel
atual. A V1 permanece como baseline historico e nao deve ser usada para
substituir a interpretacao consolidada da V2.

## Ordem de leitura

1. `../README.md`: estado atual, evidencias e fluxo executavel.
2. `RESULTADOS-V2.md`: resultados instrumentados, Grad-CAM e interpretacao final.
3. `VALIDACAO-METODOLOGIA.md`: auditoria do que foi e nao foi executado.
4. `INDICE-EVIDENCIAS.md`: caminhos e status dos artefatos publicados.
5. `GUIA-ENTENDIMENTO-PROJETO.md`: pergunta, desenho e vocabulário.
6. `HISTORICO-V1/ENTREGA-V1.md`: checklist e proveniencia do baseline.
7. `HISTORICO-V1/RESULTADOS-EXPERIMENTO.md`: resultados agregados da V1.
8. `HISTORICO-V1/LIMITACAO-COLAPSO-CONTRAFACTUAL.md`: auditoria histórica da V1.
9. `artifacts/v1/reports/epoch-pilot.json`: evidencia do orçamento de 100 epocas.
10. `RELATORIO-GRADCAM-V1-SEED-1001.md`: análise qualitativa de Grad-CAM da V1.

## Estado da entrega

- `main` e o snapshot estavel para consulta e para o artigo.
- `develop` e a branch para novas auditorias e melhorias.
- A V1 continua congelada em `artifacts/v1/results/` e `artifacts/v1/summary.json`.
- A V2 concluiu os 30 pares e as 60 execucoes instrumentadas.
- O resumo da V2 esta em `artifacts/v2/summary.json`.
- Os resultados, o resumo e os mapas Grad-CAM da V2 estao em `artifacts/v2/`.
- Os checkpoints da V2 permanecem locais em `artifacts/v2/checkpoints/`.
- A interpretacao consolidada esta em `RESULTADOS-V2.md`.

## Como consultar sem refazer os treinamentos

```bash
uv sync --locked
make analyze
```

O `make analyze` usa os resultados detalhados da V2. Nao e necessario baixar o
dataset para consultar esses resultados.

Os resultados da V2 podem ser consultados diretamente em `RESULTADOS-V2.md` e
nos artefatos publicados em `artifacts/v2/`. A V2 e a evidencia principal do
artigo e tambem o fluxo atual da aplicacao.

Para preparar as entradas segmentadas compartilhadas localmente:

```bash
make prepare
```

Esse comando baixa os tres arquivos oficiais do Beans pelo espelho fixado,
confere os checksums e gera `artifacts/v1/segmented/`. As imagens geradas nao sao
versionadas. O `make experiment` e o `make analyze` usam os resultados em
`artifacts/v2/`.

O Grad-CAM pode ser consultado ou gerado com `make gradcam`, usando os tres
exemplos fixos e os checkpoints da V2.

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

Esses trabalhos nao devem alterar silenciosamente os resultados da campanha
atual.
