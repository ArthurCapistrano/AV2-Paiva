# Segmentar a silhueta com HSV

A segmentação removerá somente o fundo. Um procedimento determinístico em HSV
localizará a folha, preencherá seu contorno externo e preservará todos os pixels
internos, inclusive regiões amarelas e marrons que possam representar sintomas.

HSV separa matiz, saturação e valor: família da cor, intensidade da cor e
brilho. Os limites inferior `[20, 20, 20]` e superior `[100, 255, 255]`
selecionam pixels candidatos à folha. O exterior é substituído por
`(127, 127, 127)`, um cinza médio neutro que não introduz um fundo preto ou
branco forte e fica próximo de zero após a normalização da rede.

GrabCut foi rejeitado porque normalmente exige uma inicialização ou máscara por
imagem e uma segmentação iterativa. Isso acrescentaria parâmetros e decisões
específicas por imagem, dificultando a reprodução e a explicação.

## Ajuste e rubrica

Os parâmetros globais serão ajustados em 30 imagens do treino, dez por classe,
selecionadas por uma seed previamente fixada. A máscara será aceita quando:

- mantiver a folha como um componente contínuo;
- não cortar bordas relevantes;
- preservar regiões amarelas e marrons internas;
- remover a maior parte do fundo;
- dispensar correções manuais por imagem.

Se houver falhas, somente limites HSV e operações morfológicas globais poderão
ser ajustados nessa amostra. Falhas remanescentes serão contabilizadas e
tratadas como limitação. Falhas frequentes ou que removam sintomas exigirão
reconsiderar o desenho antes dos experimentos confirmatórios.

## Procedimento congelado

Depois do ajuste no treino, serão fixados limites HSV, operações morfológicas,
regra do maior componente, preenchimento do contorno, cor de fundo e método de
redimensionamento. Validação, teste e resultados dos modelos não poderão mudar
essas escolhas.

O procedimento será:

1. converter a imagem original para HSV;
2. aplicar limites globais para obter a máscara inicial;
3. aplicar operações morfológicas fixas;
4. selecionar o maior componente associado à folha;
5. extrair e preencher seu contorno externo;
6. substituir somente o exterior por RGB `(127, 127, 127)`;
7. redimensionar a imagem composta para 160 x 160 pelo método fixado.

Todos os splits serão segmentados uma única vez depois do congelamento. A
configuração, as versões e os checksums dos artefatos serão registrados, e os
dois braços consumirão exatamente os mesmos arquivos. “Congelado” se refere ao
procedimento de segmentação, não às camadas da rede neural.

## Aplicação na V1

O procedimento foi aplicado aos splits oficiais e as mesmas entradas segmentadas
foram fornecidas aos dois ramos. As imagens de exemplo da segmentação estão em
`../assets/segmentation/`. O Grad-CAM da V1 também mostra a imagem original, a
entrada segmentada e o mapa sobreposto à entrada segmentada.

A V1 não preservou um inventário separado de versões e checksums dos artefatos.
Essa parte do registro fica classificada como não feita na auditoria da V1.

## Aplicação na V2

A V2 reutilizou o mesmo procedimento de segmentação congelado da V1 nos três
splits. A coleta adicional preservou os resultados dos modelos e os diagnósticos
locais, mas não transformou a segmentação em uma métrica objetiva de qualidade.

## Aplicação na V3

A V3 usa as mesmas entradas segmentadas compartilhadas pelos dois ramos. Os
parâmetros congelados e a proveniência da preparação estão registrados no
manifesto em `artifacts/v3/manifest.json`.
