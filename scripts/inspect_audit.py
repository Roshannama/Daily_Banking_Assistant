import argparse
import json
from pathlib import Path

parser=argparse.ArgumentParser(description='Local-only trace inspection; never exposes credentials')
parser.add_argument('--trace',required=True)
args=parser.parse_args()
path=Path(__file__).resolve().parents[1]/'runtime'/'audit.jsonl'
for line in path.read_text(encoding='utf-8').splitlines() if path.exists() else []:
    event=json.loads(line)
    if event['trace_id']==args.trace:
        print(json.dumps(event,indent=2))
