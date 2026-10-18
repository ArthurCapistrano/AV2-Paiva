PYTHON := uv run
CONFIG := protocol.json
SEGMENTED := artifacts/v1/segmented
OUTPUT := artifacts/v2
SUMMARY := $(OUTPUT)/summary.json

.PHONY: help prepare experiment analyze gradcam all

# Mostra os comandos disponíveis para executar o experimento.
# Exemplo: make help
help:
	@printf '%s\n' \
		'make prepare    prepara as entradas segmentadas' \
		'make experiment executa os 30 pares experimentais' \
		'make analyze    calcula e apresenta os resultados' \
		'make gradcam    gera os mapas Grad-CAM dos exemplos fixos' \
		'make all        executa treinamento e análise'

# Prepara uma coleção fixa de entradas segmentadas compartilhadas pelos modelos.
# Exemplo: make prepare
prepare:
	$(PYTHON) experimento-feijao prepare \
		--config $(CONFIG) \
		--output $(SEGMENTED)

# Executa os dois modelos para todas as 30 seeds definidas no protocolo V2.
# Exemplo: make experiment
experiment:
	$(PYTHON) experimento-feijao experiment \
		--config $(CONFIG) \
		--segmented-inputs $(SEGMENTED) \
		--output $(OUTPUT)

# Calcula e apresenta as métricas e a análise estatística dos pares V2.
# Exemplo: make analyze
analyze:
	$(PYTHON) experimento-feijao analyze \
		--results $(OUTPUT) \
		--output $(SUMMARY)

# Gera os mapas dos três exemplos fixos para os 30 pares V2.
# Exemplo: make gradcam
gradcam:
	$(PYTHON) experimento-feijao gradcam \
		--config $(CONFIG) \
		--segmented-inputs $(SEGMENTED) \
		--output $(OUTPUT)

# Executa preparação, experimento e análise na ordem correta.
# Exemplo: make all
all: prepare experiment analyze
