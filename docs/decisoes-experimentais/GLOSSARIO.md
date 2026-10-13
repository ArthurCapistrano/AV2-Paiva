# Classificação de doenças em folhas de feijão

Vocabulário do desenho experimental que compara duas formas de inicializar a
mesma rede de classificação.

## Linguagem

**Solução principal**:
Braço experimental cuja base MobileNetV2 começa com conhecimento transferido do
ImageNet.
_Evitar_: modelo melhor, modelo vencedor

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
