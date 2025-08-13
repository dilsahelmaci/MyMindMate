# -*- coding: utf-8 -*-
"""
Yapay Zeka Uzun Süreli Hafıza Yönetimi Modülü (Pinecone Entegrasyonu).

Bu modül, yapay zekanın kullanıcıya özel uzun süreli hafızasını yönetir.
Kullanıcıyla yapılan önemli konuşmaları, günlükleri ve hedefleri anlamsal
vektörlere dönüştürerek Pinecone adlı vektör veritabanında saklar. Bu sayede
yapay zeka, geçmiş konuşmaları "hatırlayabilir" ve daha bağlamsal yanıtlar
üretebilir (Retrieval-Augmented Generation - RAG).

İşleyiş:
1.  Metinler, `get_gemini_embedding` ile sayısal vektörlere çevrilir.
2.  Bu vektörler, kullanıcı ID'si ile etiketlenerek Pinecone'a kaydedilir (`save_to_memory`).
3.  Yeni bir sohbette, kullanıcının mesajına anlamsal olarak en yakın geçmiş
    konuşmalar Pinecone'dan aranır (`search_memory`).
4.  Bulunan bu "hatıralar", yapay zekaya ek bağlam olarak sunulur.
"""
import streamlit as st
import numpy as np
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import uuid

# --- GÜVENLİ KONFİGÜRASYON VE BAŞLATMA ---

try:
    PINECONE_API_KEY = st.secrets["pinecone"]["api_key"]
    GOOGLE_API_KEY = st.secrets["google"]["api_key"]
    genai.configure(api_key=GOOGLE_API_KEY)
except (KeyError, AttributeError):
    raise RuntimeError(
        "Pinecone veya Google API anahtarı bulunamadı. "
        "Lütfen `.streamlit/secrets.toml` dosyanızı kontrol edin."
    )

# --- PINECONE INDEX KURULUMU ---

EMBED_DIM = 768  # Gemini 'embedding-001' modelinin vektör boyutu.
INDEX_NAME = "mymindmate-memory"  # Pinecone'daki index'imizin adı.

pc = Pinecone(api_key=PINECONE_API_KEY)

# Uygulama ilk kez çalıştırıldığında, Pinecone'da index'imiz yoksa oluştur.
# Bu, manuel kurulum ihtiyacını ortadan kaldırır.
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBED_DIM,
        metric="cosine",  # Anlamsal benzerlik için en yaygın ve etkili metrik.
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"  # Pinecone ücretsiz katmanının standart bölgesi.
        )
    )

# Index'e bağlanarak üzerinde işlem yapmaya hazır hale gel.
pinecone_index = pc.Index(INDEX_NAME)

# --- YARDIMCI FONKSİYON: EMBEDDING ALMA ---

@st.cache_data(show_spinner=False)
def get_gemini_embedding(text: str) -> List[float]:
    """
    Verilen metin için Google Gemini embedding'i oluşturur.
    
    `@st.cache_data` sayesinde aynı metin için tekrar tekrar API çağrısı
    yapılmaz, bu da performansı artırır ve maliyeti düşürür.
    """
    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"  # Arama amaçlı embedding olduğunu belirtir.
        )
        return response["embedding"]
    except Exception as e:
        st.error(f"Embedding alınırken bir hata oluştu: {e}")
        return []

# --- ANA HAFIZA YÖNETİMİ FONKSİYONLARI ---

def save_to_memory(user_id: str, text: str, metadata: Dict[str, Any]):
    """Bir metni, meta verileriyle birlikte kullanıcının hafızasına kaydeder."""
    if not user_id or not text:
        return

    # Pinecone'a gönderilecek her vektörün benzersiz bir ID'si olmalıdır.
    vector_id = str(uuid.uuid4())
    embedding = get_gemini_embedding(text)
    if not embedding:
        return  # Embedding alınamadıysa kaydetme.

    # Pinecone'a yüklenecek vektörü hazırla. Metaveri, arama sonuçlarını
    # zenginleştirmek ve filtrelemek için kritik öneme sahiptir.
    vector_to_upsert = {
        "id": vector_id,
        "values": embedding,
        "metadata": {
            "user_id": user_id,  # Hangi kullanıcıya ait olduğunu belirtir.
            "text": text,        # Orijinal metni saklar.
            **metadata          # Gelen diğer tüm meta verileri ekler (örn: 'role', 'timestamp').
        }
    }

    try:
        pinecone_index.upsert(vectors=[vector_to_upsert])
    except Exception as e:
        st.error(f"Hafızaya kaydederken bir Pinecone hatası oluştu: {e}")

def search_memory(user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Kullanıcının hafızasında, verilen sorguyla anlamsal olarak en ilişkili
    kayıtları arar.
    """
    if not user_id or not query:
        return []

    query_embedding = get_gemini_embedding(query)
    if not query_embedding:
        return []

    try:
        # Pinecone'da arama yap ve sonuçları sadece ilgili kullanıcı için filtrele.
        results = pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,  # En alakalı `top_k` sonucu getir.
            filter={"user_id": {"$eq": user_id}},  # Sadece bu kullanıcıya ait vektörleri ara.
            include_metadata=True  # Sonuçlarla birlikte meta verileri de getir.
        )
        
        # Sonuçları, sadece meta verileri içeren temiz bir listeye dönüştür.
        found_matches = [match.metadata for match in results.matches] if results.matches else []
        return found_matches
    except Exception as e:
        st.error(f"Hafızada arama yaparken bir Pinecone hatası oluştu: {e}")
        return []

def delete_user_memory(user_id: str):
    """
    Belirli bir kullanıcıya ait tüm hafıza kayıtlarını (vektörleri) Pinecone'dan siler.
    Genellikle hesap silme işlemiyle birlikte kullanılır.
    """
    if not user_id:
        return
    
    try:
        pinecone_index.delete(filter={"user_id": {"$eq": user_id}})
        st.toast(f"{user_id} için AI hafızası başarıyla temizlendi.", icon="🧠")
    except Exception as e:
        st.error(f"Kullanıcı hafızasını silerken bir Pinecone hatası oluştu: {e}")