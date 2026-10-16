# Fixar um protocolo simples de Grad-CAM

O Grad-CAM será uma análise qualitativa comum aos dois braços e explicará a
entrada segmentada efetivamente recebida pelo modelo. Ele não será usado para
declarar que uma explicação ou solução é melhor sem anotações espaciais e uma
métrica previamente definida.

## Protocolo

- Fixar previamente um dos 30 pares por sua seed.
- Sortear previamente uma imagem de teste por classe, sem observar resultados.
- Usar a última camada convolucional da MobileNetV2.
- Calcular o mapa para a classe predita.
- Manter escala, mapa de cores e transparência iguais nos dois braços.
- Mostrar, para cada caso, a imagem original, a entrada segmentada e o mapa
  sobreposto à entrada segmentada.

Na V1, o protocolo produziu seis mapas, três por braço. Destaques sobre a borda
da folha serão interpretados como possível dependência da segmentação, e não
como evidência automática de atenção a sintomas.

## Aplicação na V1

Para este diagnóstico exploratório, foi fixado o par `seed 1001` e usada uma
regra determinística: a primeira imagem de cada classe na ordem do arquivo
oficial `test.zip`. Essa regra é uma escolha operacional da V1 e não o sorteio
aleatório previsto no protocolo original. Os seis painéis estão em
`reports/gradcam/seed-1001/`. O diagnóstico com previsões, matriz de confusão e
métricas está em `reports/gradcam/seed-1001/diagnostic.json`.

Esta aplicação não representa os outros 29 pares.

## Aplicação na V2

A V2 reutilizou os três exemplos fixos da V1, identificados como `test-0042`,
`test-0085` e `test-0000`, nos 30 pares e nos dois ramos. Foram produzidos 60
arquivos `diagnostic.json` e 180 painéis PNG em `artifacts/v2/gradcam/`.

Os diagnósticos registram a classe predita e as identidades usadas. A expansão
para todos os pares aumenta a cobertura da auditoria, mas não transforma o
Grad-CAM em métrica de desempenho nem em explicação causal.
