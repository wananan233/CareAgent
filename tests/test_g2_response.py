from carehub.g2 import ResponseEngine

def test_response_template_requires_sources_and_blocks_medical_claims():
    engine=ResponseEngine()
    blocked=engine.render(agent_run_id="run-1",channel="TTS",template="您已服药。",facts=[{"text":"x","source_refs":["evt"]}])
    missing=engine.render(agent_run_id="run-2",channel="TERMINAL",template="正常提醒。",facts=[])
    assert blocked["fallback"]=="TEMPLATE_FALLBACK"
    assert missing["fallback"]=="TEMPLATE_FALLBACK"
