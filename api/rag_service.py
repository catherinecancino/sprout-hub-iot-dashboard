# api/rag_service.py
import os
import json
import re

# ── OpenAI ──────────────────────────────────────────────────────────────────
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: openai not installed. Run: pip install openai")
    OPENAI_AVAILABLE = False

openai_client = None
if OPENAI_AVAILABLE:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        openai_client = OpenAI(api_key=api_key)
    else:
        print("Warning: OPENAI_API_KEY not found in environment variables")

# ── ChromaDB ────────────────────────────────────────────────────────────────
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    print("Warning: chromadb not installed. Run: pip install chromadb")
    CHROMA_AVAILABLE = False

# ── Document Parsers ─────────────────────────────────────────────────────────
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class RAGService:
    OPENAI_MODEL = "gpt-4o-mini"
    _chroma_client = None
    _collection    = None

    # ─────────────────────── CHROMA INIT ────────────────────────────────────

    @classmethod
    def _get_collection(cls):
        if cls._collection is not None:
            return cls._collection

        if not CHROMA_AVAILABLE:
            raise RuntimeError("ChromaDB not installed.")

        if cls._chroma_client is None:
            chroma_path = os.path.join(os.path.dirname(__file__), "chroma_db")
            os.makedirs(chroma_path, exist_ok=True)
            cls._chroma_client = chromadb.PersistentClient(path=chroma_path)

        ef = embedding_functions.DefaultEmbeddingFunction()
        cls._collection = cls._chroma_client.get_or_create_collection(
            name="agricultural_knowledge",
            embedding_function=ef,
        )
        return cls._collection

    # ─────────────────────── TEXT EXTRACTION ────────────────────────────────

    @staticmethod
    def extract_text_from_pdf(file_path):
        if not PDF_AVAILABLE:
            raise RuntimeError("PyPDF2 not installed. Run: pip install PyPDF2")
        text = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
        return "\n".join(text)

    @staticmethod
    def extract_text_from_docx(file_path):
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    @staticmethod
    def extract_text_from_txt(file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    # ─────────────────────── CHUNKING ───────────────────────────────────────

    @staticmethod
    def chunk_text(text, chunk_size=500, overlap=50):
        words  = text.split()
        chunks = []
        start  = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - overlap
        return chunks

    # ─────────────────────── STORE DOCUMENT ─────────────────────────────────

    @classmethod
    def store_document(cls, text, document_name, crop_type="general"):
        collection = cls._get_collection()
        chunks     = cls.chunk_text(text)

        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_name}_{i}"
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append({
                "document_name": document_name,
                "crop_type":     crop_type,
                "chunk_index":   i,
                "total_chunks":  len(chunks),
            })

        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas)

        return {"status": "stored", "chunks": len(chunks), "document": document_name}

    # ─────────────────────── SEARCH ─────────────────────────────────────────

    @classmethod
    def search_knowledge(cls, query, n_results=4, crop_type=None):
        try:
            collection = cls._get_collection()
            kwargs = {"query_texts": [query], "n_results": n_results}
            if crop_type:
                kwargs["where"] = {"crop_type": crop_type}
            results = collection.query(**kwargs)

            items = []
            if results and results.get("documents"):
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    items.append({"text": doc, "metadata": meta, "distance": dist})
            return items

        except Exception as e:
            print(f"RAG search error: {e}")
            return []

    # ─────────────────────── LIST DOCUMENTS ─────────────────────────────────

    @classmethod
    def list_documents(cls):
        try:
            collection = cls._get_collection()
            all_items  = collection.get()
            seen, docs = set(), []
            for meta in all_items.get("metadatas", []):
                name = meta.get("document_name")
                if name and name not in seen:
                    seen.add(name)
                    docs.append({
                        "name":      name,
                        "crop_type": meta.get("crop_type", "general"),
                    })
            return docs
        except Exception as e:
            print(f"List documents error: {e}")
            return []

    # ─────────────────────── DELETE DOCUMENT ────────────────────────────────

    @classmethod
    def delete_document(cls, document_name):
        try:
            collection = cls._get_collection()
            all_items  = collection.get()
            ids_to_del = []
            for doc_id, meta in zip(
                all_items.get("ids", []),
                all_items.get("metadatas", []),
            ):
                if meta.get("document_name") == document_name:
                    ids_to_del.append(doc_id)

            if ids_to_del:
                collection.delete(ids=ids_to_del)
                return {"status": "deleted", "document": document_name, "chunks_removed": len(ids_to_del)}

            return {"status": "not_found", "document": document_name}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─────────────────────── THRESHOLD EXTRACTION (GPT-4o-mini) ─────────────

    @classmethod
    def extract_thresholds_from_text(cls, text, crop_type):
        """
        Use GPT-4o-mini to extract numeric growing thresholds from a document.
        Returns a dict of threshold values, or an empty dict on failure.
        """
        if not OPENAI_AVAILABLE or openai_client is None:
            print("OpenAI not available for threshold extraction.")
            return {}

        # Truncate to keep within token limits (~3000 words ≈ 4000 tokens)
        words = text.split()
        if len(words) > 3000:
            text = " ".join(words[:3000]) + "...[truncated]"

        prompt = f"""You are an agricultural expert. Extract growing thresholds from the text below for crop: {crop_type}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
    "moisture_min": <number or null>,
    "moisture_max": <number or null>,
    "ph_min": <number or null>,
    "ph_max": <number or null>,
    "temp_min": <number or null>,
    "temp_max": <number or null>,
    "nitrogen_min": <number or null>,
    "nitrogen_max": <number or null>,
    "phosphorus_min": <number or null>,
    "phosphorus_max": <number or null>,
    "potassium_min": <number or null>,
    "potassium_max": <number or null>,
    "humidity_min": <number or null>,
    "humidity_max": <number or null>
}}

Rules:
- Use null for values not found in the text
- All numbers should be numeric (not strings)
- Do NOT include any text outside the JSON object

TEXT:
{text}"""

        try:
            response = openai_client.chat.completions.create(
                model=cls.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.1,    # Low temp for structured extraction
            )

            raw = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

            thresholds = json.loads(raw)

            # Filter out null values
            return {k: v for k, v in thresholds.items() if v is not None}

        except json.JSONDecodeError as e:
            print(f"JSON parse error in threshold extraction: {e}")
            return {}
        except Exception as e:
            print(f"Threshold extraction error: {e}")
            return {}