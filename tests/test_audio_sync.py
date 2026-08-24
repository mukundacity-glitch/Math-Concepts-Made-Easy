from pipeline.audio_sync import apply_word_timing


def test_word_timing_maps_statements_and_actions():
    scene = {
        "narration": "First idea. Second idea.",
        "narration_beats": ["First idea.", "Second idea."],
        "duration_seconds": 2.0,
        "actions": [
            {"narration_sentence_index": 0},
            {"narration_sentence_index": 1},
        ],
    }
    words = [
        {"word": "First", "start": 0.0, "end": 0.4},
        {"word": "idea", "start": 0.4, "end": 0.8},
        {"word": "Second", "start": 1.0, "end": 1.4},
        {"word": "idea", "start": 1.4, "end": 1.8},
    ]
    apply_word_timing(scene, words)
    assert scene["statement_timing"][0] == {
        "sentence_index": 0, "start": 0.0, "end": 0.8,
    }
    assert scene["actions"][1]["start_seconds"] == 1.0
