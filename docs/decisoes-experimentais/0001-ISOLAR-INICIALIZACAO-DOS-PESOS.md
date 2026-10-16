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

O piloto usou somente treino e validação e fixou um orçamento comum de 100
épocas: a solução principal estabilizou na época 100 e a contrafactual na época
15. O código exploratório não integra a entrega; a seed, as configurações, a
regra de estabilização e o resumo das curvas estão preservados em
`artifacts/v1/reports/epoch-pilot.json`.

## Aplicação na V1

A decisão foi aplicada aos 30 pares. Os dois ramos foram treinados fim a fim
desde a primeira época, variando somente a inicialização da base. Os resultados
agregados estão em `artifacts/v1/summary.json` e são interpretados em
`RESULTADOS-EXPERIMENTO.md`.

## Implementação

O código deriva uma seed determinística para cada componente do treinamento a
partir da seed do par. `_derive_seed` e `run_experiment` ficam em
`src/experimento_feijao/experiment.py`. A base contrafactual usa a seed `base`
para criar pesos aleatórios; a cabeça, os dados, os aumentos e o dropout usam
seeds próprias compartilhadas pelos dois ramos. Isso evita que a criação da
base aleatória altere as sequências dos componentes comuns.

## Aplicação na V2

A V2 manteve esta decisão sem alterar a arquitetura, os inicializadores ou os
componentes pareados. Os 30 pares foram reexecutados com a mesma separação entre
a base ImageNet e a base aleatória, acrescentando apenas telemetria e artefatos
de auditoria.
