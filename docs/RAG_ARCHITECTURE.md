# RAG architecture

1. **Upload** (`POST /documents/upload`): extension allow-list (PDF/TXT/MD), content check on the first bytes (PDF magic, no NUL/binary, UTF-8), streamed size limit, server-generated file name.
2. **Extract** (`rag/document_loader.py`): PDFs via `pypdf` page by page (page numbers kept); encrypted, corrupt, >500-page or text-less (scanned) PDFs fail with a clear message. TXT/MD are one unnumbered page.
3. **Chunk** (`rag/chunking.py`): paragraph-aware, `RAG_CHUNK_SIZE` (800 chars) with `RAG_CHUNK_OVERLAP` (100); chunks never span pages; ids `c0000...` are unique per document.
4. **Embed** (`rag/embeddings.py`): `EMBEDDING_MODEL` (default `sentence-transformers/all-MiniLM-L6-v2`). If the package/model is unavailable and `EMBEDDING_FALLBACK=true`, a **lexical** hashing embedder is used (keyword-style matching with stopword removal, light stemming and 'time out' -> 'timeout' normalisation, 4096 hashed dimensions; not semantic, so e.g. 'respond' does not match 'response') and the Settings page says so.
5. **Index** (`rag/vector_store.py`): per-user store; FAISS `IndexFlatIP` when installed and `MATCHER=faiss`, otherwise exact NumPy search (same results). Vectors and metadata are saved separately; a stale/missing index is rebuilt from `document_chunks`. Deleting a document removes its chunks immediately.
6. **Retrieve** (`rag/retrieval.py`): top `RAG_TOP_K` above `RAG_SIMILARITY_THRESHOLD`, always filtered by `owner_id`. The default threshold (0.15) suits the lexical embedder; tune it for your embedding model.
7. **Generate** (`rag/generator.py`): excerpts are labelled C1..Cn inside `<untrusted_data>` delimiters; the model returns JSON `{answer, citations, sufficient}`.

## Guarantees (all unit-tested)
* No retrieved context -> the fixed message "The uploaded documentation does not provide a sufficient answer to this question." and the LLM is **not called**.
* Citations are rebuilt from the retrieved chunks (real document, page, chunk id); labels the model invents are dropped; an answer with no valid citation is withheld.
* LLM missing or failing -> the retrieved excerpts are still returned with an explanatory notice.
* Instructions embedded in documents are treated as data (sanitised, delimited); this reduces but cannot eliminate prompt-injection risk.
