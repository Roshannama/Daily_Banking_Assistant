import json
from datetime import datetime, timezone
from pathlib import Path
from app.config import ROOT

class Audit:
    def __init__(self, repository, path=None):
        self.repository = repository
        self.path = path or ROOT/'runtime'/'audit.jsonl'
        self.path.parent.mkdir(parents=True,exist_ok=True)

    def record(self, trace, customer, event, **kwargs):
        allowed = {'agents','tools','authorization','pin_outcome','confirmation','source_ids','action_status','latency_ms','error_category'}
        row = dict(trace_id=trace, customer_id=customer, timestamp=datetime.now(timezone.utc).isoformat(), event=event, **{k:v for k,v in kwargs.items() if k in allowed})
        # No prompts, answers, credentials, bearer tokens, or PIN hashes.
        self.repository.audit(row)
        with self.path.open('a',encoding='utf-8') as f:
            f.write(json.dumps(row)+'\n')
