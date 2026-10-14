# Decisões experimentais

Esta pasta é a fonte de verdade para as decisões que definem o desenho
experimental. Consulte o [glossário](GLOSSARIO.md) para o vocabulário e os
registros numerados para os motivos e consequências de cada escolha.

## Registros

- [0001 - Isolar a inicialização dos pesos](0001-isolar-inicializacao-dos-pesos.md)
- [0002 - Segmentação HSV da silhueta](0002-segmentacao-hsv-da-silhueta.md)
- [0003 - Protocolo Grad-CAM](0003-protocolo-grad-cam.md)

## Estado

As decisões estão aceitas. O piloto de épocas foi executado e congelou o
orçamento comum em 100 épocas; sua evidência está em
`reports/epoch-pilot.json`. Os demais valores obtidos durante a implementação
devem ser acrescentados aos registros correspondentes somente depois dos
pilotos descritos na metodologia.
