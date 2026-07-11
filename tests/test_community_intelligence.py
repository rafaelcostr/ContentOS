from contentos_intelligence.application.community_intelligence import build_community_intelligence_report


def test_community_intelligence_generates_strategic_outputs() -> None:
    report = build_community_intelligence_report(
        project_id="project-1",
        comment_insights=[
            {
                "comment_count": 8,
                "themes": ["gta", "mapa"],
                "sample_comments": [
                    "Quando sai a parte 2 do mapa?",
                    "Não entendi esse detalhe do trailer",
                    "Isso parece fake e clickbait",
                ],
            }
        ],
        community_drafts=[
            {
                "category": "question",
                "original_comment": "Faz um vídeo explicando os carros?",
                "priority": 90,
            }
        ],
    )

    data = report.to_dict()

    assert data["status"] == "ready"
    assert data["faq"]
    assert data["pains"]
    assert data["objections"]
    assert data["requests"]
    assert data["video_ideas"]
    assert data["campaign_ideas"]
    assert data["audience_updates"]
    assert data["calendar_influence"]
    assert data["objective_influence"]


def test_community_intelligence_keeps_reply_guardrails() -> None:
    report = build_community_intelligence_report(project_id="project-1")

    assert report.status == "learning"
    assert any("Não responder automaticamente" in item for item in report.reply_guardrails)
    assert any("aprovação humana" in item for item in report.reply_guardrails)
