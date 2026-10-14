# Prompts para `to-spec` e `to-tickets`

## Prompt para `/to-spec`

```text
Use todo o contexto já discutido nesta conversa para criar e publicar uma nova especificação simplificada do experimento.

A especificação antiga está em:
.scratch/experimento-classificacao-feijao/spec.md

Ela deve ser preservada como histórico. Não sobrescreva a especificação antiga nem altere os tickets antigos já implementados.

Publique a nova especificação em uma nova iniciativa, preferencialmente:
.scratch/experimento-classificacao-feijao-simples/

O objetivo é refatorar o código existente, não reimplementar o projeto do zero.

A nova especificação deve refletir estas decisões:

- O trabalho deve ser simples, legível, funcional e fácil de explicar.
- A hipótese central continua sendo comparar MobileNetV2 com inicialização ImageNet contra inicialização aleatória.
- Devemos manter as 30 seeds e o protocolo estatístico pareado.
- Devemos calcular somente os resultados necessários: seed, F1 macro, acurácia e resultados agregados.
- Devemos manter média, desvio-padrão, diferenças, teste t pareado bilateral e valor-p.
- Grad-CAM fica fora do escopo principal.
- A preparação dos dados deve ter um único fluxo fixo e simples.
- Os estados adjustment e epoch_pilot devem ser removidos ou simplificados.
- O ambiente é controlado. Não são necessárias validações detalhadas de GPU, CUDA, sistema operacional, pacotes, nomes de GPU, JSONs malformados ou outros cenários defensivos.
- Não precisamos manter manifests extensos, hashes, probabilidades, históricos, checkpoints permanentes, retries ou auditoria detalhada.
- A configuração deve ser simples e declarada diretamente.
- A divisão desejada é:
  - preparation.py para preparar os dados;
  - experiment.py para executar um par de modelos;
  - analysis.py para consolidar as 30 execuções e calcular as estatísticas;
  - cli.py para receber parâmetros e chamar as etapas.
- Não devemos criar abstrações ou camadas sem necessidade concreta.
- Funções relevantes devem ter docstrings e comentários explicando regras não óbvias.
- Funções privadas pequenas não precisam de documentação própria.
- O código deve ter espaços e linhas em branco entre blocos lógicos.
- Não vamos criar uma nova suíte de testes. A verificação será manual em ambiente controlado.
- Os testes existentes não devem ser tratados como contrato obrigatório quando protegerem funcionalidades que serão removidas.

A especificação deve incluir claramente o que será preservado, o que será removido, os módulos envolvidos, o fluxo mínimo completo, os resultados esperados e tudo que ficará fora do escopo.

Não implemente código. Apenas crie e publique a nova especificação com status ready-for-agent.
```

## Prompt para `/to-tickets`

```text
Leia a nova especificação em:

.scratch/experimento-classificacao-feijao-simples/spec.md

Considere também o código existente no repositório. Os tickets antigos da iniciativa experimento-classificacao-feijao devem ser preservados como histórico. Não altere nem sobrescreva os tickets antigos.

Crie uma nova sequência de tickets para refatorar e simplificar o código existente. Os tickets não devem reimplementar o projeto do zero.

A sequência desejada é:

1. Simplificar a configuração e a CLI existentes.
2. Simplificar a preparação fixa dos dados.
3. Simplificar a execução de um par comparável de modelos.
4. Executar os dois modelos nas 30 seeds de forma simples.
5. Consolidar os resultados e calcular a análise estatística.
6. Apresentar os resultados mínimos do experimento.

Regras para os tickets:

- Cada ticket deve entregar um comportamento verificável.
- Os tickets devem declarar seus bloqueios.
- Os tickets devem ser ordenados pelos bloqueios.
- O primeiro ticket deve trabalhar sobre o código existente e remover complexidade desnecessária.
- Não criar ticket para Grad-CAM.
- Não criar ticket para uma nova suíte de testes.
- A verificação deve ser manual e ocorrer em ambiente controlado.
- Não criar tickets para validações de GPU, CUDA, sistema operacional, pacotes, nomes de GPU, JSONs malformados ou outros cenários defensivos.
- Não criar tickets para manifests extensos, hashes, probabilidades, históricos, checkpoints permanentes, retries ou auditoria detalhada.
- Preservar apenas as garantias essenciais do experimento:
  - mesmas entradas para os dois modelos;
  - mesma configuração de treinamento;
  - diferença apenas entre pesos ImageNet e pesos aleatórios;
  - 30 seeds pareadas;
  - F1 macro e acurácia;
  - média, desvio-padrão, teste t pareado bilateral e valor-p.
- Usar poucas funções e módulos com responsabilidades claras.
- Evitar tickets horizontais que apenas criem camadas técnicas sem entregar um fluxo verificável.

Publique os tickets na nova iniciativa:

.scratch/experimento-classificacao-feijao-simples/issues/

Antes de publicar, apresente a lista de tickets com título, bloqueios e comportamento entregue para aprovação. Não implemente código.
```
