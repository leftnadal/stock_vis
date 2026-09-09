"""Working replay protocol; no repair of JSON content or surrounding prose."""
import json
import re

def parse_action(text):
    if not isinstance(text, str):
        raise ValueError('answer_not_string')
    body = text.strip()
    wrapping = 'plain_json'
    if body.startswith('```'):
        match = re.fullmatch(r'```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```', body)
        if not match:
            raise ValueError('invalid_json_fence')
        body = match.group(1)
        wrapping = 'single_json_fence'
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate_json_key')
            out[key] = value
        return out
    def constant(value):
        raise ValueError('nonfinite_json_number')
    action = json.loads(body, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(action, dict):
        raise ValueError('action_not_object')
    if action.get('action') == 'final':
        if not isinstance(action.get('answer'), str) or not action['answer'].strip():
            raise ValueError('missing_final_answer')
        for key in ('used_source_ids', 'changes', 'limitations'):
            if not isinstance(action.get(key), list) or not all(isinstance(x, str) for x in action[key]):
                raise ValueError('invalid_final_field_' + key)
    elif action.get('action') == 'retrieve':
        if not isinstance(action.get('source_ids'), list) or not all(isinstance(x, str) for x in action['source_ids']):
            raise ValueError('invalid_source_ids')
    else:
        raise ValueError('invalid_action')
    return action, wrapping
