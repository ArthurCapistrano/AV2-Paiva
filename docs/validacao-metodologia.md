<!-- markdownlint-disable MD013 MD033 -->

# Validação da metodologia experimental

## Escopo da pesquisa metodológica

Este documento registra o desenho experimental definido antes dos treinamentos,
a sua aplicação na entrega V1 e a auditoria instrumentada da V2. A V1 permanece
descrita como histórico: seus limites não são substituídos retroativamente. A
V2 reexecutou o mesmo protocolo e acrescentou artefatos para investigar os
limites que ficaram fora da V1.

## Estado da execução V1

- Dataset executado: `beans:0.1.0`.
- Pares executados: 30, totalizando 60 treinamentos.
- Métrica primária: F1 macro.
- Análise primária: teste t pareado bilateral.
- Grad-CAM: seis mapas somente para o `seed 1001`.
- Auditoria de previsões: somente para o ramo contrafactual do `seed 1001`.
- Nível de significância: não registrado no protocolo executado; a V1 publica o
  valor-p sem tratar uma decisão confirmatória como pré-registrada.

O resumo completo está em `artifacts/summary.json`. A auditoria do caso
contrafactual está em `reports/gradcam/seed-1001/diagnostic.json`.

Os 30 pares reutilizam o mesmo split de teste de 128 imagens. A campanha
original armazenou F1 macro e acurácia, mas não armazenou previsões, matrizes de
confusão, métricas por classe ou checkpoints para os outros 29 pares. Esses
itens ficam fora da V1.

## Estado da execução V2

- Dataset e splits: os mesmos `beans:0.1.0` e 128 imagens de teste da V1.
- Pares executados: 30, totalizando 60 treinamentos.
- Previsões, probabilidades, métricas por classe e matrizes: coletadas para os
  30 pares.
- Históricos, melhores épocas e checkpoints: coletados localmente para os 30
  pares.
- Grad-CAM: 60 diagnósticos e 180 painéis, usando os três exemplos fixos nos
  dois ramos.
- Intervalo de confiança da diferença pareada de F1: `[0.7619, 0.7788]`.
- Diferença média de F1: `0.7704`; estatística t: `186.4706`; valor-p:
  `3.3036e-46`.

Na V2, todos os 30 pares contrafactuais previram uma única classe no teste: 14
previram `angular_leaf_spot` e 16 previram `bean_rust`. Esse resultado amplia a
auditoria do colapso observado na V1, mas não identifica sua causa.

Os resultados consolidados estão em `RESULTADOS-V2.md` e
`artifacts/v2/summary.json`. Os artefatos brutos e checkpoints da V2 são locais
e não fazem parte do histórico versionado.

## Auditoria do que foi feito na V1

Esta tabela separa o protocolo planejado da execução efetivamente versionada.
“Feito” significa que há código, resultado ou artefato correspondente. “Parcial”
significa que somente uma parte do requisito foi executada. “Não feito na V1”
indica que o item não foi produzido ou registrado nesta entrega, mesmo quando
poderia ser calculado sem novo treinamento.
“Não aplicável/contraditório” identifica uma formulação que não corresponde à
pergunta executada. “Inconclusivo” indica que as fontes ou artefatos atuais não
permitem decidir.

| Item metodológico | Status V1 | Evidência e limite |
| --- | --- | --- |
| Dataset `beans:0.1.0` e splits oficiais | Feito | `protocol.json`, preparação e resultados versionados; o teste tem 128 imagens. |
| Contagens por classe de todos os splits | Não feito na V1 | A auditoria direta registra as classes do teste, mas a campanha não preservou o inventário completo dos splits. |
| Versões e checksums dos artefatos | Não feito na V1 | A preparação foi executada, mas a campanha não preservou um inventário separado desses metadados. |
| Segmentação HSV comum aos dois ramos | Parcial | A mesma preparação foi usada nos dois ramos e há exemplos visuais; não há métrica objetiva de qualidade da máscara. |
| Entrada `160 x 160` e MobileNetV2 comum | Feito | A arquitetura e a entrada estão fixadas no protocolo e no código. |
| Única diferença deliberada na base | Feito | Os dois ramos foram treinados fim a fim com a mesma configuração, variando a inicialização da base. |
| Treinamento fim a fim ImageNet versus aleatório | Feito | 30 pares, totalizando 60 treinamentos, em `artifacts/results/`. |
| Fine-tuning canônico em duas fases | Não aplicável/contraditório | Não era a pergunta da V1; não se deve chamar o treinamento executado de fine-tuning canônico. |
| F1 macro, acurácia e teste t pareado | Feito | Resultado em `artifacts/summary.json`; o nível de significância não foi registrado no protocolo. |
| Intervalo de confiança da diferença pareada | Não feito na V1 | O valor-p foi preservado, mas o intervalo não foi calculado. Ele pode ser obtido das diferenças já versionadas, sem novo treinamento, mas ficou fora da V1. |
| Previsões, matrizes e métricas por classe dos 29 pares restantes | Não feito na V1 | Os `result.json` antigos guardam somente F1 macro e acurácia. |
| Auditoria detalhada do ramo contrafactual | Parcial | O `seed 1001` foi auditado diretamente; os outros 29 não têm previsões versionadas. |
| Grad-CAM do par selecionado | Feito | Há seis painéis do `seed 1001`, conforme a análise exploratória da V1. |
| Grad-CAM adicional nos outros seeds | Não feito na V1 | Não fazia parte da entrega; não há mapas dos outros 29 pares. |
| Seleção aleatória das imagens do Grad-CAM | Parcial | Na V1 foi usada a primeira entrada de cada classe na ordem de `test.zip`, como regra determinística exploratória. |
| Tempo, épocas efetivas, probabilidades e checkpoints | Não feito na V1 | Esses artefatos não foram preservados pela campanha original. |
| Independência biológica entre os splits | Inconclusivo | O dataset separa os arquivos, mas não fornece identificadores de planta ou sessão para auditoria por grupo. |
| Causa do colapso contrafactual | Não feito na V1 | A V1 confirmou o comportamento, mas não coletou evidências para isolar sua causa. |

## Auditoria da V2

| Item metodológico | Status V2 | Evidência e limite |
| --- | --- | --- |
| Previsões, probabilidades, matrizes e métricas por classe | Feito | Coletados para os 30 pares em `artifacts/v2/`; os arquivos são locais. |
| Históricos, melhores épocas e checkpoints | Feito | Coletados para os 30 pares; checkpoints não são versionados. |
| Grad-CAM nos dois ramos e nos 30 pares | Feito | 60 diagnósticos e 180 painéis em `artifacts/v2/gradcam/`. |
| Intervalo de confiança da diferença pareada | Feito | IC 95% `[0.7619, 0.7788]` no resumo da V2. |
| Auditoria do colapso contrafactual | Feito | Todos os 30 pares colapsaram para uma classe; a causa continua inconclusiva. |
| Independência estatística entre os testes | Limite preservado | As 30 repetições reutilizam o mesmo split de teste de 128 imagens. |

## O que não deve ser inferido

O colapso para uma única classe é um resultado observado, não um diagnóstico da
causa. A V1 não permite afirmar qual componente do treinamento produziu o
comportamento. Não há evidência suficiente para atribuir a causa a uma escolha
específica.

Também não se deve afirmar que os outros 29 ramos contrafactuais previram a
mesma classe, porque somente o `seed 1001` foi auditado diretamente.

Essa última restrição era necessária para a V1. Na V2, as previsões dos 30 pares
foram coletadas e permitem afirmar que todos os ramos contrafactuais previram
uma única classe, embora a classe tenha variado entre seeds.

A V2 também não permite afirmar que ImageNet sempre supera qualquer
inicialização aleatória, que o resultado vale para outros splits ou que o
Grad-CAM demonstra causalidade.

## Limite da revisão

Esta auditoria preserva o estado histórico da V1 e registra a V2 como uma
reexecução instrumentada. A V2 coletou previsões, investigou a extensão do
colapso, calculou o intervalo de confiança e gerou Grad-CAM para todos os pares.
Ela não isolou experimentalmente a causa do colapso nem transformou o split de
teste em 30 amostras independentes.

## Pergunta científica

> A inicialização com pesos ImageNet altera o desempenho, medido pelo F1-score
> macro, da MobileNetV2 na classificação de doenças em folhas de feijão quando
> comparada à inicialização aleatória?

A formulação usa “altera”, e não “melhora”, porque o teste planejado é bilateral.

## Hipóteses

- **H0:** não existe diferença na média do F1-score macro entre a MobileNetV2
  com inicialização ImageNet e com inicialização aleatória.
- **H1:** existe diferença na média do F1-score macro entre as duas abordagens.

Seja \(d_i = F1_{ImageNet,i} - F1_{aleatoria,i}\) a diferença no par de
execução \(i\).
Assim, as hipóteses operacionais são \(H_0: \mu_d = 0\) e
\(H_1: \mu_d \neq 0\).

## Síntese da validação do desenho (histórico)

A tabela abaixo registra a análise metodológica feita antes da execução. Para
saber o que foi realmente produzido na V1, use a auditoria acima; esta tabela
preserva justificativas e requisitos que não foram necessariamente coletados.

| Ponto da proposta | Classificação | Validação e ação necessária |
| --- | --- | --- |
| Usar o TFDS Beans com três classes e os splits oficiais | **Feito** | A versão 0.1.0 possui 1.034 imagens de treino, 133 de validação e 128 de teste, totalizando 1.295 imagens RGB 500 x 500; os rótulos são `angular_leaf_spot`, `bean_rust` e `healthy` [[1]](#ref-1) [[2]](#ref-2). A V1 fixou `beans:0.1.0` e não recompôs os splits. |
| Usar segmentação HSV como técnica comum | **Parcial** | O HSV foi usado nos dois ramos e há exemplos visuais. A V1 não possui métrica objetiva de qualidade da máscara. |
| Entrada 160 x 160 na MobileNetV2 | **Feito** | A implementação usa três canais, entrada 160 x 160 e os parâmetros registrados no protocolo [[3]](#ref-3). |
| Comparar `weights="imagenet"` com `weights=None` | **Feito** | A API define essas opções como pesos ImageNet e inicialização aleatória [[3]](#ref-3); arquitetura, cabeça, pré-processamento e orçamento foram compartilhados. |
| Chamar de “fine-tuning” o treinamento de todas as camadas desde o início | **Não aplicável/contraditório** | No fluxo oficial da Keras, extração de características congela a base; fine-tuning ocorre depois de treinar a nova cabeça, ao descongelar toda ou parte da base com taxa baixa [[4]](#ref-4). O treinamento da V1 foi fim a fim desde a primeira época e não deve receber o nome de fine-tuning canônico. |
| Manter exatamente os mesmos hiperparâmetros | **Feito** | O protocolo comum isolou a inicialização sob um orçamento fixo, mas não comparou o melhor ajuste possível de cada abordagem. |
| Fazer 30 execuções por abordagem | **Feito** | Foram executados 30 pares; isso mede a variação do procedimento, mas não garante poder estatístico nem substitui um intervalo de confiança [[17]](#ref-17). |
| Escolher entre teste t pareado e Wilcoxon | **Feito** | O teste t pareado bilateral foi usado como análise primária. Wilcoxon não foi usado na V1. |
| Usar Grad-CAM nas duas abordagens | **Parcial** | Grad-CAM foi produzido para um par e três imagens por ramo; a leitura permanece qualitativa [[11]](#ref-11). |
| Afirmar que os splits evitam imagens relacionadas entre treino e teste | **Inconclusivo** | O construtor oficial confirma arquivos separados de treino, validação e teste, mas as fontes consultadas não documentam identificadores de planta, talhão ou sessão fotográfica que permitam verificar independência por grupo [[1]](#ref-1) [[2]](#ref-2). Não alegar ausência de vazamento por indivíduo sem auditoria adicional. |

## Protocolo de referência e limites

Esta seção preserva os detalhes técnicos que sustentaram o desenho. Ela não
substitui a auditoria da V1 e não significa que cada artefato recomendado foi
coletado na campanha já concluída.

### 1. Dados e pré-processamento

Usar exclusivamente os splits oficiais de `beans:0.1.0`: treino com 1.034,
validação com 133 e teste com 128 imagens. O metadado oficial registra imagens
RGB 500 x 500 com valores até 255, enquanto o construtor oficial fixa os três
rótulos e associa diretamente cada diretório ao respectivo split
[[1]](#ref-1) [[2]](#ref-2). Antes do treino, registrar a contagem de cada classe
em cada split; o total por split está confirmado, mas o balanceamento por classe
não deve ser presumido a partir dessas fontes.

Aplicar a segmentação descrita abaixo na resolução original, compor o fundo e
então redimensionar para 160 x 160 com um método fixo. Aplicar **uma única vez**
`keras.applications.mobilenet_v2.preprocess_input`. Na implementação oficial,
essa função escala os pixels para o intervalo `[-1, 1]`; aplicar também uma
divisão por 255 produziria uma entrada diferente da especificada pela API
[[3]](#ref-3). Aumento de dados, se adotado, deve ocorrer apenas no treino e usar
as mesmas transformações e realizações aleatórias dentro de cada par.

Validação e teste não podem participar do ajuste dos pesos. A validação pode
selecionar hiperparâmetros, época ou checkpoint; o teste deve ser usado somente
para a avaliação final do protocolo já fixado, evitando vazamento de informação
do teste para o ajuste [[15]](#ref-15). O split de teste contém apenas 128
imagens, de modo que poucos erros por classe podem alterar sensivelmente o F1;
por isso devem ser publicados também a matriz de confusão e os valores de
precisão, recall e F1 por classe, sem substituir a métrica primária.

#### 1.1. Segmentação de silhueta

A segmentação é uma técnica comum aos dois braços e tem como objetivo remover
somente o fundo. Usar HSV para obter uma máscara inicial, aplicar operações
morfológicas globais, selecionar o maior componente associado à folha e preencher
seu contorno externo. O preenchimento transforma a detecção por cor em uma
silhueta completa: pixels amarelos, marrons ou de outras cores permanecem quando
estão dentro do contorno. Substituir apenas o exterior por RGB `(127, 127, 127)`
e redimensionar a imagem composta para 160 x 160.

Selecionar por seed 30 imagens do treino, dez por classe, antes do ajuste. A
rubrica qualitativa deve verificar que a folha permanece contínua, bordas
relevantes não são cortadas, sintomas internos são preservados, a maior parte do
fundo é removida e nenhuma correção manual por imagem é necessária. Somente
limites HSV e operações morfológicas globais podem ser ajustados nessa amostra.
GrabCut não será usado, pois a decisão privilegia simplicidade, determinismo e
facilidade de explicação. Falhas remanescentes devem ser contabilizadas; se forem
frequentes ou removerem sintomas, o protocolo precisa ser reconsiderado antes
dos experimentos confirmatórios.

Depois do piloto no treino, congelar limites HSV, operações morfológicas, regra
do maior componente, preenchimento do contorno, cor do fundo e interpolação. Isso
significa que validação, teste e resultados dos modelos não podem alterar o
procedimento; não se refere a congelar camadas da rede. Processar cada split uma
única vez, registrar parâmetros e versões, salvar os artefatos com checksums e
fornecer exatamente os mesmos arquivos aos dois braços. O teste pode ser
processado pelo procedimento já congelado, mas suas máscaras não podem ser
inspecionadas para reajustá-lo.

### 2. Modelo e significado da comparação

Instanciar a mesma `MobileNetV2` com `input_shape=(160, 160, 3)`,
`alpha=1.0` e `include_top=False`, seguida exatamente pela mesma cabeça de três
classes. A API oficial permite `weights="imagenet"` para carregar pré-treinamento
ImageNet e `weights=None` para inicialização aleatória; com a cabeça ImageNet
incluída, `classes` teria de ser 1.000, razão pela qual a cabeça original deve ser
removida nesta tarefa de três classes [[3]](#ref-3).

A MobileNetV2 é uma escolha pragmática porque combina pesos ImageNet oficiais,
opção de inicialização aleatória, entrada 160 x 160 e baixo custo. A tabela de
Keras Applications informa aproximadamente 3,5 milhões de parâmetros e 14 MB
para a arquitetura [[21]](#ref-21). Seu projeto usa convoluções separáveis em
profundidade, resíduos invertidos e gargalos lineares para equilibrar capacidade
e eficiência [[22]](#ref-22). Essas propriedades tornam viáveis os 60
treinamentos, mas não demonstram que ela seja a melhor arquitetura para o Beans.

Para responder estritamente ao efeito da **inicialização dos pesos**, usar:

- solução principal: base com `weights="imagenet"` e todas as camadas treináveis desde a
  primeira época;
- solução contrafactual: base com `weights=None` e todas as camadas treináveis desde a
  primeira época.

Essa opção mantém arquitetura, camadas treináveis e agenda iguais, mas deve ser
descrita como “treinamento fim a fim com inicialização ImageNet versus aleatória”.
A Keras chama de extração de características o uso da base congelada e de
fine-tuning o descongelamento posterior de toda ou parte da base, normalmente
com taxa de aprendizado baixa e recompilação após alterar `trainable`
[[4]](#ref-4). A mesma documentação alerta que uma cabeça aleatória treinada
junto da base pré-treinada pode produzir atualizações grandes nos recursos
pré-treinados [[4]](#ref-4); esse risco é uma limitação consciente do desenho
mais estrito.

Se o objetivo for avaliar o **fluxo canônico de Transfer Learning**, deve existir
uma primeira fase com a base ImageNet congelada e uma segunda de fine-tuning.
Nesse caso, o braço deixa de diferir apenas pela inicialização, pois o conjunto
de parâmetros treináveis e a agenda também mudam. Esse é outro experimento e
exige pergunta e interpretação próprias. Não misturar as duas definições após
observar os resultados.

Usar a mesma função de perda, otimizador, tamanho de lote, regularização,
aumento, número fixo de épocas e regra de seleção de checkpoint nos dois braços.
Esse número foi determinado em um piloto separado com treino e validação. Pela
regra definida antes da leitura das curvas, a solução principal estabilizou na
época 100 e a contrafactual na época 15; o orçamento comum ficou congelado em
100 épocas. O horizonte do piloto foi estendido até 150 épocas sem consultar o
teste. O piloto não integra as 30 repetições, e `reports/epoch-pilot.json`
preserva o orçamento, a seed, a configuração, a regra e o resumo das curvas.

### 3. Reprodutibilidade e pareamento

Pré-definir uma lista ordenada de 30 seeds. No par \(i\), os dois braços devem
usar seeds correspondentes para ordem dos lotes, aumento, dropout e cabeça
classificadora; o braço aleatório usa ainda uma seed exclusiva do componente
base. `keras.utils.set_random_seed`
configura Python, NumPy e o backend TensorFlow, mas a própria documentação
registra limitações para operações não determinísticas [[5]](#ref-5). Ativar
também `tf.config.experimental.enable_op_determinism()`; o código-fonte oficial
do TensorFlow documenta que a opção exige seeds nas operações aleatórias e visa
execução determinística, com possível custo de desempenho [[6]](#ref-6).
Como carregar pesos ImageNet e inicializar uma base aleatória consomem números
aleatórios de maneiras diferentes, uma única seed global não basta. Usar seeds
ou geradores separados para base, cabeça, ordem dos dados, aumento e dropout.
“Separados” significa que o consumo de aleatoriedade de um componente não
desloca a sequência dos demais, não que os componentes comuns recebam seeds
diferentes entre os braços. Assim, os dois braços começam com a mesma cabeça e
recebem as mesmas ordens, transformações e máscaras de dropout; somente a base
aleatória consome sua seed específica [[7]](#ref-7).

Seeds iguais não bastam para reprodução entre ambientes: fixar e registrar
versões de Python, TensorFlow, Keras, TFDS, NumPy, scikit-learn e SciPy, além de
sistema operacional, CPU/GPU, CUDA e cuDNN. O próprio TensorFlow informa que
sequências podem mudar entre versões e recomenda seeds explícitas quando valores
repetíveis forem necessários [[7]](#ref-7). Registrar ainda a lista das 30 seeds,
ordem de execução e configuração completa em cada linha de resultado.

Alternar ou randomizar a ordem principal/contrafactual dentro de cada par reduz
a associação do braço com aquecimento do dispositivo ou carga temporal da
máquina. Executar um par por vez, no mesmo hardware e sem treinamentos
concorrentes. Uma execução que falhar não deve ser descartada silenciosamente:
registrar a falha e repetir o par completo sob uma regra definida antes da
análise.

### 4. Métrica primária

Para cada imagem do teste, converter a saída em uma única classe por `argmax` e
calcular, para cada uma das três classes,
\(F1_c = 2 P_c R_c/(P_c+R_c)\). O F1 macro é a média aritmética não ponderada
dos três valores, portanto dá o mesmo peso a cada classe independentemente de
sua frequência [[10]](#ref-10). Na implementação, fixar explicitamente
`labels=[0, 1, 2]`, `average="macro"` e a política de divisão por zero; publicar
essa política, pois uma classe sem predições pode tornar precisão ou F1
indefinidos [[10]](#ref-10).

Calcular o F1 uma vez por modelo sobre as 128 imagens agregadas, e não fazer a
média do F1 por lote. Armazenar rótulos verdadeiros, classes preditas e
probabilidades para permitir auditoria posterior, mantendo o teste fora de toda
decisão de treinamento [[10]](#ref-10) [[15]](#ref-15).

### 5. Teste estatístico

Adotar como análise primária o **teste t pareado bilateral**, com
`alternative="two-sided"` e nível de significância pré-fixado, por exemplo
\(\alpha=0{,}05\). A unidade da análise é o par de seed, e a entrada do teste são
os 30 valores \(d_i\), não as 128 predições individuais. A API de referência
define o teste para duas amostras relacionadas e calcula a estatística a partir
da média das diferenças [[8]](#ref-8). O modelo do teste t para a média pressupõe
diferenças independentes e aproximadamente normais; no desenho pareado, ele é
aplicado à amostra única de diferenças [[20]](#ref-20).

Antes de interpretar o teste, examinar histograma, gráfico Q-Q e valores
atípicos das diferenças, sem remover observações por conveniência. Relatar
sempre média de \(d\), desvio-padrão, intervalo de confiança de 95%, estatística,
graus de liberdade e valor-p; a API do teste t pareado fornece também o intervalo
de confiança da diferença média [[8]](#ref-8). “Não rejeitar H0” não equivale a
provar igualdade [[19]](#ref-19).

Wilcoxon pode ser apresentado apenas como análise de sensibilidade
pré-especificada. Ele testa simetria da distribuição das diferenças em torno de
zero, pressupõe diferenças independentes e identicamente distribuídas e requer
decisões explícitas para zeros, empates e método de cálculo do valor-p
[[9]](#ref-9). Se Wilcoxon for transformado no teste primário, as hipóteses devem
ser reformuladas para o parâmetro que ele testa; não se deve manter uma hipótese
sobre médias e interpretar Wilcoxon como se a testasse.

Como há uma única métrica e um único teste confirmatório, não há multiplicidade
na análise primária. Acurácia, tempo, F1 por classe, Grad-CAM e qualquer teste
adicional são secundários/exploratórios. Se passarem a gerar várias hipóteses
confirmatórias, o protocolo deverá definir previamente uma correção de testes
múltiplos, como o procedimento sequencial de Holm [[18]](#ref-18).

### 6. Tempo de treinamento

Definir “tempo de treinamento” como o tempo de parede desde imediatamente antes
de `model.fit` até seu retorno, excluindo download, construção do modelo,
carregamento dos pesos e avaliação. `time.perf_counter()` usa o contador de maior
resolução disponível para medir durações curtas e somente diferenças entre
chamadas têm significado [[12]](#ref-12). Fazer uma execução de aquecimento não
incluída nos 30 pares e manter hardware, modo determinístico, cache/prefetch,
tamanho de lote e carga concorrente constantes.

Publicar tempo total, épocas efetivamente executadas e número de atualizações.
Se o número de épocas for fixo, o tempo compara custo para o mesmo orçamento; se
houver parada antecipada, compara o custo do procedimento completo, não apenas
velocidade por época. Não usar tempo para afirmar “convergência mais rápida” sem
definir previamente um limiar de desempenho e como tratar execuções que nunca o
alcançam.

### 7. Grad-CAM

Gerar Grad-CAM depois de congelar os checkpoints finais. Antes de observar os
resultados, fixar um dos 30 pares por sua seed e sortear uma imagem de teste por
classe. Usar as três entradas segmentadas sem aumento, a última camada
convolucional da MobileNetV2 e a classe predita como conceito-alvo. O artigo
original define Grad-CAM a partir dos gradientes do conceito-alvo que fluem para
a camada convolucional final [[11]](#ref-11), e o exemplo oficial da Keras
implementa essa construção com `GradientTape` e média espacial dos gradientes
[[13]](#ref-13).

O protocolo gera seis mapas, três por braço. Para cada caso, mostrar lado a lado
a imagem original, a entrada segmentada e o mapa sobreposto à entrada segmentada,
sempre com a mesma escala, mapa de cores e transparência. O mapa explica o que o
modelo recebeu, não o fundo da imagem original. Destaques na borda devem ser
tratados como possível efeito da segmentação. Sem máscara de lesão, anotação de
especialista ou métrica espacial, a análise permanece qualitativa e não sustenta
afirmar que uma explicação é “melhor”.

## Limitações aplicáveis à V1 e a campanhas futuras

- **Teste pequeno:** existem somente 128 imagens no split de teste oficial
  [[1]](#ref-1); publicar incerteza e resultados por classe, evitando conclusões
  amplas a partir de poucos erros.
- **Reuso do mesmo teste:** as 30 execuções reutilizam as mesmas imagens. Logo,
  a distribuição dos 30 F1 descreve principalmente a aleatoriedade do processo
  de treinamento condicionada a esse conjunto fixo; ela não incorpora 30 novas
  amostras de folhas. A dependência introduzida pelo reuso de dados é uma razão
  conhecida para testes ingênuos de comparação de classificadores produzirem
  inferências inadequadas [[16]](#ref-16).
- **Independência biológica inconclusiva:** a documentação informa coleta em
  campo por câmeras de smartphone e anotação por especialistas, mas não fornece
  identificadores de planta ou sessão para auditar separação por grupo
  [[2]](#ref-2). As conclusões devem ser restritas ao split fornecido.
- **Escopo do tratamento:** hiperparâmetros comuns isolam a inicialização sob um
  protocolo fixo, mas não comparam o melhor ajuste possível de cada abordagem.
- **Segmentação HSV:** a rubrica sem máscaras de referência fornece controle
  qualitativo, não uma medida objetiva de qualidade. Erros de silhueta e atenção
  do Grad-CAM às bordas devem acompanhar a interpretação dos resultados.
- **Trinta pares:** o requisito aumenta a observação da variabilidade entre
  treinamentos, porém não garante poder estatístico nem corrige as limitações do
  conjunto de teste.
- **Determinismo versus tempo:** o TensorFlow adverte que operações
  determinísticas podem reduzir o desempenho [[6]](#ref-6); por isso o mesmo
  modo deve ser mantido em todos os pares e declarado ao relatar tempo.
- **Grad-CAM:** sem referência espacial, sua leitura é qualitativa e não mede
  fidelidade clínica ou agronômica das regiões destacadas [[11]](#ref-11).

## Checklist para uma futura campanha

Os itens abaixo não são pendências para iniciar a V2 automaticamente. Eles são
requisitos a revisar somente quando uma nova campanha for autorizada.

- Fixar dataset `beans:0.1.0`, hashes/versões e contagens por classe.
- Ajustar o HSV em 30 imagens do treino, registrar a rubrica, congelar os
  parâmetros e materializar uma única versão segmentada de cada split.
- Pré-registrar o protocolo fim a fim que isola os pesos iniciais ou, em estudo
  separado, o fluxo em duas fases de fine-tuning.
- Fixar arquitetura, cabeça, inicializadores, pré-processamento, aumento,
  hiperparâmetros, orçamento, checkpoint e critério de falha.
- Determinar o número fixo de épocas em piloto de treino/validação e preservar
  configuração, regra de estabilização e resumo das curvas.
- Publicar previamente as 30 seeds e separar os fluxos de base, cabeça, dados,
  aumento e dropout, mantendo iguais os componentes comuns de cada par.
- Reservar validação para decisões e teste apenas para avaliação final.
- Definir F1 macro com três rótulos e política de divisão por zero.
- Definir teste t pareado bilateral como análise primária e Wilcoxon, se usado,
  apenas como sensibilidade com interpretação distinta.
- Definir exatamente o intervalo cronometrado e executar tudo no mesmo ambiente.
- Fixar um par, uma imagem por classe, classe predita, última camada
  convolucional e visualização do Grad-CAM antes de examinar mapas.
- Salvar configuração, versões, predições e métricas de cada execução; práticas
  de divulgação de código, dados e detalhes experimentais são centrais à
  reprodutibilidade em aprendizado de máquina [[14]](#ref-14).

## Referências primárias

1. <a id="ref-1"></a>TensorFlow Datasets. **Metadados oficiais do Beans
   0.1.0**. <https://storage.googleapis.com/tfds-data/dataset_info/beans/0.1.0/dataset_info.json>
2. <a id="ref-2"></a>TensorFlow Datasets. **Código-fonte oficial do construtor
   Beans**. <https://github.com/tensorflow/datasets/blob/master/tensorflow_datasets/datasets/beans/beans_dataset_builder.py>
3. <a id="ref-3"></a>Keras. **Código-fonte e API oficial da MobileNetV2 e de
   `preprocess_input`**. <https://github.com/keras-team/keras/blob/master/keras/src/applications/mobilenet_v2.py>
4. <a id="ref-4"></a>Keras. **Transfer learning & fine-tuning**.
   <https://keras.io/guides/transfer_learning/>
5. <a id="ref-5"></a>Keras. **`keras.utils.set_random_seed`**.
   <https://keras.io/api/utils/python_utils/#setrandomseed-function>
6. <a id="ref-6"></a>TensorFlow. **Código-fonte oficial de
   `enable_op_determinism`**.
   <https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/framework/config.py>
7. <a id="ref-7"></a>TensorFlow. **Código-fonte e documentação oficial de
   `tf.random.set_seed`**.
   <https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/framework/random_seed.py>
8. <a id="ref-8"></a>SciPy. **`scipy.stats.ttest_rel`**.
   <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_rel.html>
9. <a id="ref-9"></a>SciPy. **`scipy.stats.wilcoxon`**.
   <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html>
10. <a id="ref-10"></a>scikit-learn. **`sklearn.metrics.f1_score` e médias
    multiclasse**.
    <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html>
11. <a id="ref-11"></a>Selvaraju, R. R. et al. **Grad-CAM: Visual Explanations
    From Deep Networks via Gradient-Based Localization**. ICCV, 2017.
    <https://openaccess.thecvf.com/content_ICCV_2017/papers/Selvaraju_Grad-CAM_Visual_Explanations_ICCV_2017_paper.pdf>
12. <a id="ref-12"></a>Python Software Foundation. **`time.perf_counter`**.
    <https://docs.python.org/3/library/time.html#time.perf_counter>
13. <a id="ref-13"></a>Keras. **Exemplo oficial: Grad-CAM class activation
    visualization**. <https://keras.io/examples/vision/grad_cam/>
14. <a id="ref-14"></a>Pineau, J. et al. **Improving Reproducibility in Machine
    Learning Research: A Report from the NeurIPS 2019 Reproducibility
    Program**. JMLR 22(164), 2021.
    <https://www.jmlr.org/papers/v22/20-303.html>
15. <a id="ref-15"></a>scikit-learn. **Common pitfalls and recommended
    practices: data leakage**.
    <https://scikit-learn.org/stable/common_pitfalls.html#data-leakage>
16. <a id="ref-16"></a>Dietterich, T. G. **Approximate Statistical Tests for
    Comparing Supervised Classification Learning Algorithms**. Neural
    Computation 10(7), 1998. <https://doi.org/10.1162/089976698300017197>
17. <a id="ref-17"></a>Cohen, J. **A Power Primer**. Psychological Bulletin
    112(1), 1992. <https://doi.org/10.1037/0033-2909.112.1.155>
18. <a id="ref-18"></a>Holm, S. **A Simple Sequentially Rejective Multiple Test
    Procedure**. Scandinavian Journal of Statistics 6(2), 1979.
    <https://www.jstor.org/stable/4615733>
19. <a id="ref-19"></a>Wasserstein, R. L.; Lazar, N. A. **The ASA's Statement
    on p-Values: Context, Process, and Purpose**. The American Statistician
    70(2), 2016. <https://doi.org/10.1080/00031305.2016.1154108>
20. <a id="ref-20"></a>Student. **The Probable Error of a Mean**. Biometrika
    6(1), 1908. <https://doi.org/10.1093/biomet/6.1.1>
21. <a id="ref-21"></a>Keras. **Keras Applications: tabela de modelos**.
    <https://keras.io/api/applications/>
22. <a id="ref-22"></a>Sandler, M. et al. **MobileNetV2: Inverted Residuals
    and Linear Bottlenecks**. CVPR, 2018.
    <https://doi.org/10.48550/arXiv.1801.04381>
