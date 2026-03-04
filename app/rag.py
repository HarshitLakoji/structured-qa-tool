import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
import os
from groq import Groq
import json
from huggingface_hub import InferenceClient

load_dotenv()

hf_client = InferenceClient(
    token=os.getenv("HF_TOKEN")
)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
#embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client(
    Settings(
        persist_directory="./chroma_db",
        is_persistent=True
    )
)

collection = chroma_client.get_or_create_collection(name="documents")

print("===== CHROMA DEBUG =====")
print("Collection count:", collection.count())
print("=========================")


def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks

def get_embedding(text: str):
    embedding = hf_client.feature_extraction(
        text,
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    return embedding


def add_document_to_vectorstore(doc_id: int, text: str, user_id: int, filename: str):

    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):

        embedding = get_embedding(chunk)

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{doc_id}_{i}"],
            metadatas=[{
                "user_id": user_id,
                "filename": filename,
                "chunk": i
            }]
        )

def retrieve_relevant_chunks(query: str, user_id: int, top_k: int = 2):

    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id}
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    citations = []

    for meta in metadatas:
        citations.append(
            f"{meta['filename']} (chunk {meta['chunk']})"
        )

    return documents, citations

def generate_answer(question: str, user_id: int):

    relevant_chunks, citations = retrieve_relevant_chunks(question, user_id)

    if not relevant_chunks:
        return {
            "answer": "Not found in references.",
            "citations": []
        }

    context = "\n\n".join(relevant_chunks)

    prompt = f"""
You are answering a security compliance questionnaire.

Rules:
- Use ONLY the provided context.
- Answer in 1–3 concise sentences.
- If not found say: Not found in references.
- Do NOT guess.

Context:
{context}

Question:
{question}

Answer:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    answer_text = response.choices[0].message.content.strip()

    if "Not found" in answer_text:
        return {
            "answer": "Not found in references.",
            "citations": [],
            "confidence": "Low"
        }

    confidence = "Low"
    if len(citations) >= 2:
        confidence = "High"
    elif len(citations) == 1:
        confidence = "Medium"

    return {
        "answer": answer_text,
        "citations": citations,
        "confidence": confidence
    }

def generate_answers_batch(questions: list[str], user_id: int):

    question_blocks = []
    citations_map = {}

    for q in questions:
        chunks, citations = retrieve_relevant_chunks(q, user_id)

        context = "\n".join(chunks)

        question_blocks.append(
            f"""
Question:
{q}

Context:
{context}
"""
        )

        citations_map[q] = citations

    combined_prompt = f"""
You are answering a security compliance questionnaire.

Rules:
- Use ONLY the provided context.
- If the answer is not present respond exactly: Not found in references.
- Answer concisely (1-3 sentences).
- Return output strictly in JSON.

Questions:
{''.join(question_blocks)}

Return format:
[
  {{
    "question": "...",
    "answer": "..."
  }}
]
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": combined_prompt}],
        temperature=0
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        answers = json.loads(raw_output)
    except:
        return []

    results = []

    for item in answers:
        q = item["question"]
        citations = citations_map.get(q, [])
        confidence = "Low"
        if len(citations) >= 2:
            confidence = "High"
        elif len(citations) == 1:
            confidence = "Medium"

        results.append({
            "question": q,
            "answer": item["answer"],
            "citations": citations,
            "confidence": confidence
        })

    return results