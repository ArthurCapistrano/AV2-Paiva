# Experimento de classificação de folhas de feijão

Aplicação Python 3.11 que compara uma MobileNetV2 com inicialização ImageNet
contra a mesma arquitetura com inicialização aleatória.

## Referência da entrega

A V3 é a única referência de metodologia, resultados e evidências para o
artigo e para a entrega final. Seus artefatos publicados estão em
`artifacts/v3/` e sua interpretação está em `docs/RESULTADOS-V3.md`.

Os registros V1 e V2 foram preservados em seus próprios artefatos e na pasta de
histórico. Eles não devem ser usados para substituir os resultados da V3.

## Ambiente

Na raiz do projeto:

```bash
uv sync --locked
make help
```

O projeto usa TensorFlow/Keras e pode usar GPU. A campanha completa executa 60
treinamentos e pode levar bastante tempo. O fluxo não sobrescreve uma campanha
existente; use um identificador novo para cada execução.

## Consultar a V3 sem treinar

Os resultados publicados podem ser consultados diretamente:

```bash
uv run experimento-feijao analyze --results artifacts/v3
```

O comando lê os 30 pares e apresenta as métricas. O resumo consolidado já está
em `artifacts/v3/summary.json`.

Materiais disponíveis:

```text
artifacts/v3/manifest.json  configuração, seeds e proveniência
artifacts/v3/summary.json   métricas agregadas e análise estatística
artifacts/v3/results/       resultados detalhados dos 30 pares
artifacts/v3/gradcam/       diagnósticos e painéis Grad-CAM
```

Os checkpoints e as entradas segmentadas não são publicados.

## Executar uma nova campanha

Para reproduzir o fluxo em uma nova pasta:

```bash
make all CAMPAIGN=artifacts/campaigns/campaign-nova
```

O comando executa, nesta ordem:

1. prepara ou reutiliza as entradas segmentadas;
2. treina os dois ramos nas 30 seeds;
3. gera os mapas Grad-CAM;
4. calcula a análise estatística;
5. grava o resumo em `<campanha>/summary.json`.

As etapas também podem ser executadas separadamente:

```bash
make prepare
make experiment CAMPAIGN=artifacts/campaigns/campaign-nova
make gradcam CAMPAIGN=artifacts/campaigns/campaign-nova
make analyze CAMPAIGN=artifacts/campaigns/campaign-nova
```

`make prepare` gera as entradas em `artifacts/v1/segmented/`. Essa pasta é
compartilhada pelos dois ramos e permanece local.

## Protocolo V3

- Dataset: `beans:0.1.0`.
- Splits: 1.034 treino, 133 validação e 128 teste.
- Entrada: imagem RGB segmentada em `160 x 160`.
- Arquitetura: MobileNetV2, `alpha=1.0`, sem a cabeça ImageNet original.
- Solução principal: pesos ImageNet.
- Solução contrafactual: pesos aleatórios.
- Treinamento: 100 épocas, batch size 32, learning rate `0.0001`.
- Regularização: L2 `0.0001` e dropout `0.2`.
- Seeds: `1001` a `1030`.
- BatchNorm: `momentum=0.9` e calibração com entradas de treino após cada época.
- Métrica primária: F1 macro.
- Métrica secundária: acurácia.

A validação seleciona o melhor estado após a calibração da BatchNorm. O conjunto
de teste é usado somente na avaliação final.

## Documentação

### Referência V3

- [Resultados V3](docs/RESULTADOS-V3.md)
- [Validação da metodologia](docs/VALIDACAO-METODOLOGIA.md)
- [Guia para o artigo](docs/GUIA-ARTIGO.md)
- [Guia de entendimento](docs/GUIA-ENTENDIMENTO-PROJETO.md)
- [Índice de evidências](docs/INDICE-EVIDENCIAS.md)
- [Organização do trabalho](docs/ORGANIZACAO-TRABALHO.md)
- [Decisões experimentais](docs/decisoes-experimentais/INDICE.md)
- [Glossário](docs/decisoes-experimentais/GLOSSARIO.md)

### Histórico

- [Histórico V1](docs/HISTORICO-V1/)
- [Histórico V2](docs/HISTORICO-V2/)
- [Relatório Grad-CAM V1](docs/RELATORIO-GRADCAM-V1-SEED-1001.md)
