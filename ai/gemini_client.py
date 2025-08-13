# -*- coding: utf-8 -*-
"""
Google Gemini API İstemci Modülü.

Bu modül, Google'ın Gemini üretken yapay zeka modelleriyle tüm etkileşimi
merkezi bir yerden yönetir. İki ana işlevi vardır:
1.  Metin tabanlı sohbet yanıtları oluşturmak (`get_gemini_response`).
2.  Metinleri anlamsal vektörlere (embeddings) dönüştürmek (`get_gemini_embedding`),
    bu vektörler yapay zekanın uzun süreli hafızası için kullanılır.
"""
import streamlit as st
import google.generativeai as genai
import numpy as np
import requests

# --- API Anahtarı ve Model Başlatma ---
# Uygulama başlarken API anahtarını Streamlit secrets'tan okur ve modeli başlatır.
# Bu, her fonksiyon çağrıldığında tekrar tekrar kurulum yapılmasını engeller.
try:
    genai.configure(api_key=st.secrets["google"]["api_key"])
except (KeyError, AttributeError):
    # Eğer secrets dosyası veya anahtar bulunamazsa, uygulamayı bilgilendirici
    # bir hata ile durdur. Bu, kurulum hatalarını kolayca tespit etmeyi sağlar.
    raise RuntimeError(
        "Google Gemini API anahtarı bulunamadı. "
        "Lütfen `.streamlit/secrets.toml` dosyanıza `[google]` başlığı altına "
        "`api_key = '...'` şeklinde ekleyin."
    )

# Kullanılacak ana dil modeli (LLM). "latest" her zaman en güncel ve yetenekli
# Pro modelini kullanmamızı sağlar.
_gemini_model = genai.GenerativeModel("models/gemini-1.5-pro-latest")


def get_gemini_response(prompt: str, system_instruction: str = None) -> str:
    """
    Verilen bir metin istemine (prompt) Gemini modeli ile yanıt oluşturur.

    Args:
        prompt (str): Yapay zekanın yanıtlaması istenen kullanıcı mesajı veya soru.
        system_instruction (str, optional): Modelin nasıl davranması gerektiğini
            belirleyen sistem talimatı (örn: "Sen bir yardımcı asistansın.").
            Varsayılan: None.

    Returns:
        str: Model tarafından üretilen temizlenmiş metin yanıtı.
    """
    if system_instruction:
        # Sistem talimatı varsa, en iyi sonuçlar için kullanıcı isteminin başına eklenir.
        full_prompt = f"{system_instruction}\n\n{prompt}"
        response = _gemini_model.generate_content(full_prompt)
    else:
        response = _gemini_model.generate_content(prompt)
    
    # Modelin yanıtını `response.text` özelliğinden al ve başındaki/sonundaki
    # boşlukları temizle.
    return response.text.strip() if hasattr(response, "text") else str(response)


def get_gemini_embedding(text: str) -> np.ndarray:
    """
    Verilen metni, anlamsal bir sayısal vektöre (embedding) dönüştürür.

    Bu fonksiyon, Google'ın özel embedding modeli 'embedding-001'i kullanır.
    Elde edilen vektörler, metinler arası anlamsal benzerliği ölçmek için
    (örn: hafıza aramasında) kullanılır.

    Args:
        text (str): Vektöre dönüştürülecek metin.

    Returns:
        np.ndarray: Metnin 768 boyutlu sayısal vektör temsili.
                    Daha sonraki matematiksel işlemler için numpy array'i olarak döndürülür.
    """
    api_key = st.secrets["google"]["api_key"]
    # Embedding için standart REST API endpoint'i kullanılır.
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "models/embedding-001",
        "content": {"parts": [{"text": text}]}
    }
    
    response = requests.post(api_url, headers=headers, json=data)
    response.raise_for_status()  # API'den hata dönerse (örn: 4xx, 5xx) exception fırlat.
    
    emb = response.json()["embedding"]["values"]
    
    # Embedding'i, Pinecone gibi vektör veritabanlarının beklediği
    # format olan float32 tipinde bir numpy array'ine dönüştür.
    return np.array([emb], dtype="float32")