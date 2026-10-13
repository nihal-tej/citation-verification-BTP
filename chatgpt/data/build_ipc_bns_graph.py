"""Build candidate IPC-BNS mappings and an LLM-assisted statutory graph.

Inputs (defaults are the two CSVs supplied for this project):
  /mnt/data/bns_correspondence.csv
  /mnt/data/BNS_IPC_Comparative.csv

For the LLM stage, create /mnt/data/statutory_texts.json with this format:
{
  "IPC:34": {"title": "...", "text": "Full provision text ..."},
  "BNS:3(5)": {"title": "...", "text": "Full provision text ..."}
}

Run candidate generation only:
  python build_ipc_bns_graph.py --stage candidates

Run candidates + LLM judgments (requires OPENAI_API_KEY and statutory_texts.json):
  python build_ipc_bns_graph.py --stage all

LLM outputs are proposed edges only. Expert review is still required before
calling any edge verified.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

BASE = Path('/mnt/data')
CORRESPONDENCE_CSV = BASE / 'bns_correspondence.csv'
COMPARATIVE_CSV = BASE / 'BNS_IPC_Comparative.csv'
TEXTS_JSON = BASE / 'statutory_texts.json'
OUT = BASE / 'ipc_bns_outputs'

RELATION_TYPES = [
    'EXACT',
    'MATERIAL_MODIFICATION',
    'SCOPE_EXPANDED',
    'SCOPE_NARROWED',
    'PUNISHMENT_ALTERED',
    'MERGED',
    'SPLIT',
    'NEW_PROVISION',
    'REPEALED_OR_OMITTED',
    'NO_DIRECT_CORRESPONDENCE',
    'UNCERTAIN',
]


def clean(value: Any) -> str:
    if pd.isna(value):
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def normalize_section(value: Any) -> str:
    """Normalize a section identifier, not its legal meaning."""
    s = clean(value).upper()
    s = re.sub(r'^\s*(BNS|IPC|SECTION|SEC\.?|S\.?)[\s:-]*', '', s)
    s = re.sub(r'\s+', '', s)
    s = s.strip(' .,:;')
    return s


def extract_ipc_sections(value: Any) -> list[str]:
    """Extract section-like identifiers from strings such as 'IPC 120A, 120B'.

    This is deliberately conservative. Review unusual source formats manually.
    """
    s = clean(value).upper()
    if not s or any(x in s for x in ['NEW OFFENCE', 'NEW OFFENSE', 'NO IPC', 'N/A', 'NONE']):
        return []
    # Match numbers optionally followed by a letter and/or parenthesized subsection.
    # Examples: 34, 120A, 376(3), 498A.
    matches = re.findall(r'(?<![A-Z0-9])\d+[A-Z]?(?:\(\d+[A-Z]?\))?', s)
    result = []
    for item in matches:
        item = normalize_section(item)
        if item and item not in result:
            result.append(item)
    return result


def make_candidate_rows() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not CORRESPONDENCE_CSV.exists() or not COMPARATIVE_CSV.exists():
        raise FileNotFoundError(
            'Could not find the input CSVs. Update CORRESPONDENCE_CSV and '
            'COMPARATIVE_CSV at the top of this script.'
        )

    correspondence = pd.read_csv(CORRESPONDENCE_CSV, dtype=str).fillna('')
    comparative = pd.read_csv(COMPARATIVE_CSV, dtype=str).fillna('')

    required_a = {'section', 'ipc_equivalent'}
    required_b = {'BNS_Section', 'IPC_Section'}
    if not required_a.issubset(correspondence.columns):
        raise ValueError(f'Correspondence CSV needs columns: {sorted(required_a)}')
    if not required_b.issubset(comparative.columns):
        raise ValueError(f'Comparative CSV needs columns: {sorted(required_b)}')

    rows: list[dict[str, Any]] = []

    # Source 1: BNS correspondence table.
    for idx, row in correspondence.iterrows():
        bns_raw = row.get('section', '')
        ipc_raw = row.get('ipc_equivalent', '')
        bns = normalize_section(bns_raw)
        ipc_sections = extract_ipc_sections(ipc_raw)
        if ipc_sections:
            for ipc in ipc_sections:
                rows.append({
                    'bns_section': bns,
                    'ipc_section': ipc,
                    'source': 'bns_correspondence.csv',
                    'source_row': int(idx) + 2,
                    'bns_title': clean(row.get('title', '')),
                    'ipc_source_text': clean(ipc_raw),
                    'status': '',
                    'candidate_status': 'CANDIDATE',
                })
        else:
            rows.append({
                'bns_section': bns,
                'ipc_section': '',
                'source': 'bns_correspondence.csv',
                'source_row': int(idx) + 2,
                'bns_title': clean(row.get('title', '')),
                'ipc_source_text': clean(ipc_raw),
                'status': '',
                'candidate_status': 'UNMATCHED_OR_NEW_PROVISION',
            })

    # Source 2: comparative table.
    for idx, row in comparative.iterrows():
        bns_raw = row.get('BNS_Section', '')
        ipc_raw = row.get('IPC_Section', '')
        bns = normalize_section(bns_raw)
        ipc_sections = extract_ipc_sections(ipc_raw)
        if ipc_sections:
            for ipc in ipc_sections:
                rows.append({
                    'bns_section': bns,
                    'ipc_section': ipc,
                    'source': 'BNS_IPC_Comparative.csv',
                    'source_row': int(idx) + 2,
                    'bns_title': clean(row.get('BNS_Title', '')),
                    'ipc_source_text': clean(ipc_raw),
                    'status': clean(row.get('Status', '')),
                    'candidate_status': 'CANDIDATE',
                })
        else:
            rows.append({
                'bns_section': bns,
                'ipc_section': '',
                'source': 'BNS_IPC_Comparative.csv',
                'source_row': int(idx) + 2,
                'bns_title': clean(row.get('BNS_Title', '')),
                'ipc_source_text': clean(ipc_raw),
                'status': clean(row.get('Status', '')),
                'candidate_status': 'UNMATCHED_OR_NEW_PROVISION',
            })

    all_rows = pd.DataFrame(rows)
    all_rows = all_rows[all_rows['bns_section'].astype(bool)].copy()

    # Preserve source rows in the audit output; deduplicate only the LLM worklist.
    all_rows.to_csv(OUT / 'ipc_bns_candidate_rows.csv', index=False)
    pair_rows = all_rows[all_rows['ipc_section'].astype(bool)].copy()
    candidates = (
        pair_rows.groupby(['bns_section', 'ipc_section'], as_index=False)
        .agg(
            sources=('source', lambda x: ';'.join(sorted(set(x)))),
            source_rows=('source_row', lambda x: ';'.join(map(str, sorted(set(x))))),
            bns_titles=('bns_title', lambda x: ' | '.join(sorted(set(v for v in x if v)))),
            ipc_source_texts=('ipc_source_text', lambda x: ' | '.join(sorted(set(v for v in x if v)))),
            source_statuses=('status', lambda x: ' | '.join(sorted(set(v for v in x if v)))),
        )
    )
    candidates['review_status'] = 'PENDING_TEXT_AND_LEGAL_REVIEW'
    candidates.to_csv(OUT / 'ipc_bns_candidates.csv', index=False)

    # Audit section keys appearing in only one source. This is not a legal mismatch.
    keys_a = {normalize_section(x) for x in correspondence['section'] if normalize_section(x)}
    keys_b = {normalize_section(x) for x in comparative['BNS_Section'] if normalize_section(x)}
    audit = pd.DataFrame([
        {'bns_section': key, 'present_in_correspondence': key in keys_a,
         'present_in_comparative': key in keys_b,
         'note': 'Identifier-level mismatch only; inspect granularity and source format.'}
        for key in sorted(keys_a | keys_b)
    ])
    audit.to_csv(OUT / 'bns_section_key_audit.csv', index=False)

    unmatched = all_rows[all_rows['ipc_section'].eq('')].copy()
    unmatched.to_csv(OUT / 'ipc_bns_unmatched_rows.csv', index=False)

    print(f'Loaded correspondence rows: {len(correspondence)}')
    print(f'Loaded comparative rows:    {len(comparative)}')
    print(f'Candidate IPC-BNS pairs:     {len(candidates)}')
    print(f'Rows needing manual parsing: {len(unmatched)}')
    print(f'Unique BNS keys in both sources: {len(keys_a & keys_b)}')
    print(f'Outputs: {OUT}')
    return candidates, all_rows


def load_statutory_texts() -> dict[str, dict[str, str]]:
    if not TEXTS_JSON.exists():
        raise FileNotFoundError(
            f'Missing {TEXTS_JSON}. Add full official provision texts in the JSON format '
            'described in the script header before running --stage all.'
        )
    with TEXTS_JSON.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('statutory_texts.json must be a JSON object keyed by IPC:<section> / BNS:<section>.')
    return data


def get_provision(texts: dict[str, dict[str, str]], act: str, section: str) -> dict[str, str] | None:
    key = f'{act}:{normalize_section(section)}'
    value = texts.get(key)
    if not isinstance(value, dict) or not clean(value.get('text', '')):
        return None
    return {'title': clean(value.get('title', '')), 'text': clean(value.get('text', ''))}


def judge_candidates(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError('Install dependencies with: pip install openai pandas networkx') from exc

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('Set OPENAI_API_KEY before running the LLM stage.')

    model = os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini')
    client = OpenAI(api_key=api_key)
    texts = load_statutory_texts()
    results: list[dict[str, Any]] = []

    for i, row in candidates.iterrows():
        bns_id = normalize_section(row['bns_section'])
        ipc_id = normalize_section(row['ipc_section'])
        ipc = get_provision(texts, 'IPC', ipc_id)
        bns = get_provision(texts, 'BNS', bns_id)
        base = {
            'bns_section': bns_id,
            'ipc_section': ipc_id,
            'sources': row.get('sources', ''),
            'source_rows': row.get('source_rows', ''),
        }

        if not ipc or not bns:
            results.append({
                **base,
                'labels': ['UNCERTAIN'],
                'rationale': 'Full text missing for IPC or BNS provision; no legal comparison performed.',
                'evidence': [],
                'confidence': 0.0,
                'review_status': 'NEEDS_STATUTORY_TEXT',
            })
            continue

        prompt = f'''Compare these two enacted statutory provisions for a research candidate mapping.
Do not assume they are equivalent because their titles or a government table says so.
Compare ingredients/elements, scope, exceptions, mental state, punishment, and legal effect.
You are not providing legal advice. If evidence is insufficient, use UNCERTAIN.

Allowed labels: {', '.join(RELATION_TYPES)}
Multiple labels may be used where appropriate. Use NO_DIRECT_CORRESPONDENCE only if the texts support that conclusion.
Evidence must quote short phrases from the supplied provisions and explain why they matter.
Return JSON only with keys: labels (array), rationale (string), evidence (array of objects with ipc_quote, bns_quote, explanation), confidence (number 0 to 1), review_status (string).
review_status should be EXPERT_REVIEW_REQUIRED unless the texts are clearly unavailable or malformed.

IPC Section {ipc_id}: {ipc.get('title', '')}
IPC text:
{ipc['text']}

BNS Section {bns_id}: {bns.get('title', '')}
BNS text:
{bns['text']}
'''
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': 'You are a cautious statutory comparison assistant. Return valid JSON only.'},
                    {'role': 'user', 'content': prompt},
                ],
                response_format={'type': 'json_object'},
                temperature=0,
            )
            raw = response.choices[0].message.content or '{}'
            judged = json.loads(raw)
            labels = judged.get('labels', ['UNCERTAIN'])
            if not isinstance(labels, list):
                labels = ['UNCERTAIN']
            labels = [x for x in labels if x in RELATION_TYPES] or ['UNCERTAIN']
            confidence = judged.get('confidence', 0.0)
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence = 0.0
            results.append({
                **base,
                'labels': labels,
                'rationale': clean(judged.get('rationale', '')),
                'evidence': judged.get('evidence', []),
                'confidence': confidence,
                'review_status': 'EXPERT_REVIEW_REQUIRED',
                'model': model,
            })
        except Exception as exc:
            results.append({
                **base,
                'labels': ['UNCERTAIN'],
                'rationale': f'LLM call or JSON parsing failed: {type(exc).__name__}: {exc}',
                'evidence': [],
                'confidence': 0.0,
                'review_status': 'LLM_ERROR_RETRY',
                'model': model,
            })
        print(f'Judged {len(results)}/{len(candidates)}: BNS {bns_id} <-> IPC {ipc_id}')

    with (OUT / 'ipc_bns_llm_judgments.jsonl').open('w', encoding='utf-8') as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    pd.DataFrame([
        {**r, 'labels': ';'.join(r.get('labels', [])),
         'evidence': json.dumps(r.get('evidence', []), ensure_ascii=False)}
        for r in results
    ]).to_csv(OUT / 'ipc_bns_llm_judgments.csv', index=False)
    return results


def build_graph(judgments: list[dict[str, Any]]) -> None:
    try:
        import networkx as nx
    except ImportError as exc:
        raise ImportError('Install NetworkX with: pip install networkx') from exc

    graph = nx.MultiDiGraph(name='Candidate IPC-BNS Correspondence Graph')
    for item in judgments:
        ipc = item['ipc_section']
        bns = item['bns_section']
        graph.add_node(f'IPC:{ipc}', act='IPC', section=ipc)
        graph.add_node(f'BNS:{bns}', act='BNS', section=bns)
        # Direction is old IPC provision -> new BNS provision for readability.
        graph.add_edge(
            f'IPC:{ipc}', f'BNS:{bns}',
            labels=';'.join(item.get('labels', ['UNCERTAIN'])),
            rationale=item.get('rationale', ''),
            confidence=float(item.get('confidence', 0.0)),
            review_status=item.get('review_status', 'EXPERT_REVIEW_REQUIRED'),
            sources=item.get('sources', ''),
            evidence=json.dumps(item.get('evidence', []), ensure_ascii=False),
        )

    nx.write_graphml(graph, OUT / 'ipc_bns_candidate_graph.graphml')
    graph_json = {
        'nodes': [{'id': node, **attrs} for node, attrs in graph.nodes(data=True)],
        'edges': [
            {'source': u, 'target': v, **attrs}
            for u, v, attrs in graph.edges(data=True)
        ],
        'warning': 'All LLM edges are proposed candidates; do not treat as verified without expert review.',
    }
    with (OUT / 'ipc_bns_candidate_graph.json').open('w', encoding='utf-8') as f:
        json.dump(graph_json, f, ensure_ascii=False, indent=2)
    print(f'Graph nodes: {graph.number_of_nodes()}, edges: {graph.number_of_edges()}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['candidates', 'all'], default='candidates')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    candidates, _ = make_candidate_rows()
    if args.stage == 'all':
        judgments = judge_candidates(candidates)
        build_graph(judgments)


if __name__ == '__main__':
    main()
