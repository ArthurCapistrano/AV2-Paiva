# Entrega V1

Esta é a primeira entrega do projeto para a equipe que vai trabalhar no artigo.
Ela contém os resultados dos 30 pares já executados, a documentação do desenho
experimental e uma auditoria detalhada do `seed 1001`.

## Como começar

1. Leia `GUIA-ARTIGO.md`.
2. Consulte `RESULTADOS-EXPERIMENTO.md`.
3. Leia `LIMITACAO-COLAPSO-CONTRAFACTUAL.md`.
4. Abra `reports/gradcam/seed-1001/README.md` antes de interpretar as imagens.

Para consultar os números sem iniciar treinamentos:

```bash
uv sync --locked
make analyze
```

Não execute `make experiment` ou `make all` nesta entrega. O comando
`experiment` ignora pares que já possuem `result.json`, mas pode iniciar
treinamentos ausentes; nenhum deles é necessário para consultar esta entrega.

## Evidências principais

- `artifacts/summary.json`: médias, desvios, diferenças e teste t pareado.
- `artifacts/results/`: resultados individuais dos 30 pares.
- `protocol.json`: protocolo fixado.
- `reports/epoch-pilot.json`: justificativa do orçamento de 100 épocas.
- `reports/gradcam/seed-1001/diagnostic.json`: auditoria direta do caso.

## Imagens para enviar aos colegas

Enviar os seis arquivos abaixo. Os caminhos são relativos à raiz do repositorio:

```text
reports/gradcam/seed-1001/solucao_principal/angular_leaf_spot.png
reports/gradcam/seed-1001/solucao_principal/bean_rust.png
reports/gradcam/seed-1001/solucao_principal/healthy.png
reports/gradcam/seed-1001/solucao_contrafactual/angular_leaf_spot.png
reports/gradcam/seed-1001/solucao_contrafactual/bean_rust.png
reports/gradcam/seed-1001/solucao_contrafactual/healthy.png
```

Enviar também, se os colegas precisarem conferir os números do diagnóstico:

```text
reports/gradcam/seed-1001/diagnostic.json
```

Cada PNG é um painel de 960 x 320 pixels com, da esquerda para a direita, a
imagem original, a entrada segmentada e o Grad-CAM sobreposto.

## Limites da V1

- A classe prevista para todas as 128 imagens foi confirmada diretamente apenas
  no ramo contrafactual do `seed 1001`.
- Os outros 29 pares têm F1 macro e acurácia, mas não têm previsões individuais
  versionadas.
- Os mapas Grad-CAM são qualitativos e existem apenas para o `seed 1001`.
- Nenhum resultado da V1 deve ser interpretado como fine-tuning canônico em duas
  fases.

A coleta de previsões, métricas por classe, matrizes dos demais seeds e Grad-CAM
adicional pertence à V2 e não faz parte desta entrega.
