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

**Campanha**:
Execução completa de um protocolo, com preparação compartilhada, os 30 pares,
checkpoints, resultados, Grad-CAM e análise estatística. Cada campanha possui
uma pasta própria e não sobrescreve outra campanha.

**Logit**:
Pontuação bruta produzida pela cabeça classificadora antes da conversão para
probabilidades pelo softmax. É o escore usado pelo Grad-CAM das novas campanhas
para evitar saturação da probabilidade.

**Probabilidade**:
Saída normalizada pelo softmax a partir dos logits. As probabilidades das três
classes somam um e são usadas para a previsão e para as métricas de teste.

**Checkpoint**:
Arquivo de pesos do melhor estado de um ramo, escolhido pela menor perda de
validação. A identidade do arquivo é registrada pelo seu caminho e SHA-256.

**Calibração da BatchNorm**:
Atualização das estatísticas móveis das camadas BatchNorm usando somente as
entradas de treino antes de medir a validação ou o teste. Não atualiza pesos por
gradiente nem usa rótulos da validação ou do teste.

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
Na V2, as previsões individuais mostram que todos os 30 pares colapsaram para
uma única classe; 14 escolheram `angular_leaf_spot` e 16 escolheram `bean_rust`.
_Evitar_: aplicar a conclusão da V2 retroativamente aos artefatos incompletos da
V1.

**Grad-CAM**:
Mapa qualitativo das regiões da entrada segmentada associadas à classe predita,
calculado a partir da última camada convolucional. Na V1, os mapas existem
somente para o `seed 1001`; na V2, foram gerados para os 30 pares.
_Evitar_: tratar o mapa como prova de causalidade ou como métrica de desempenho

**V1**:
Campanha experimental original, composta pela preparação das entradas, pelos 30
pares experimentais e pela análise estatística de F1 macro e acurácia. É o
baseline histórico preservado nos artefatos V1.

**V2**:
Campanha instrumentada histórica que reexecutou o protocolo da V1 e preservou
evidências adicionais, como previsões, históricos, checkpoints e Grad-CAM. É a
fonte principal de evidências para o artigo e a entrega, além de dar nome ao
fluxo atual de `experiment`, `analyze` e `gradcam`. Não é um novo protocolo
experimental.

**Teste automatizado**:
Verificação de comportamento do código por uma ferramenta de desenvolvimento.
Não é uma etapa do treinamento nem o conjunto de imagens usado para avaliar os
modelos.

**Split de teste**:
Parte do dataset usada depois do treinamento para calcular as métricas dos dois
braços experimentais.

**Resultado de teste**:
Métrica calculada a partir das previsões feitas no split de teste. Os resultados
da V1 e da V2 estão preservados nos artefatos versionados correspondentes.
