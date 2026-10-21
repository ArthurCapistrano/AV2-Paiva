from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "artifacts" / "v3"
ACTIVE_DOCS = (
    ROOT / "README.md",
    ROOT / "docs" / "RESULTADOS-V3.md",
    ROOT / "docs" / "VALIDACAO-METODOLOGIA.md",
    ROOT / "docs" / "ORGANIZACAO-TRABALHO.md",
    ROOT / "docs" / "GUIA-ARTIGO.md",
    ROOT / "docs" / "GUIA-ENTENDIMENTO-PROJETO.md",
    ROOT / "docs" / "INDICE-EVIDENCIAS.md",
)


def test_v3_publishes_all_compact_evidence_without_checkpoints():
    manifest = json.loads((V3 / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((V3 / "summary.json").read_text(encoding="utf-8"))

    assert manifest["campaign_id"] == "campaign-bn-final"
    assert manifest["seeds"] == list(range(1001, 1031))
    assert manifest["batch_normalization_momentum"] == 0.9
    assert summary["pair_count"] == 30
    assert not (V3 / "checkpoints").exists()

    pair_results = sorted((V3 / "results").glob("pair-*/result.json"))
    branch_results = sorted((V3 / "results").glob("pair-*/solucao_*/result.json"))
    diagnostics = sorted((V3 / "gradcam").glob("pair-*/solucao_*/diagnostic.json"))
    panels = sorted((V3 / "gradcam").glob("pair-*/solucao_*/*.png"))

    assert len(pair_results) == 30
    assert len(branch_results) == 60
    assert len(diagnostics) == 60
    assert len(panels) == 180


def test_v3_summary_contains_the_published_results():
    summary = json.loads((V3 / "summary.json").read_text(encoding="utf-8"))

    assert summary["metrics"]["macro_f1"]["solucao_principal"]["mean"] == 0.8375445283950272
    assert summary["metrics"]["macro_f1"]["solucao_contrafactual"]["mean"] == 0.587953128957529
    assert summary["paired_macro_f1_difference"]["test"]["p_value"] == 8.652052380838855e-26


def test_active_documentation_uses_v3_as_the_primary_reference():
    for path in ACTIVE_DOCS:
        content = path.read_text(encoding="utf-8")
        assert "artifacts/v3" in content

    assert (ROOT / "docs" / "HISTORICO-V2" / "RESULTADOS.md").is_file()
    assert (ROOT / "docs" / "HISTORICO-V2" / "ESPECIFICACAO.md").is_file()
