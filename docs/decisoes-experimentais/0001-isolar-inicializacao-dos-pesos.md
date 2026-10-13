# Isolar a inicialização dos pesos

A comparação avaliará o efeito da inicialização da base MobileNetV2: a solução
principal usará pesos ImageNet e a contrafactual usará pesos aleatórios. Todas
as camadas serão treináveis desde a primeira época nos dois braços; portanto, o
procedimento será descrito como treinamento fim a fim com inicialização ImageNet
versus aleatória, e não como fine-tuning canônico em duas fases.

## Motivo

Variar congelamento, camadas treináveis ou agenda junto com os pesos iniciais
impediria atribuir a diferença observada somente à inicialização. A MobileNetV2
foi escolhida porque oferece as duas inicializações na API do Keras, aceita
entrada 160 x 160, possui aproximadamente 3,5 milhões de parâmetros e torna
viáveis os 60 treinamentos previstos. Essa é uma escolha pragmática, não uma
afirmação de que a arquitetura é superior para o Beans.

## Controles do par

Cada par usará a mesma arquitetura, cabeça, pesos iniciais da cabeça, divisão de
dados, ordem de lotes, aumentos, realizações de dropout, função de perda,
otimizador, hiperparâmetros, número de épocas e regra de checkpoint. Seeds ou
geradores separados por componente impedirão que a inicialização aleatória da
base desloque as sequências usadas pela cabeça, pelos dados, pelo aumento e pelo
dropout. Entre os braços, somente o estado inicial da base será diferente.

O número fixo de épocas será determinado em um piloto que usará somente treino
e validação. O código exploratório não integrará a entrega, mas serão preservados
o orçamento escolhido, as seeds, as configurações, a regra de estabilização e um
resumo das curvas. O documento não deve afirmar que o piloto ocorreu antes de
essas evidências existirem.
