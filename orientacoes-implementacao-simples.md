# Orientacoes para Implementacao Simples

Reavalie este ticket pelo menor escopo que atenda ao requisito. Remova
abstracoes, camadas e funcionalidades nao essenciais. Preserve apenas o
comportamento necessario e mantenha o fluxo facil de explicar.

Priorize codigo simples, direto e legivel. Nao adicione generalizacoes ou uma
arquitetura sofisticada sem uma necessidade concreta. Se uma solucao mais
simples atender ao requisito, escolha a solucao mais simples.

Adicione comentarios acima das funcoes relevantes explicando claramente a
responsabilidade de cada uma. Utilize docstrings para documentar a finalidade
da funcao, seus parametros, seu retorno e regras importantes. Funcoes privadas
pequenas nao precisam de documentacao propria. Os comentarios devem ajudar a
entender o codigo, sem apenas repetir o que a implementacao ja diz.

Organize o codigo dentro das funcoes com espacos e linhas em branco entre blocos
logicos. Evite funcoes muito densas, expressoes excessivamente compactas e
muitas operacoes na mesma linha. Prefira uma sequencia de passos explicita e
facil de acompanhar.

O codigo deve priorizar, nesta ordem:

1. Funcionar corretamente.
2. Respeitar o protocolo essencial do experimento.
3. Ser facil de ler.
4. Ser facil de verificar.
5. Ser facil de explicar ao professor.

Nao implemente funcionalidades apenas por antecipacao. Toda abstracao,
validacao, camada ou configuracao deve ter uma justificativa relacionada ao
requisito atual. O ambiente e controlado, portanto nao e necessario validar
todos os cenarios possiveis.
