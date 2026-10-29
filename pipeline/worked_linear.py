"""Opt-in exact linear worked examples compiled to the existing cinematic contract.

No curriculum/state writes, renderer or publisher live here. Expressions are
bounded affine ASTs; each declared operation is checked on both equation sides.
"""
from __future__ import annotations

import ast
import math
import re
from copy import deepcopy
from fractions import Fraction


def affine(text: str) -> tuple[Fraction, Fraction, Fraction]:
    """Coefficients of x, y and 1; no eval or unrestricted symbolic parsing."""
    if not isinstance(text, str) or len(text) > 120:
        raise ValueError('Invalid linear expression')
    text = re.sub(r'(\d)([xy])', r'\1*\2', text)
    try:
        tree = ast.parse(text, mode='eval')
    except SyntaxError as error:
        raise ValueError('Invalid linear expression') from error
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError('Linear expression too complex')

    def walk(node):
        if isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value) <= 1000000:
            return (Fraction(0), Fraction(0), Fraction(node.value))
        if isinstance(node, ast.Name) and node.id in ('x', 'y'):
            return (Fraction(node.id == 'x'), Fraction(node.id == 'y'), Fraction(0))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return tuple(value * (-1 if isinstance(node.op, ast.USub) else 1) for value in walk(node.operand))
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                return tuple(a + (-b if isinstance(node.op, ast.Sub) else b) for a, b in zip(left, right))
            if isinstance(node.op, ast.Mult) and (not any(left[:2]) or not any(right[:2])):
                vector, scalar = (right, left[2]) if not any(left[:2]) else (left, right[2])
                return tuple(value * scalar for value in vector)
            if isinstance(node.op, ast.Div) and not any(right[:2]) and right[2]:
                return tuple(value / right[2] for value in left)
        raise ValueError('Only bounded affine arithmetic in x and y is supported')

    return walk(tree.body)


def equation(row: dict):
    text = ''.join(node['text'] for node in row['nodes'])
    if text.count('=') != 1:
        raise ValueError('Each result must be an equation')
    return tuple(affine(side) for side in text.split('='))


def scalar(value):
    if type(value) is not int or abs(value) > 1000000:
        raise ValueError('Expected bounded integer')
    return Fraction(value)


def substitute(eq, values):
    if not values or not set(values) <= {'x', 'y'}:
        raise ValueError('Invalid substitution variables')
    values = {key: scalar(value) for key, value in values.items()}
    return tuple((Fraction(0) if 'x' in values else x,
                  Fraction(0) if 'y' in values else y,
                  constant + x * values.get('x', 0) + y * values.get('y', 0))
                 for x, y, constant in eq)


def validate_lesson(lesson: dict) -> None:
    if lesson.get('schemaVersion') != 'worked-linear-v1':
        raise ValueError('Unsupported worked lesson contract')
    if type(lesson.get('day')) is not int or lesson['day'] < 1 or not lesson.get('title', '').strip():
        raise ValueError('Invalid worked lesson identity')
    rows = {}
    terms = {}
    for row in lesson['rows']:
        if row['id'] in rows or row['id'] in terms:
            raise ValueError('Duplicate object ID')
        rows[row['id']] = row
        for term in row['nodes']:
            if term['id'] in terms or term['id'] in rows:
                raise ValueError('Duplicate object ID')
            terms[term['id']] = (row['id'], affine(term['text']) if term['text'] not in ('=', '+', '-') else None)
        equation(row)
    if set(rows) & set(terms):
        raise ValueError('Duplicate object ID')
    if len(lesson['pinnedRows']) != 2 or not set(lesson['pinnedRows']) <= rows.keys():
        raise ValueError('Two original equations must be pinned')
    known, beat_ids, verified, givens = set(), set(), set(), set()
    for beat in lesson['beats']:
        if not re.fullmatch(r'[a-z0-9-]{1,64}', beat['id']):
            raise ValueError('Invalid beat asset ID')
        if beat['id'] in beat_ids:
            raise ValueError('Duplicate beat ID')
        beat_ids.add(beat['id'])
        for field in ('purpose', 'narration', 'reason'):
            if not isinstance(beat.get(field), str) or not beat[field].strip():
                raise ValueError('Missing teaching ' + field)
        phrase = beat.get('cuePhrase', '')
        normalize = lambda text: re.sub(r'[^\w\s]', '', text.lower()).split()
        spoken, target = normalize(beat['narration'].replace('{result}', '')), normalize(phrase)
        if not target or not any(spoken[i:i+len(target)] == target for i in range(len(spoken))):
            raise ValueError('Missing narration cue')
        if len(beat['reason']) > 88:
            raise ValueError('Split a crowded teaching reason')
        pause = beat['readingPauseSeconds']
        if type(pause) not in (int, float) or not math.isfinite(pause) or not 0 <= pause <= 15:
            raise ValueError('Invalid reading pause')
        sources, results, retained = beat['sources'], beat['results'], beat['retain']
        if not set(sources) <= known or not set(results) <= rows.keys() or set(results) & known:
            raise ValueError('Unknown, premature or repeated object reference')
        if len(results) > 1 or len(set(results)) != len(results):
            raise ValueError('Split a crowded teaching beat')
        if bool(results) != ('{result}' in beat['narration']) or beat['narration'].count('{result}') > 1:
            raise ValueError('Result requires exactly one narration cue placeholder')
        if len(retained) > 4 or len(set(retained)) != len(retained) or not set(retained) <= known | set(results):
            raise ValueError('Invalid retained board content')
        if not (set(lesson['pinnedRows']) & known) <= set(retained) or not set(results) <= set(retained):
            raise ValueError('Original problem and current result must remain visible')
        for target in beat['highlights']:
            if target not in terms or terms[target][0] not in retained:
                raise ValueError('Highlight references an unseen term')
        operation = beat['operation']
        kind = operation['kind']
        src = [equation(rows[key]) for key in sources]
        result = equation(rows[results[0]]) if results else None
        expected = None
        if kind == 'given':
            if sources or not results or results[0] not in lesson['pinnedRows']:
                raise ValueError('Given must introduce an original equation')
            givens.add(results[0])
        elif kind == 'explain':
            if results:
                raise ValueError('Explanation cannot introduce unchecked math')
        elif kind == 'add':
            if len(src) != 2 or not results:
                raise ValueError('Addition requires two sources and one result')
            expected = tuple(tuple(a + b for a, b in zip(left, right)) for left, right in zip(*src))
            targets = operation.get('cancelTerms', [])
            if targets:
                if len(targets) != 2 or targets[0] == targets[1] or any(t not in terms for t in targets):
                    raise ValueError('Invalid cancellation targets')
                (owner_a, a), (owner_b, b) = (terms[t] for t in targets)
                if {owner_a, owner_b} != set(sources) or a is None or b is None or not any(a[:2]) or any(x + y for x, y in zip(a, b)):
                    raise ValueError('Cancellation requires opposite terms from both source equations')
                for target in targets:
                    owner = terms[target][0]
                    row_terms = rows[owner]['nodes']
                    if next(i for i,t in enumerate(row_terms) if t['id'] == target) > next(i for i,t in enumerate(row_terms) if t['text'] == '='):
                        raise ValueError('Cancellation must be on the same equation side')
        elif kind in ('divide', 'subtract'):
            if len(src) != 1 or not results:
                raise ValueError('Operation requires one source and result')
            value = scalar(operation['divisor' if kind == 'divide' else 'value'])
            if kind == 'divide':
                if not value:
                    raise ValueError('Division by zero')
                expected = tuple(tuple(v / value for v in side) for side in src[0])
            else:
                expected = tuple((x, y, constant - value) for x, y, constant in src[0])
        elif kind in ('substitute', 'verify'):
            if not src or not results:
                raise ValueError('Substitution requires a source and result')
            values = operation['values']
            evidence = operation['evidence']
            if not set(evidence) <= set(sources[1:]):
                raise ValueError('Substitution evidence must be established sources')
            for variable, value in values.items():
                assignment = ((Fraction(variable == 'x'), Fraction(variable == 'y'), Fraction(0)),
                              (Fraction(0), Fraction(0), scalar(value)))
                if not any(equation(rows[key]) == assignment for key in evidence):
                    raise ValueError('Substitution value lacks solved-variable evidence')
            expected = substitute(src[0], values)
            if kind == 'verify':
                if sources[0] not in givens or set(values) != {'x', 'y'} or expected[0] != expected[1]:
                    raise ValueError('Final substitution fails an original equation')
                verified.add(sources[0])
        elif kind == 'interpret':
            if results or verified != set(lesson['pinnedRows']):
                raise ValueError('Interpretation requires both original checks')
            for key in givens:
                sides = substitute(equation(rows[key]), operation['values'])
                if sides[0] != sides[1] or any(sides[0][:2]) or any(sides[1][:2]):
                    raise ValueError('Final pair does not satisfy both originals')
        else:
            raise ValueError('Unsupported mathematical operation: ' + kind)
        if expected is not None and result != expected:
            raise ValueError('Incorrect intermediate result for ' + beat['id'])
        known.update(results)
    if verified != set(lesson['pinnedRows']) or known != set(rows) or lesson['beats'][-1]['operation']['kind'] != 'interpret':
        raise ValueError('Incomplete worked lesson')


def compile_lesson(lesson: dict) -> dict:
    """Reuse shared token speech/cues and cinematic schema; math has one source."""
    validate_lesson(lesson)
    from pipeline.cinematic_content import speak_atom
    rows = {row['id']: deepcopy(row) for row in lesson['rows']}
    beats, board, states = [], [], []
    for authored in lesson['beats']:
        identifier = authored['id']
        narration = authored['narration']
        if authored['results']:
            source = rows[authored['results'][0]]
            # Keep authored semantic IDs while reusing the established speech tokenizer.
            # Signed terms (+y/-y) are single semantic units for paired highlighting.
            words, nodes = [], []
            prefix, suffix = narration.split('{result}')
            for token in source['nodes']:
                text = token['text']
                phrase = ('plus ' if text.startswith('+') else 'minus ' if text.startswith('-') else '') + speak_atom(text.lstrip('+-'))
                phrase = phrase.strip()
                before = prefix + ' '.join(words)
                target = phrase.split()
                normalized = lambda s: re.sub(r'[^\w\s]', '', s.lower()).split()
                earlier = normalized(before)
                occurrence = sum(earlier[i:i+len(target)] == target for i in range(len(earlier)))
                nodes.append({**token, 'cue': {'beat': identifier, 'phrase': phrase, 'occurrence': occurrence}})
                words.extend(phrase.split())
            speech = prefix + ' '.join(words) + suffix
            cue = nodes[0]['cue']
            row = {'id': source['id'], 'label': source['label'], 'nodes': nodes, 'cue': cue}
            rows[source['id']] = row
            board.append(row)
        else:
            speech = narration
        cue = {'beat': identifier, 'phrase': authored['cuePhrase']}
        beats.append({'id': identifier, 'scene': 'algebra', 'speech': speech,
                      'holdSeconds': authored['readingPauseSeconds'], 'teaching': deepcopy(authored)})
        reason = authored['reason']
        if authored['operation']['kind'] == 'interpret':
            values = authored['operation']['values']
            reason = f"Solution: x = {values['x']}, y = {values['y']}. " + reason
        states.append({'cue': cue, 'rowIds': authored['retain'], 'reason': reason})
        for target in authored['highlights']:
            for row in board:
                for node in row['nodes']:
                    if node['id'] == target:
                        node['highlight'] = {'from': cue, 'to': {'beat': identifier, 'phrase': speech.split()[-1], 'edge': 'end'}}
        for row in board:
            for node in row['nodes']:
                if 'cancel' in node and 'cancelUntil' not in node and node['cancel']['beat'] != identifier:
                    node['cancelUntil'] = cue
        for target in authored['operation'].get('cancelTerms', []):
            for row in board:
                for node in row['nodes']:
                    if node['id'] == target:
                        node['cancel'] = {'beat': identifier, 'phrase': 'cancel'}
    return {'schemaVersion': 'cinematic-v1', 'previewMode': False, 'day': lesson['day'], 'title': lesson['title'],
            'chapters': [{'id': 'elimination', 'title': lesson['title'], 'dark': False,
                          'beats': beats, 'board': board, 'boardStates': states}]}
