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

O protocolo produzirá seis mapas, três por braço. Destaques sobre a borda da
folha serão interpretados como possível dependência da segmentação, e não como
evidência automática de atenção a sintomas.

## Aplicação na V1

Para este diagnóstico exploratório, foi fixado o par `seed 1001` e usada uma
regra determinística: a primeira imagem de cada classe na ordem do arquivo
oficial `test.zip`. Essa regra é uma escolha operacional da V1 e não o sorteio
aleatório previsto no protocolo original. Os seis painéis estão em
`reports/gradcam/seed-1001/`. O diagnóstico com previsões, matriz de confusão e
métricas está em `reports/gradcam/seed-1001/diagnostic.json`.

Esta aplicação não representa os outros 29 pares.
