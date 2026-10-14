PYTHON := uv run
CONFIG := protocol.json
SEGMENTED := artifacts/segmented
RESULTS := artifacts/results
SUMMARY := artifacts/summary.json

.PHONY: help prepare experiment analyze all

# Mostra os comandos disponíveis para executar o experimento.
# Exemplo: make help
help:
	@printf '%s\n' \
		'make prepare    prepara as entradas segmentadas' \
		'make experiment executa os 30 pares experimentais' \
		'make analyze    calcula e apresenta os resultados' \
		'make all        executa o fluxo completo'

# Prepara uma coleção fixa de entradas segmentadas compartilhadas pelos modelos.
# Exemplo: make prepare
prepare:
	$(PYTHON) experimento-feijao prepare \
		--config $(CONFIG) \
		--output $(SEGMENTED)

# Executa os dois modelos para todas as 30 seeds definidas no protocolo.
# Exemplo: make experiment
experiment:
	$(PYTHON) experimento-feijao experiment \
		--config $(CONFIG) \
		--segmented-inputs $(SEGMENTED) \
		--output $(RESULTS)

# Calcula e apresenta as métricas e a análise estatística dos pares.
# Exemplo: make analyze
analyze:
	$(PYTHON) experimento-feijao analyze \
		--results $(RESULTS) \
		--output $(SUMMARY)

# Executa preparação, experimento e análise na ordem correta.
# Exemplo: make all
all: prepare experiment analyze
