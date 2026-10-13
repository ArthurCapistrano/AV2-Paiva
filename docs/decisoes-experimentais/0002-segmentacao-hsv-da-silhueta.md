# Segmentar a silhueta com HSV

A segmentação removerá somente o fundo. Um procedimento determinístico em HSV
localizará a folha, preencherá seu contorno externo e preservará todos os pixels
internos, inclusive regiões amarelas e marrons que possam representar sintomas.
GrabCut foi rejeitado para manter a implementação e a explicação simples.

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
