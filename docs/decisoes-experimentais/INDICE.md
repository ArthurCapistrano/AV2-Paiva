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
- [0006 - Campanha V3 e calibração da BatchNorm](0006-CAMPANHA-V3-E-CALIBRACAO-BATCHNORM.md)

## Estado

As decisões de desenho foram aplicadas na V3. O orçamento comum é de 100 épocas,
as seeds são `1001` a `1030` e a evidência publicada está em `artifacts/v3/`.
O resumo metodológico está em `docs/RESULTADOS-V3.md` e
`docs/VALIDACAO-METODOLOGIA.md`.

A V1 e a V2 permanecem disponíveis como registros históricos. Seus documentos
estão em `docs/HISTORICO-V1/` e `docs/HISTORICO-V2/`; seus artefatos não são
usados como referência da V3.

Os registros numerados preservam a justificativa anterior à execução. Quando
uma decisão tem resultado observado, ele é acrescentado ao final do registro
correspondente sem apagar o motivo original.

A V1 aplicou as decisões de desenho, mas não preservou todos os metadados
auxiliares previstos nos registros, como o inventário separado de versões e
checksums dos artefatos.
