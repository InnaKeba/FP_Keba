from langchain_core.tools import tool
import chromadb

# ── 1. RAG Tool ChromaDB ──
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="support_faq")

if collection.count() == 0:
    collection.add(
        documents=[
            "Повернення коштів можливе протягом 14 днів після списання.",
            "Для налаштування роутера перейдіть за адресою 192.168.1.1.",
            "Щоб змінити тариф, зверніться до менеджера або використайте особистий кабінет."
        ],
        metadatas=[{"category": "billing"}, {"category": "tech"}, {"category": "general"}],
        ids=["faq1", "faq2", "faq3"]
    )

@tool
def search_knowledge(query: str) -> str:
    """Пошук у базі знань (FAQ) за ключовими словами."""
    results = collection.query(query_texts=[query], n_results=1)
    if results['documents'] and results['documents'][0]:
        return results['documents'][0][0]
    return "Інформацію не знайдено."

# ── 2. Legacy Pydantic Tools (*з ДЗ1) ──
@tool
def calculate_refund(amount: float, days_used: int) -> str:
    """Розрахунок суми повернення (пропорційно невикористаним дням)."""
    if days_used < 0 or days_used > 30:
        return "Помилка: кількість днів має бути від 0 до 30."
    refund = amount - (amount / 30) * days_used
    return f"До повернення: {refund:.2f} грн."