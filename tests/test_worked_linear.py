"""Operation-level regressions: a correct final answer cannot hide bad working."""
import json
from pathlib import Path

import pytest

from pipeline.cinematic_content import build_cinematic_plan
from pipeline.cinematic_lesson import preview_props
from pipeline.worked_linear import affine, validate_lesson

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def lesson():
    return json.loads((ROOT / 'examples/elimination_lesson.json').read_text())


def test_example_compiles_through_existing_cinematic_entry(lesson):
    validate_lesson(lesson)
    plan = build_cinematic_plan(lesson)
    chapter = plan['chapters'][0]
    assert plan['schemaVersion'] == 'cinematic-v1'
    assert len(chapter['board']) == 8
    assert len(chapter['beats']) == 12
    assert next(b for b in chapter['beats'] if b['id'] == 'pause')['holdSeconds'] == 6
    assert 'two x equals eight' in next(b for b in chapter['beats'] if b['id'] == 'add')['speech']
    assert {n['id'] for r in chapter['board'] for n in r['nodes'] if 'highlight' in n} == {'first-plus-y', 'second-minus-y'}
    assert all({'first', 'second'} <= set(s['rowIds']) for s in chapter['boardStates'][1:])


@pytest.mark.parametrize('row_id,term_id,bad', [('sum', 'sum-eight', '9'), ('solve-x', 'solve-x-four', '5'),
    ('substitute', 'substitute-four', '5'), ('solve-y', 'solve-y-three', '2'),
    ('check-first', 'check-first-seven', '8'), ('check-second', 'check-second-one', '2')])
def test_incorrect_intermediate_rejected_with_final_answer_unchanged(lesson, row_id, term_id, bad):
    row = next(r for r in lesson['rows'] if r['id'] == row_id)
    next(t for t in row['nodes'] if t['id'] == term_id)['text'] = bad
    with pytest.raises(ValueError, match='intermediate|evidence|substitution'):
        validate_lesson(lesson)


def test_division_zero_and_wrong_factor_rejected(lesson):
    op = next(b for b in lesson['beats'] if b['id'] == 'divide')['operation']
    for divisor in [0, 3]:
        op['divisor'] = divisor
        with pytest.raises(ValueError, match='zero|intermediate'):
            validate_lesson(lesson)


def test_substitution_needs_evidence_and_both_checks(lesson):
    beat = next(b for b in lesson['beats'] if b['id'] == 'substitute')
    beat['operation']['evidence'] = []
    with pytest.raises(ValueError, match='evidence'):
        validate_lesson(lesson)
    beat['operation']['evidence'] = ['solve-x']
    lesson['beats'] = [b for b in lesson['beats'] if b['id'] != 'check-second']
    with pytest.raises(ValueError):
        validate_lesson(lesson)


def test_final_pair_is_checked_against_originals(lesson):
    lesson['beats'][-1]['operation']['values']['y'] = 4
    with pytest.raises(ValueError, match='Final pair'):
        validate_lesson(lesson)


@pytest.mark.parametrize('mutation', ['source', 'highlight', 'retention', 'cue', 'operation', 'duplicate', 'missing-cue', 'asset-id'])
def test_bad_teaching_contract_fails_closed(lesson, mutation):
    beat = next(b for b in lesson['beats'] if b['id'] == 'add')
    if mutation == 'missing-cue': beat['cuePhrase'] = 'absent phrase'
    elif mutation == 'asset-id': beat['id'] = '../unsafe'
    elif mutation == 'source': beat['sources'][0] = 'missing'
    elif mutation == 'highlight': beat['highlights'] = ['not-a-term']
    elif mutation == 'retention': beat['retain'] = ['sum']
    elif mutation == 'cue': beat['narration'] = 'The answer appears without a spoken equation.'
    elif mutation == 'operation': beat['operation']['kind'] = 'invent_result'
    elif mutation == 'duplicate': lesson['rows'][0]['nodes'][0]['id'] = 'sum-eight'
    with pytest.raises(ValueError):
        validate_lesson(lesson)


def test_cancellation_requires_opposite_terms_from_different_sources(lesson):
    beat = next(b for b in lesson['beats'] if b['id'] == 'add')
    beat['operation']['cancelTerms'] = ['first-x', 'second-x']
    with pytest.raises(ValueError, match='opposite'):
        validate_lesson(lesson)


@pytest.mark.parametrize('expression', ['x*y', '__import__("os")', 'x/0', 'z+1', '2**10000', '1e300', 'True'])
def test_parser_rejects_unsafe_and_nonlinear_input(expression):
    with pytest.raises(ValueError):
        affine(expression)


def test_checked_in_preview_is_reproducible(lesson):
    assert preview_props(build_cinematic_plan(lesson)) == json.loads(
        (ROOT / 'remotion/src/cinematic/elimination-preview.json').read_text())
