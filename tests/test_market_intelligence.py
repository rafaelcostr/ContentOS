from contentos_autopilot.market import build_market_intelligence_report


def test_market_intelligence_ranks_strategy_and_competitor_opportunity() -> None:
    report = build_market_intelligence_report(
        project_id="project-1",
        strategy={
            "positioning": "Referencia em GTA 6",
            "goals": ["10 detalhes escondidos do GTA 6", "Aumentar retencao"],
        },
        calendar=[{"title": "GTA 6 mapa completo", "status": "planned"}],
        competitors=[
            {
                "handle": "@rival",
                "display_name": "Rival GTA",
                "metrics": {
                    "analysis": {
                        "patterns": {
                            "top_hooks": ["GTA 6 mapa secreto"],
                            "hashtags": ["#gta6"],
                        }
                    }
                },
            }
        ],
        channel_twin={
            "identity": {"niche": "games"},
            "brand_dna": {"content_patterns": {"top_hooks": ["Ninguem percebeu isso"]}},
        },
    )

    assert report.status == "ready"
    assert report.opportunities
    assert report.opportunities[0].score >= 55
    assert any(signal.source in {"strategy", "memory", "competitor"} for signal in report.opportunities[0].signals)
    assert report.saturation


def test_market_intelligence_works_without_external_sources() -> None:
    report = build_market_intelligence_report(project_id="project-1")

    assert report.project_id == "project-1"
    assert report.opportunities
    assert report.opportunities[0].topic == "Mapear tendências do nicho"
    assert report.opportunities[0].trend_brief["sources"]
