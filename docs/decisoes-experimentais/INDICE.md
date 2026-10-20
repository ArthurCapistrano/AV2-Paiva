# Decisões experimentais

Esta pasta é a fonte de verdade para as decisões que definem o desenho
experimental. Consulte o [glossário](GLOSSARIO.md) para o vocabulário e os
registros numerados para os motivos e consequências de cada escolha.

## Registros

- [0001 - Isolar a inicialização dos pesos](0001-ISOLAR-INICIALIZACAO-DOS-PESOS.md)
- [0002 - Segmentação HSV da silhueta](0002-SEGMENTACAO-HSV-DA-SILHUETA.md)
- [0003 - Protocolo Grad-CAM](0003-PROTOCOLO-GRAD-CAM.md)
- [0004 - Manter a V2 como campanha histórica](0004-V2-CAMPANHA-HISTORICA.md)
- [0005 - Campanhas reproduzíveis e análise estatística](0005-CAMPANHAS-REPRODUTIVEIS-E-ANALISE.md)

## Estado

As decisões estão aceitas e foram aplicadas na V1. O piloto de épocas congelou
o orçamento comum em 100 épocas; sua evidência está em
`artifacts/v1/reports/epoch-pilot.json`. Os resultados agregados da V1 estão em
`artifacts/v1/summary.json`. O diagnóstico e os seis mapas do `seed 1001` estão em
`artifacts/v1/reports/gradcam/seed-1001/`.

A V2 reexecutou o mesmo desenho com telemetria adicional. Seus resultados estão
em `../RESULTADOS-V2.md` e o resumo está em `artifacts/v2/summary.json`. O
Grad-CAM da V2 cobre os 30 pares; os checkpoints permanecem locais.

Os registros numerados preservam a justificativa anterior à execução. Quando
uma decisão tem resultado observado, ele é acrescentado ao final do registro
correspondente sem apagar o motivo original.

A V1 aplicou as decisões de desenho, mas não preservou todos os metadados
auxiliares previstos nos registros, como o inventário separado de versões e
checksums dos artefatos.
