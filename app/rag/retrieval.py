import hashlib
import json
import re
from pathlib import Path
import faiss
import numpy as np
import httpx
from sklearn.feature_extraction.text import TfidfTransformer, TfidfVectorizer
from app.config import ROOT

def filter_authorized_documents(chunks, role='customer'):
    # Defense in depth for this extractive demo. Approval is still an editorial trust boundary.
    injection = re.compile(r'ignore (?:previous|all|system) instructions|reveal all passwords|system prompt|execute (?:shell|code)|send .*secrets',re.I)
    return [c for c in chunks if c['approved'] and c['current'] and c['classification']=='public' and role in c['allowed_roles'] and not injection.search(c['text'])]

def ingest_documents(root=None):
    root = root or ROOT / 'knowledge_base'
    manifest = json.loads((root/'metadata'/'manifest.json').read_text(encoding='utf-8'))
    chunks = []
    for meta in manifest:
        path = (root/meta['source_file']).resolve()
        if root.resolve() not in path.parents:
            raise ValueError('Invalid source path')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta['sha256']:
            raise ValueError('Document approval digest mismatch')
        if path.suffix == '.pdf':
            from pypdf import PdfReader
            texts = [(i+1,p.extract_text()) for i,p in enumerate(PdfReader(path).pages)]
        else:
            texts = [(None,raw.decode('utf-8'))]
        for page,text in texts:
            for part in re.split(r'(?m)^## ', text)[1:]:
                title, _, body = part.partition('\n')
                section = title.split(' | ')[0].strip()
                # Small demo sections fit one chunk. Long documents use stable section-relative pieces.
                for offset in range(0, len(body), 1800):
                    chunk = dict(meta, section_id=section, section_title=title, chunk_id=f"{meta['document_id']}:{section}:{offset//1800}", page_number=page, text=body[offset:offset+1800].strip())
                    chunks.append(chunk)
    return chunks

class Retriever:
    def __init__(self, settings=None, chunks=None, cache_dir=None):
        self.settings = settings
        self.chunks = filter_authorized_documents(chunks if chunks is not None else ingest_documents())
        self.vectorizer = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True, stop_words='english')
        texts = [c['document_title']+' '+c['section_title']+' '+c['text'] for c in self.chunks]
        mode = settings.embedding_mode if settings else 'local_tfidf'
        model = settings.embedding_model if settings and mode == 'openrouter' else 'tfidf-word-bigram-v1'
        self.cache_dir = self._cache_path(settings, cache_dir) if chunks is None else None
        self.fingerprint = hashlib.sha256(json.dumps(
            {'chunks': self.chunks, 'mode': mode, 'model': model},
            sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str,
        ).encode('utf-8')).hexdigest()
        if not self._load_persistent_index(mode, model):
            if mode == 'openrouter':
                matrix = self.hosted_embeddings(texts)
            else:
                matrix = self.vectorizer.fit_transform(texts).toarray().astype('float32')
            faiss.normalize_L2(matrix)
            self.index = faiss.IndexFlatIP(matrix.shape[1]); self.index.add(matrix)
            if self.cache_dir:
                self._save_persistent_index(mode, model)

    @staticmethod
    def _cache_path(settings, cache_dir):
        configured = cache_dir or (settings.rag_index_dir if settings else 'runtime/faiss')
        path = Path(configured)
        return path if path.is_absolute() else ROOT / path

    def _load_persistent_index(self, mode, model):
        if not self.cache_dir:
            return False
        index_path = self.cache_dir / 'policies.faiss'
        manifest_path = self.cache_dir / 'manifest.json'
        vectorizer_path = self.cache_dir / 'vectorizer.json'
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest.get('fingerprint') != self.fingerprint or manifest.get('mode') != mode or manifest.get('model') != model:
                return False
            index = faiss.read_index(str(index_path))
            if index.ntotal != len(self.chunks) or index.d != manifest.get('dimension'):
                return False
            if mode == 'local_tfidf':
                state = json.loads(vectorizer_path.read_text(encoding='utf-8'))
                self.vectorizer = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True,
                    stop_words='english', vocabulary=state['vocabulary'])
                self.vectorizer.vocabulary_ = state['vocabulary']
                self.vectorizer.fixed_vocabulary_ = True
                self.vectorizer._tfidf = TfidfTransformer(norm='l2', use_idf=True, smooth_idf=True, sublinear_tf=True)
                self.vectorizer._tfidf.idf_ = np.asarray(state['idf'], dtype='float64')
                if len(state['vocabulary']) != index.d:
                    return False
            self.index = index
            return True
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError):
            return False

    def _save_persistent_index(self, mode, model):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        index_path = self.cache_dir / 'policies.faiss'
        index_tmp = self.cache_dir / 'policies.faiss.tmp'
        manifest_path = self.cache_dir / 'manifest.json'
        manifest_tmp = self.cache_dir / 'manifest.json.tmp'
        manifest_path.unlink(missing_ok=True)
        faiss.write_index(self.index, str(index_tmp))
        index_tmp.replace(index_path)
        if mode == 'local_tfidf':
            state = {'vocabulary': self.vectorizer.vocabulary_, 'idf': self.vectorizer.idf_.tolist()}
            vectorizer_tmp = self.cache_dir / 'vectorizer.json.tmp'
            vectorizer_tmp.write_text(json.dumps(state, separators=(',', ':')), encoding='utf-8')
            vectorizer_tmp.replace(self.cache_dir / 'vectorizer.json')
        manifest = {'fingerprint': self.fingerprint, 'mode': mode, 'model': model,
                    'dimension': self.index.d, 'chunk_count': self.index.ntotal}
        manifest_tmp.write_text(json.dumps(manifest, separators=(',', ':')), encoding='utf-8')
        manifest_tmp.replace(manifest_path)

    def hosted_embeddings(self, texts):
        if not self.settings.openrouter_api_key or not self.settings.embedding_model:
            raise ValueError('OpenRouter embeddings require OPENROUTER_API_KEY and EMBEDDING_MODEL')
        r = httpx.post(self.settings.openrouter_base_url.rstrip('/') + '/embeddings',
            headers={'Authorization':f'Bearer {self.settings.openrouter_api_key}'},
            json={'model':self.settings.embedding_model,'input':texts}, timeout=60)
        r.raise_for_status()
        data = r.json()['data']
        return np.array([item['embedding'] for item in sorted(data,key=lambda x:x['index'])],dtype='float32')

    def retrieve_relevant_chunks(self, query, k=3, role='customer'):
        if role != 'customer':
            return []
        if self.settings and self.settings.embedding_mode=='openrouter':
            vector = self.hosted_embeddings([query])
        else:
            vector = self.vectorizer.transform([query]).toarray().astype('float32')
        faiss.normalize_L2(vector)
        scores, indices = self.index.search(vector, min(k,len(self.chunks)))
        threshold = 0.18 if not self.settings or self.settings.embedding_mode=='local_tfidf' else 0.5
        return [dict(self.chunks[i], score=float(s)) for s,i in zip(scores[0],indices[0]) if i>=0 and s>=threshold]

def generate_citations(chunks):
    keys = ('document_id','document_title','section_id','chunk_id','version','effective_date','source_file','page_number')
    return [{k:c[k] for k in keys} for c in chunks]
