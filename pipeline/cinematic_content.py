"""Curriculum -> original word-cued boards and computed diagrams, without day-specific scenes."""
from __future__ import annotations

import math
import re
from collections import Counter
from copy import deepcopy
from typing import Any

from pipeline.mathtext import latex_to_plain, split_sentences
from pipeline.semantic_math import tokenize_math
from pipeline.lesson_contract import _math_expr

_SUPERSCRIPTS = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻', '0123456789+-')
_SMALL = ('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen').split()
_TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
_OPERATORS = {'+': 'plus', '-': 'minus', '−': 'minus', '=': 'equals', '/': 'divided by',
    '×': 'times', '*': 'times', '·': 'times', '÷': 'divided by', '≠': 'is not equal to',
    '≤': 'is less than or equal to', '≥': 'is greater than or equal to', '<': 'is less than',
    '>': 'is greater than', '≈': 'is approximately', '→': 'therefore', '⇒': 'therefore', '…': 'and so on', '⋯': 'and so on', '∪': 'union', '∩': 'intersection', '∅': 'empty set', '&': 'and', '∝': 'is proportional to',
    '⇔': 'if and only if', '∞': 'infinity', '√': 'square root of', 'π': 'pi',
    '^': 'to the power of', '±': 'plus or minus', '∈': 'belongs to', '∑': 'the sum of',
    '—': 'which means', '°': 'degrees', '!': 'factorial', '%': 'percent', '∀': 'for every', '∃': 'there exists',
    '∫': 'the integral of', '∂': 'partial', "'": 'prime', '[': 'open bracket', ']': 'close bracket', '|': 'absolute value', '.': 'point', '{': 'open brace', '}': 'close brace', 'θ': 'theta', 'α': 'alpha', 'β': 'beta'}


def number_words(value: str) -> str:
    if '.' in value:
        whole, fraction = value.split('.', 1)
        return number_words(whole) + ' point ' + ' '.join(_SMALL[int(digit)] for digit in fraction)
    number = int(value)
    if number < 0:
        return 'negative ' + number_words(str(-number))
    if number < 20:
        return _SMALL[number]
    if number < 100:
        return _TENS[number // 10] + (' ' + _SMALL[number % 10] if number % 10 else '')
    if number < 1000:
        return _SMALL[number // 100] + ' hundred' + (' ' + number_words(str(number % 100)) if number % 100 else '')
    for size, name in [(10**9, 'billion'), (10**6, 'million'), (1000, 'thousand')]:
        if number >= size:
            return number_words(str(number // size)) + ' ' + name + (' ' + number_words(str(number % size)) if number % size else '')
    raise ValueError('Unsupported numeric speech')


def speak_atom(text: str) -> str:
    if text in _OPERATORS:
        return _OPERATORS[text]
    if re.fullmatch(r'\d+(?:\.\d+)?', text):
        return number_words(text)
    if re.fullmatch(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+', text):
        exponent = text.translate(_SUPERSCRIPTS)
        if exponent in ['-', '+']: return 'negative' if exponent == '-' else 'plus'
        return {'2': 'squared', '3': 'cubed'}.get(exponent, 'to the power of ' + number_words(exponent))
    if text == '(':
        return 'open bracket'
    if text == ')':
        return 'close bracket'
    if text in ',;:':
        return 'means' if text == ':' else 'then'
    if text == '?':
        return 'what value'
    return text.replace('_', ' sub ')


def _split_top_level(text: str, separators: str) -> list[str]:
    depth, start, result = 0, 0, []
    for index, character in enumerate(text):
        if character in '([{⎡⎜': depth += 1
        elif character in ')]}⎤⎟': depth -= 1
        elif character in separators and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    result.append(text[start:].strip())
    return result


def math_display(source: str) -> str:
    source = re.sub(r'\\(?:mathbf|mathrm|operatorname|mathcal|vec|hat)\{([^{}]*)\}', r'\1', source)
    def matrix(match):
        opening, closing = ('⎜', '⎟') if match[1] == 'vmatrix' else ('⎡', '⎤')
        rows = [','.join(latex_to_plain(cell) for cell in row.split('&')) for row in re.split(r'\\\\', match[2])]
        return opening + ';'.join(rows) + closing
    source = re.sub(r'\\begin\{(pmatrix|bmatrix|vmatrix)\}(.*?)\\end\{\1\}', matrix, source, flags=re.S)
    while r'\xrightarrow{' in source:
        start = source.index(r'\xrightarrow{')
        opening = start + len(r'\xrightarrow')
        depth, end = 1, opening + 1
        while end < len(source) and depth:
            if source[end] == '{': depth += 1
            elif source[end] == '}': depth -= 1
            end += 1
        if depth: raise ValueError('Unbalanced transformation arrow label')
        label = latex_to_plain(source[opening+1:end-1])
        source = source[:start] + ' → (' + label + ') ' + source[end:]

    return latex_to_plain(source)


def equation_steps(source: str) -> list[str]:
    """Keep source equality order; never invent a solution or discard an operand."""
    clauses = re.split(r"\\(?:qquad|quad)\s*", source)
    result: list[str] = []
    for clause in clauses:
        plain = math_display(clause).replace('−', '-').strip(' ,;')
        if not plain: continue
        pieces = _split_top_level(plain, '=')
        result.extend([plain] if len(pieces) <= 2 else [' = '.join(pieces[:2]), *('= ' + piece for piece in pieces[2:])])
    return result



def _strip_outer(text: str) -> str:
    if text.startswith('(') and text.endswith(')'):
        depth = 0
        for index, character in enumerate(text):
            if character == '(': depth += 1
            elif character == ')': depth -= 1
            if depth == 0 and index < len(text) - 1: return text
        return text[1:-1]
    return text


def _expression_nodes(text: str, prefix: str) -> list[dict[str, Any]]:
    division = _split_top_level(text, '/')
    if len(division) == 2 and all(division):
        return [{'id': prefix + '-fraction', 'top': _expression_nodes(_strip_outer(division[0]), prefix + '-n'),
                 'bottom': _expression_nodes(_strip_outer(division[1]), prefix + '-d')}]
    matrix_match = re.search(r'([⎡⎜])([^⎡⎜⎤⎟]*)[⎤⎟]', text)
    if matrix_match:
        rows = matrix_match[2].split(';')
        cells = [[_expression_nodes(cell.strip(), prefix + f'-r{row_index}c{column_index}')
                  for column_index, cell in enumerate(row.split(','))] for row_index, row in enumerate(rows)]
        matrix_node = {'id': prefix + '-matrix', 'cells': cells, 'determinant': matrix_match[1] == '⎜'}
        return [*_expression_nodes(text[:matrix_match.start()], prefix + '-before'), matrix_node,
                *_expression_nodes(text[matrix_match.end():], prefix + '-after')]
    # Function applications are semantic units; arithmetic outside them still reveals atom by atom.
    pattern = r'\b[A-Za-z](?:⁻¹)?\([-+−]?\w+\)'
    nodes, cursor = [], 0
    for match in re.finditer(pattern, text):
        if match.start() > cursor:
            nodes.extend(_plain_nodes(text[cursor:match.start()], prefix + f'-p{cursor}'))
        function, argument = match.group().split('(', 1)
        argument = argument[:-1]
        words = function.replace('⁻¹', ' inverse') + ' of ' + ('negative ' + speak_atom(argument[1:]) if argument.startswith(('-', '−')) else speak_atom(argument))
        nodes.append({'id': prefix + f'-f{match.start()}', 'text': match.group(), 'spoken': words, 'accent': True})
        cursor = match.end()
    nodes.extend(_plain_nodes(text[cursor:], prefix + f'-p{cursor}'))
    return nodes


def _plain_nodes(text: str, prefix: str) -> list[dict[str, Any]]:
    return [{'id': f'{prefix}-{index}', 'text': span.text.replace('-', '−'),
             'spoken': speak_atom(span.text), 'accent': span.role in {'variable', 'function'}}
            for index, span in enumerate(tokenize_math(text, mode='math')) if span.text.strip()]


def node_width(nodes: list[dict]) -> float:
    total = 0.0
    for node in nodes:
        if 'text' in node:
            total += max(.33, sum(.32 if char in 'il1·()' else .78 if char in '=+−÷×' else .57 for char in node['text'])) + .11
        elif 'cells' in node:
            columns = max(map(len, node['cells']))
            total += sum(max((node_width(row[column]) if column < len(row) else 0) for row in node['cells']) for column in range(columns)) * .72 + columns * .5 + .4
        else:
            total += max(node_width(node['top']), node_width(node['bottom'])) * .82 + .4
    return total


def readable_steps(source: str) -> list[str]:
    result = []
    for expression in equation_steps(source):
        chunks, start, depth, last_break = [], 0, 0, None
        for index, character in enumerate(expression):
            if character in '([{⎡⎜': depth += 1
            elif character in ')]}⎤⎟': depth -= 1
            if depth == 0 and index > start and (character in '+-,' or character.isspace()):
                last_break = index
            width = node_width(_expression_nodes(expression[start:index+1], 'measure'))
            if width > 1680 / 64 and last_break is not None and last_break > start:
                chunks.append(expression[start:last_break].strip())
                start, last_break = last_break, None
        chunks.append(expression[start:].strip())
        for chunk in chunks:
            if node_width(_expression_nodes(chunk, 'measure')) > 1680 / 64:
                raise ValueError('Expression needs an authored mathematical line break: ' + chunk)
            if chunk: result.append(chunk)
    return result


def make_math_beat(identifier: str, scene: str, expression: str, label: str) -> tuple[dict, dict]:
    sides = _split_top_level(expression, '=')
    nodes: list[dict] = []
    for index, side in enumerate(sides):
        if index:
            nodes.append({'id': f'{identifier}-eq{index}', 'text': '=', 'spoken': 'equals'})
        nodes.extend(_expression_nodes(side, f'{identifier}-side{index}'))
    phrases: list[str] = []
    starts: dict[str, int] = {}
    def align(group: list[dict]) -> None:
        for node in group:
            if 'text' in node:
                spoken = node.pop('spoken')
                node['cue'] = {'beat': identifier, 'phrase': spoken}
                starts[node['id']] = len(phrases)
                phrases.extend(spoken.split())
            elif 'cells' in node:
                for row_index, row in enumerate(node['cells']):
                    phrases.extend(['row', number_words(str(row_index + 1))])
                    for cell in row: align(cell)
            else:
                align(node['top'])
                phrases.extend(['divided', 'by'])
                align(node['bottom'])
    align(nodes)
    if not nodes or not phrases:
        raise ValueError('An empty mathematical expression cannot be narrated')
    # An occurrence is counted over the complete speech, including multiword phrases.
    speech = ' '.join(phrases) + '.'
    tokens = phrases
    def correct_occurrences(group: list[dict]) -> None:
        for node in group:
            if 'text' in node:
                phrase = node['cue']['phrase']
                target = phrase.split()
                node['cue']['occurrence'] = sum(tokens[index:index+len(target)] == target for index in range(starts[node['id']]))
            elif 'cells' in node:
                for row in node['cells']:
                    for cell in row: correct_occurrences(cell)
            else:
                correct_occurrences(node['top']); correct_occurrences(node['bottom'])
    correct_occurrences(nodes)
    first = next(_atoms(nodes))['cue']
    return ({'id': identifier, 'scene': scene, 'speech': speech, 'holdSeconds': 1.4},
            {'id': identifier + '-row', 'cue': deepcopy(first), 'label': label, 'nodes': nodes, 'wide': node_width(nodes) > 1090 / 64})


def _atoms(nodes: list[dict]):
    for node in nodes:
        if 'text' in node: yield node
        elif 'cells' in node:
            for row in node['cells']:
                for cell in row: yield from _atoms(cell)
        else:
            yield from _atoms(node['top']); yield from _atoms(node['bottom'])


def _arithmetic_source(text: str) -> str:
    text = text.replace('−', '-').replace('·', '*').replace('×', '*')
    text = re.sub(r'([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)', lambda match: '**(' + match[0].translate(_SUPERSCRIPTS) + ')', text)
    text = re.sub(r'(?<=\d)(?=x|\()', '*', text)
    text = re.sub(r'(?<=\))(?=x|\()', '*', text)
    return text.replace('^', '**')


def attach_verified_cancellation(previous: dict, current: dict, before: str, after: str, beat_id: str, scene: str) -> dict | None:
    from sympy import simplify
    before_rhs, after_rhs = _split_top_level(before, '=')[-1], _split_top_level(after, '=')[-1]
    try:
        if simplify(_math_expr(_arithmetic_source(before_rhs)) - _math_expr(_arithmetic_source(after_rhs))) != 0:
            return None
    except ValueError:
        return None
    row_nodes = previous['nodes']
    last_equals = max((index for index, node in enumerate(row_nodes) if node.get('text') == '='), default=-1)
    nodes = row_nodes[last_equals + 1:]
    terms, current_term, sign, depth = [], [], 1, 0
    for node in nodes:
        text = node.get('text', '')
        if text == '(': depth += 1
        if text == ')': depth -= 1
        if depth == 0 and text in ['+', '−', '-']:
            if current_term: terms.append((sign, current_term))
            sign, current_term = (-1 if text in ['−', '-'] else 1), []
        else: current_term.append(node)
    if current_term: terms.append((sign, current_term))
    numbers = [(sign * float(term[0]['text']), term[0]) for sign, term in terms
               if len(term) == 1 and re.fullmatch(r'\d+(?:\.\d+)?', term[0].get('text', ''))]
    for index, (value, node) in enumerate(numbers):
        for other_value, other_node in numbers[index+1:]:
            if value != 0 and value == -other_value:
                cue = {'beat': beat_id, 'phrase': 'cancel'}
                node['cancel'] = cue; other_node['cancel'] = cue
                return {'id': beat_id, 'scene': scene, 'speech': 'The opposite terms cancel.', 'holdSeconds': .8}
    for node in nodes:
        if 'top' not in node or len(node['bottom']) != 1: continue
        denominator = node['bottom'][0]
        value = denominator.get('text', '')
        if not re.fullmatch(r'\d+(?:\.\d+)?', value) or float(value) == 0: continue
        if any(atom.get('text') in ['+', '−', '-'] for atom in node['top']): continue
        factor = next((atom for atom in node['top'] if atom.get('text') == value), None)
        if factor is not None:
            cue = {'beat': beat_id, 'phrase': 'cancels'}
            factor['cancel'] = cue; denominator['cancel'] = cue
            return {'id': beat_id, 'scene': scene, 'speech': 'The common nonzero factor cancels.', 'holdSeconds': .8}
    return None


def parse_plot_expression(text: str):
    candidate = latex_to_plain(text).split('=')
    if len(candidate) < 2 or not re.fullmatch(r'[fghp](?:\(x\))?', candidate[0].strip()):
        return None
    expression = candidate[1].strip().replace('−', '-')
    expression = re.sub(r'([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)', lambda match: '**(' + match[0].translate(_SUPERSCRIPTS) + ')', expression)
    expression = re.sub(r'(?<=\d)(?=x|\()', '*', expression)
    expression = re.sub(r'(?<=\))(?=x|\()', '*', expression)
    expression = expression.replace('^', '**')
    try:
        return _math_expr(expression)
    except ValueError:
        return None


def graph_model(source: str) -> dict | None:
    expression = parse_plot_expression(source)
    if expression is None: return None
    from sympy import Symbol
    variable = Symbol('x')
    points = []
    for index in range(241):
        x_value = -3 + index / 40
        try:
            y_value = float(expression.subs(variable, x_value))
        except (ValueError, TypeError, ZeroDivisionError):
            points.append(None); continue
        points.append({'x': x_value, 'y': y_value} if math.isfinite(y_value) and abs(y_value) < 10000 else None)
    samples = []
    for value in [-1, 0, 1]:
        try:
            output = float(expression.subs(variable, value))
            if math.isfinite(output): samples.append({'x': value, 'y': output})
        except (ValueError, TypeError, ZeroDivisionError): pass
    return {'kind': 'function', 'equation': latex_to_plain(source), 'points': points, 'samples': samples}


def build_cinematic_plan(lesson: dict) -> dict:
    """All mathematical states come from the lesson; the renderer is shared by all days."""
    for name in ['day', 'topic', 'lesson_goal', 'concept_intuition', 'key_formula', 'board_examples', 'common_mistake']:
        if not lesson.get(name): raise ValueError('Missing cinematic lesson field: ' + name)
    day = int(lesson['day'])
    boards = lesson['board_examples']
    chapters: list[dict] = []
    def narration_chapter(name: str, title: str, texts: list[str], *, dark: bool = False, diagram: dict | None = None) -> None:
        beats = [{'id': f'd{day:03d}-{name}-{index:03d}', 'scene': name,
                  'speech': text, 'holdSeconds': 1.1} for index, text in enumerate(texts) if text.strip()]
        chapters.append({'id': name, 'title': title, 'dark': dark, 'beats': beats, 'board': [], 'diagram': deepcopy(diagram)})
    narration_chapter('opening', lesson['topic'], [
        'Here is our challenge. Why does this mathematical rule work?',
        f"Hold that thought, because today it becomes mathematics. Welcome to Math Concepts Made Easy. Today is Day {number_words(str(day))}. Our lesson is {lesson['topic']}.",
        lesson['lesson_goal']], dark=True)
    diagram = graph_model(boards.get('formula', ''))
    narration_chapter('machine', 'See the idea.', split_sentences(lesson['concept_intuition']), dark=True, diagram=diagram)
    if diagram:
        chapter = chapters[-1]
        chapter['diagram']['sampleCues'] = []
        for sample_index, sample in enumerate(diagram['samples']):
            identifier = f'd{day:03d}-machine-sample-{sample_index}'
            input_words = number_words(str(int(sample['x'])))
            output_words = number_words(str(int(sample['y']))) if sample['y'].is_integer() else str(sample['y'])
            chapter['beats'].append({'id': identifier, 'scene': 'machine',
                'speech': f'At input {input_words}, the output is {output_words}.', 'holdSeconds': 1.1})
            chapter['diagram']['sampleCues'].append({'beat': identifier, 'phrase': 'At input'})
    def mathematics_chapter(name: str, title: str, sources: list[str], label: str) -> None:
        beats, rows = [], []
        for source_index, source in enumerate(sources):
            for expression in readable_steps(str(source)):
                identifier = f'd{day:03d}-{name}-{len(beats):03d}'
                beat, mathematical_row = make_math_beat(identifier, name, expression, label if source_index == 0 else 'Continue the working')
                if rows:
                    cancellation = attach_verified_cancellation(rows[-1], mathematical_row, beats[-1].get('expression', ''), expression, identifier + '-cancel', name)
                    if cancellation: beats.append(cancellation)
                beat['expression'] = expression
                beats.append(beat); rows.append(mathematical_row)
        chapters.append({'id': name, 'title': title, 'dark': False, 'beats': beats, 'board': rows, 'diagram': None})
    mathematics_chapter('algebra', 'Build the rule.', [lesson['key_formula']], 'The key relationship')
    mathematics_chapter('verify', 'Work it through.', [boards.get('formula') or lesson['key_formula'], *boards['worked_example']], 'Worked example')
    narration_chapter('domain', 'Check the reasoning.', split_sentences(lesson['common_mistake']), diagram=diagram)
    mathematics_chapter('practice', 'Your turn.', boards['practice'], 'Try it independently')
    practice = chapters[-1]
    if practice['beats']:
        first = practice['beats'][0]
        practice['beats'].insert(1, {'id': f'd{day:03d}-practice-pause', 'scene': 'practice',
            'speech': 'Pause here. Work through the next step before continuing.', 'holdSeconds': 6.0})
    narration_chapter('recap', 'The idea to keep.', [lesson['lesson_goal'], 'Keep the reasoning, not just the answer. We will build on this in the next lesson.'], dark=True, diagram=diagram)
    if not all(chapter['beats'] for chapter in chapters):
        raise ValueError('A complete lesson needs narration in every teaching chapter')
    return enrich_symmetry_story({'schemaVersion': 'cinematic-v1', 'day': day, 'title': lesson['topic'], 'chapters': chapters}, lesson)


def enrich_symmetry_story(plan: dict, lesson: dict) -> dict:
    """Use exact function identities to build the geometric/algebraic symmetry story."""
    rule = math_display(lesson['key_formula']).replace(' ', '')
    if 'f(-x)' not in rule or '-f(x)' not in rule: return plan
    from sympy import Symbol, latex, simplify
    variable = Symbol('x')
    candidates = re.findall(r'[fgh]\(x\)\s*=\s*[^\s,;]+', lesson['common_mistake'])
    neither = None
    for source in candidates:
        expression = parse_plot_expression(source)
        if expression is not None and simplify(expression.subs(variable, -variable) - expression) != 0 and simplify(expression.subs(variable, -variable) + expression) != 0:
            neither = (source, expression); break
    if neither:
        source, expression = neither
        sample = next((value for value in range(1, 21)
                       if simplify(expression.subs(variable, -value) - expression.subs(variable, value)) != 0
                       and simplify(expression.subs(variable, -value) + expression.subs(variable, value)) != 0), None)
        if sample is None: raise ValueError('Cannot find a verified symmetry counterexample')
        positive = expression.subs(variable, sample)
        negative = expression.subs(variable, -sample)
        sources = [source, 'f(-x)=' + latex(expression.subs(variable, -variable)),
                   f'f({sample})=' + latex(positive), f'f(-{sample})=' + latex(negative),
                   latex(negative) + r'\neq ' + latex(positive), latex(negative) + r'\neq ' + latex(-positive),
                   r'\text{Neither even nor odd}']
        chapter = next(item for item in plan['chapters'] if item['id'] == 'domain')
        chapter['title'], chapter['board'], chapter['beats'], chapter['diagram'] = 'Test the whole function.', [], [], None
        for index, source_line in enumerate(sources):
            identifier = f"d{plan['day']:03d}-domain-{index:03d}"
            beat, row = make_math_beat(identifier, 'domain', math_display(source_line), 'Check both symmetries')
            chapter['beats'].append(beat); chapter['board'].append(row)
    practice = lesson['board_examples']['practice'][0]
    diagram = graph_model(practice)
    if diagram:
        chapter_id = 'graph-check'
        identifier = f"d{plan['day']:03d}-{chapter_id}-intro"
        chapter = {'id': chapter_id, 'title': 'Check the graph.', 'dark': True, 'board': [], 'diagram': diagram,
                   'beats': [{'id': identifier, 'scene': 'graph',
                              'speech': 'Now check the same rule geometrically. Compare equal distances on opposite sides of the origin.', 'holdSeconds': 1.5}]}
        diagram['sampleCues'] = []
        for index, point in enumerate(diagram['samples']):
            beat_id = f"d{plan['day']:03d}-{chapter_id}-{index:03d}"
            input_words = number_words(str(int(point['x'])))
            output_words = number_words(str(int(point['y']))) if point['y'].is_integer() else str(point['y'])
            chapter['beats'].append({'id': beat_id, 'scene': 'graph', 'speech': f'At input {input_words}, the output is {output_words}.', 'holdSeconds': 1.3})
            diagram['sampleCues'].append({'beat': beat_id, 'phrase': 'At input'})
        plan['chapters'].insert(-1, chapter)
    return plan
