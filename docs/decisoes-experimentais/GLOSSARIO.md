# Classificação de doenças em folhas de feijão

Vocabulário do desenho experimental que compara duas formas de inicializar a
mesma rede de classificação.

## Linguagem

**Solução principal**:
Braço experimental cuja base MobileNetV2 começa com conhecimento transferido do
ImageNet.
_Evitar_: modelo melhor, modelo vencedor

**MobileNetV2**:
Arquitetura compacta de rede neural usada para classificar as folhas. Foi
escolhida por combinar pesos ImageNet oficiais, inicialização aleatória
equivalente, baixo custo e compatibilidade com Grad-CAM.

**ImageNet**:
Dataset usado para pré-treinar os pesos da solução principal. Não é o nome da
arquitetura.

**Alpha**:
Multiplicador da largura da MobileNetV2, que controla a quantidade de canais
das camadas. `alpha=1.0` mantém a largura padrão.

**Cabeça classificadora**:
Camada ou conjunto final de camadas que transforma as características extraídas
pela base em probabilidades para as três classes do Beans.

**Solução contrafactual**:
Braço experimental cuja base MobileNetV2 começa sem conhecimento transferido e
serve de comparação para a solução principal.
_Evitar_: solução inferior, controle sem técnica

**Segmentação de silhueta**:
Separação entre a folha inteira e o fundo que preserva todas as cores contidas
no contorno da folha, inclusive as associadas a sintomas.
_Evitar_: segmentação do verde, segmentação da lesão

**Entrada segmentada**:
Representação da imagem após a segmentação de silhueta, usada efetivamente pela
rede de classificação e pelo Grad-CAM.
_Evitar_: imagem original, máscara

**Par experimental**:
Uma execução da solução principal e uma da solução contrafactual submetidas às
mesmas condições pareadas.
_Evitar_: duas execuções independentes

**Inicialização ImageNet**:
Estado inicial da base MobileNetV2 formado por pesos aprendidos previamente no
ImageNet.
_Evitar_: fine-tuning, modelo congelado

**Seed experimental**:
Identificador de um par de treinamentos. As seeds válidas são `1001` a `1030`.
Cada seed é transformada em valores determinísticos para controlar ordem dos
dados, aumentos, dropout, cabeça e, no ramo contrafactual, a base aleatória.
_Evitar_: tratar a seed como um novo conjunto de teste

**HSV**:
Espaço de cores que separa matiz, saturação e valor, facilitando localizar a
folha por limites globais de cor e brilho.

**Colapso contrafactual**:
Comportamento observado quando a solução contrafactual passa a prever uma única
classe para as entradas avaliadas. No diagnóstico direto do `seed 1001`, todas
as 128 previsões foram `angular_leaf_spot`.
_Evitar_: afirmar que todos os 30 pares tiveram a mesma classe prevista sem
previsões individuais

**Grad-CAM**:
Mapa qualitativo das regiões da entrada segmentada associadas à classe predita,
calculado a partir da última camada convolucional. Na V1, os mapas existem
somente para o `seed 1001`; na V2, foram gerados para os 30 pares.
_Evitar_: tratar o mapa como prova de causalidade ou como métrica de desempenho
