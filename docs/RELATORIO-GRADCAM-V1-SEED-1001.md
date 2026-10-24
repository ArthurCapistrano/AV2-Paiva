# Grad-CAM do seed 1001

Esta pasta contem uma analise qualitativa de um unico par experimental. Ela
nao representa uma media das 30 seeds e nao altera os resultados oficiais.

## Selecao

Para este diagnóstico exploratório, foi escolhida a primeira imagem de teste de
cada classe na ordem do arquivo oficial `test.zip`. Isso é uma regra
determinística da V1, não o sorteio aleatório descrito no protocolo original:

- `angular_leaf_spot`: `test/angular_leaf_spot/angular_leaf_spot_test.42.jpg`;
- `bean_rust`: `test/bean_rust/bean_rust_test.33.jpg`;
- `healthy`: `test/healthy/healthy_test.21.jpg`.

A regra foi aplicada antes da geracao dos mapas deste diagnostico e esta
registrada em `diagnostic.json`.

## Arquivos

Existem tres paineis para cada solucao:

- `solucao_principal/*.png`;
- `solucao_contrafactual/*.png`.

Cada painel mostra, da esquerda para a direita, a imagem original, a entrada
segmentada e o mapa de ativacao sobreposto a entrada segmentada.

O `diagnostic.json` registra as previsoes, matrizes de confusao, metricas por
classe, perdas de validacao e identificadores das imagens.

## Metodo

O mapa usa a ultima camada convolucional da MobileNetV2 e a classe predita como
alvo. Os pesos usados sao os melhores pesos do treinamento segundo a menor
perda de validacao, seguindo a regra do experimento. A mesma escala de cores e
transparencia foi usada nos dois ramos.

Os mapas servem para levantar uma leitura qualitativa das regioes usadas por
cada modelo. Eles nao demonstram causalidade, nao medem qualidade de
explicacao e nao devem ser generalizados para os outros 29 pares.

## Atualização V2

Este diretório continua sendo o diagnóstico exploratório da V1. A V2 reutilizou
as mesmas três identidades nos 30 pares e nos dois ramos, produzindo 60
diagnósticos e 180 painéis. Os resultados ampliados estão em
[`RESULTADOS.md`](HISTORICO-V2/RESULTADOS.md); os painéis V2 permanecem
publicados em `artifacts/v2/gradcam/`.
