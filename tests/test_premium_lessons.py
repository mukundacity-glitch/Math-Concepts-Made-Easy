from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
import subprocess

import pytest

from pipeline.curriculum import MASTER_CURRICULUM, get_lesson
from pipeline.lesson_plan import _choose_variant, HOOK_VARIANTS, OUTRO_VARIANTS, plan_lesson
from pipeline.narration import write_narrations
from pipeline.practice import split_practice
from pipeline.mathtext import latex_to_speech
from pipeline.remotion_render import scene_props
from pipeline.preview import build_preview
from pipeline.pause_audio import synthesize_with_pauses
from pipeline.visual_models import validate_visual
from pipeline.upload_receipts import receipt_for, save_receipt


def test_production_boundary_preserves_solution_rows():
    question, solution = split_practice(get_lesson(42)['board_examples'])
    assert len(question) == 1
    assert len(solution) == 1
    assert 'Note' in solution[0]
    assert split_practice({'practice':['A complete verification']}) == (['A complete verification'], [])
    assert split_practice({'practice_question':['Question?','Given values'],
                           'practice_solution':['Step one','Answer']}) == (['Question?','Given values'],['Step one','Answer'])


def test_every_authored_chapter_has_three_examples_and_six_practice_problems(tmp_path):
    authored = [lesson for lesson in MASTER_CURRICULUM if lesson.get('lesson_design')]
    assert {lesson['grade'] for lesson in authored} == {9,10,11,12}
    for lesson in authored:
        before = copy.deepcopy(lesson)
        plan = plan_lesson(lesson)
        design = plan['lesson_design']
        assert len(design['worked_examples']) >= 3
        assert len(design['practice_set']) >= 6
        blocks = write_narrations(lesson,'Next chapter','',plan)
        assert len(blocks['practice']['pauses']) == len(design['practice_set'])
        assert lesson == before
        script = build_preview(lesson['day'],tmp_path/str(lesson['day']))
        json.dumps(script,allow_nan=False)
        assert (tmp_path/str(lesson['day'])/'worked_example.json').is_file()
        for scene in script['scenes']:
            props=scene_props(script,scene)
            for panel,rendered in zip(scene['panels'],props['panels']):
                for line,statement,start in zip(panel['lines'],panel['line_sentences'],rendered['lineStarts']):
                    assert start == scene['statement_timing'][statement]['start']
                    if not panel.get('pause_after'):
                        assert scene['narration_beats'][statement] == latex_to_speech(line)


def test_exact_objects_are_data_driven():
    design = get_lesson(131)['lesson_design']
    assert design['worked_examples'][0]['visual']['values'] == [3]
    assert design['worked_examples'][1]['visual']['values'] == [4]
    for count in range(1,25):
        assert validate_visual({'model':'countable_objects','values':[count]})['values'] == [count]
    with pytest.raises(ValueError):
        validate_visual({'model':'countable_objects','values':[3.5]})
    with pytest.raises(ValueError):
        validate_visual({'model':'countable_objects','values':[3],'remove':4})


def test_five_published_lesson_rotation_and_empty_options():
    for choices in (HOOK_VARIANTS,OUTRO_VARIANTS):
        assert _choose_variant(choices,list(choices[:5]),42) not in choices[:5]
    with pytest.raises(ValueError):
        _choose_variant((),[],1)


def test_graph_data_matches_the_authored_function():
    design = get_lesson(42)['lesson_design']
    series = design['worked_examples'][2]['visual']['points']
    for x,y in series[0]:
        assert y == pytest.approx((x+3)**2,abs=0.001)
    for x,y in series[1]:
        assert y == pytest.approx(x*x+3,abs=0.001)


def test_pause_is_real_audio_and_answer_words_follow_it(tmp_path):
    scene={'narration_beats':['Question now.','Answer later.'],
           'pauses':[{'after_sentence':1,'seconds':1.0}]}
    async def synthesize(text,audio,words):
        subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
                        'sine=frequency=440:sample_rate=24000','-t','0.3',str(audio)],check=True)
        words.write_text(json.dumps([{'word':text,'start':0,'end':0.25}]))
        return True
    async def measure(path):
        result=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                               '-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,check=True)
        return float(result.stdout)
    audio,words=tmp_path/'scene.mp3',tmp_path/'words.json'
    assert asyncio.run(synthesize_with_pauses(scene,audio,words,synthesize,measure))
    gap=scene['pause_timing'][0]
    assert gap['seconds'] >= 1.0
    boundaries=json.loads(words.read_text())
    assert boundaries[1]['start'] >= gap['start']+gap['seconds']
    assert asyncio.run(measure(audio)) >= 1.6


def test_upload_receipts_survive_partial_package_retry(tmp_path):
    path=tmp_path/'receipts.json'
    assert receipt_for(42,'main',path) is None
    save_receipt(42,'main','confirmed-main-id',path)
    save_receipt(42,'HOOK','confirmed-short-id',path)
    assert receipt_for(42,'main',path) == 'confirmed-main-id'
    assert receipt_for(42,'HOOK',path) == 'confirmed-short-id'
    assert receipt_for(42,'FORMULA',path) is None
