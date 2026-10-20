# Campanhas reproduzíveis e análise estatística

## Decisão

Campanhas novas são executadas em uma pasta própria sob `artifacts/campaigns/`.
A preparação segmentada pode ser compartilhada quando sua pasta já existe, mas
as saídas de treinamento, Grad-CAM e análise não são sobrescritas.

O fluxo completo é:

```text
prepare -> experiment -> gradcam -> analyze
```

O `prepare` reutiliza uma pasta existente em ambiente controlado. Cada ramo
registra a identidade do checkpoint e seu SHA-256. O Grad-CAM valida essa
referência antes de ler os pesos.

## Análise estatística

As diferenças são calculadas por seed como:

```text
solução principal - solução contrafactual
```

A normalidade é avaliada nas diferenças pareadas, separadamente para macro-F1 e
acurácia, com Shapiro-Wilk e `alpha=0.05`. Se a normalidade for compatível, é
usado o teste t pareado. Caso contrário, é usado Wilcoxon signed-rank, com o
método e o tratamento de zeros/empates registrados no resumo.

## Grad-CAM

As novas campanhas mantêm probabilidades softmax para a classificação, mas usam
o logit pré-softmax da classe predita como escore do Grad-CAM. As campanhas
históricas não são regravadas.
