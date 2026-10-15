import os,re
import torch
from sentence_transformers import SentenceTransformer
class Embeddings:
    def __init__(self):
        torch.set_num_threads(int(os.getenv('EMBEDDING_CPU_THREADS','2')))
        self.name=os.getenv('EMBEDDING_MODEL','sentence-transformers/all-MiniLM-L6-v2')
        self.revision=os.environ['EMBEDDING_REVISION']
        if not re.fullmatch(r'[0-9a-f]{40}',self.revision):raise ValueError('Use an immutable embedding model revision')
        self.model=SentenceTransformer(self.name,revision=self.revision,device='cpu',trust_remote_code=False)
        self.dimension=self.model.get_embedding_dimension()
        if self.dimension!=384:raise ValueError('Embedding dimension requires an explicit schema migration')
    def encode(self,texts): return self.model.encode(texts,normalize_embeddings=True,show_progress_bar=True).tolist()
    @property
    def metadata(self): return {'model':self.name,'revision':self.revision,'dimension':self.dimension}
