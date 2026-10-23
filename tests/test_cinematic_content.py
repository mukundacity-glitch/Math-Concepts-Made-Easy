from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.cinematic_content import (
    attach_verified_cancellation, build_cinematic_plan, equation_steps, graph_model,
    make_math_beat, math_display, node_width, readable_steps,
)
from pipeline.curriculum import get_lesson, MASTER_CURRICULUM


def atoms(nodes):
    for node in nodes:
        if 'text' in node: yield node
        elif 'cells' in node:
            for row in node['cells']:
                for cell in row: yield from atoms(cell)
        else:
            yield from atoms(node['top']); yield from atoms(node['bottom'])


def test_every_remaining_lesson_has_readable_source_driven_working_and_spoken_cues():
    for lesson in MASTER_CURRICULUM:
        if lesson['day'] < 44: continue
        plan = build_cinematic_plan(lesson)
        assert len(plan['chapters']) >= 7
        for chapter in plan['chapters']:
            identifiers = {beat['id'] for beat in chapter['beats']}
            for row in chapter['board']:
                assert node_width(row['nodes']) <= (1680 if row['wide'] else 1090) / 64
                for atom in atoms(row['nodes']):
                    assert atom['cue']['beat'] in identifiers
                    assert any(character.isalnum() for character in atom['cue']['phrase']), (lesson['day'], atom)


def test_independent_rules_are_not_rewritten_as_an_equality_chain():
    rules = equation_steps(get_lesson(44)['key_formula'])
    assert len(rules) == 2
    assert rules[0].startswith('Even:') and rules[1].startswith('Odd:')
    assert rules[0].count('=') == 1 and rules[1].count('=') == 1
    assert equation_steps('x=2+3=5') == ['x = 2+3', '= 5']


def test_repeated_variables_use_occurrences_in_the_entire_spoken_expression():
    beat, row = make_math_beat('test', 'algebra', 'f(x) = x + x', 'Substitute')
    variables = [atom for atom in atoms(row['nodes']) if atom['text'] == 'x']
    assert [atom['cue']['occurrence'] for atom in variables] == [1, 2]
    assert beat['speech'] == 'f of x equals x plus x.'


def test_cancellation_requires_an_equivalent_state_and_the_correct_structural_terms():
    _, previous = make_math_beat('before', 'algebra', 'y = x + 7 - 7', 'Balance')
    _, current = make_math_beat('after', 'algebra', 'y = x', 'Simplify')
    cue = attach_verified_cancellation(previous, current, 'x+7-7', 'x', 'cancel', 'algebra')
    assert cue and cue['speech'] == 'The opposite terms cancel.'
    targets = [atom for atom in atoms(previous['nodes']) if 'cancel' in atom]
    assert len(targets) == 2 and all(atom['text'] == '7' for atom in targets)
    _, unsafe = make_math_beat('unsafe', 'algebra', '(x+7)/7', 'Check factors')
    assert attach_verified_cancellation(unsafe, current, '(x+7)/7', 'x', 'bad', 'algebra') is None
    _, factor = make_math_beat('factor', 'algebra', '7x/7', 'Common factor')
    assert attach_verified_cancellation(factor, current, '7x/7', 'x', 'good', 'algebra')
    assert sum('cancel' in atom for atom in atoms(factor['nodes'])) == 2


def test_matrices_keep_actual_rows_columns_and_numeric_cell_cues():
    plain = math_display(r'\begin{pmatrix}1&2\\3&4\end{pmatrix}')
    assert plain == '⎡1,2;3,4⎤'
    beat, row = make_math_beat('matrix', 'algebra', plain, 'Read the matrix')
    matrix = row['nodes'][0]
    assert len(matrix['cells']) == 2 and all(len(cells) == 2 for cells in matrix['cells'])
    assert [atom['text'] for atom in atoms(row['nodes'])] == ['1','2','3','4']
    assert 'begin' not in beat['speech']


def test_graph_coordinates_are_computed_from_the_curriculum_and_unsafe_syntax_is_rejected():
    model = graph_model('f(x)=x^4-2x^2')
    assert model and model['samples'] == [{'x': -1, 'y': -1.0}, {'x': 0, 'y': 0.0}, {'x': 1, 'y': -1.0}]
    assert graph_model("f(x)=__import__('os')") is None
    reciprocal = graph_model('f(x)=1/x')
    assert reciprocal and None in reciprocal['points']


def test_next_day_includes_an_exact_neither_counterexample_and_independent_practice():
    plan = build_cinematic_plan(get_lesson(44))
    domain = next(chapter for chapter in plan['chapters'] if chapter['id'] == 'domain')
    assert any('neither even nor odd' in beat['speech'].lower() for beat in domain['beats'])
    pause = next(beat for chapter in plan['chapters'] for beat in chapter['beats'] if beat['id'].endswith('pause'))
    assert pause['holdSeconds'] == 6
    assert plan['chapters'][-2]['diagram']['samples'][-1] == {'x': 1, 'y': 2.0}


def test_scheduled_path_and_upload_gate_use_the_new_renderer_without_advancing_uploaded_days():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / '.github/workflows/daily-video.yml').read_text()
    assert '--no-advance --cinematic' in workflow
    assert 'MCME_REQUIRE_CINEMATIC: "1"' in workflow
    assert 'MCME_REQUIRE_CINEMATIC: "1"' in (root / '.github/workflows/publish-video.yml').read_text()
    from autopilot import production_stages
    assert production_stages(False)[1][1] == 'pipeline.cinematic_lesson'
    assert 'Advance progress only after upload succeeds' in workflow
    assert 'cron: "0 10 * * *"' in workflow and 'cron: "0 11 * * *"' in workflow


def test_stale_or_partial_cinematic_receipts_cannot_pass_the_publish_gate(tmp_path, monkeypatch):
    import hashlib
    from pipeline import media_gate
    monkeypatch.setattr(media_gate, 'BASE_DIR', tmp_path)
    directory = tmp_path / 'final_videos'
    directory.mkdir()
    video = directory / 'Day_044.mp4'
    video.write_bytes(b'verified-encoded-video')
    receipt = {'format': 'cinematic-v1', 'day': 44,
               'videoSha256': hashlib.sha256(video.read_bytes()).hexdigest(),
               'narrationBeats': 30, 'verifiedNarrationBeats': 30, 'width': 1920, 'height': 1080,
               'minimumLabelSize': 42, 'unreadableFallbackAllowed': False}
    path = directory / 'Day_044_cinematic-qa.json'
    path.write_text(json.dumps(receipt))
    media_gate.validate_cinematic_receipt(44, video)
    for change in [{'verifiedNarrationBeats': 29}, {'minimumLabelSize': 23}, {'unreadableFallbackAllowed': True}, {'day': 43}]:
        path.write_text(json.dumps({**receipt, **change}))
        with pytest.raises(ValueError): media_gate.validate_cinematic_receipt(44, video)
    path.write_text(json.dumps(receipt))
    video.write_bytes(b'an-older-or-different-render')
    with pytest.raises(ValueError): media_gate.validate_cinematic_receipt(44, video)
