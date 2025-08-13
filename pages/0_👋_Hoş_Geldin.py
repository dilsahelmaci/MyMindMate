# -*- coding: utf-8 -*-
"""
Hoşgeldin Sayfası.

Bu sayfa, uygulamayı ilk kez ziyaret eden veya oturum açmamış kullanıcılar
için bir karşılama ekranı görevi görür. Uygulamanın ne olduğunu özetler ve
kullanıcıyı giriş/kayıt sayfasına yönlendiren bir buton içerir.

Bu sayfa sadece oturum açmamış kullanıcılara gösterilir. Oturum açmış bir
kullanıcı bu sayfaya erişmeye çalışırsa, `app.py` tarafından otomatik olarak
Ana Sayfa'ya yönlendirilir.
"""
import streamlit as st
from utils.style import inject_sidebar_styles

st.set_page_config(page_title="Hoş Geldin", page_icon="👋")


# --- Sayfa Yapılandırması ve Stiller ---
# Bu sayfa sadece giriş yapmamış kullanıcılar içindir.
# Giriş yapmış kullanıcılar app.py tarafından doğrudan Dashboard'a yönlendirilir.
inject_sidebar_styles()

# --- Özel Buton Stili ---
st.markdown("""
<style>
    div[data-testid="stButton"] > button {
        background-color: #4DB6AC;
        color: white;
        border-radius: 20px;
        padding: 10px 20px;
        border: none;
        font-weight: bold;
        transition: background-color 0.3s;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #80CBC4; /* Ana rengin biraz daha açık bir tonu */
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar İçeriği ---
with st.sidebar:
    st.markdown("## 🧠 MyMindMate")
    st.markdown("---")
    st.markdown("*Kişisel gelişim ve ruh hali takibi için AI destekli dijital arkadaşınız!*")

# --- Ana Sayfa İçeriği ---
st.markdown("""
<div style="text-align: center; padding-top: 2rem;">
    <h1 style="font-weight: 800; font-size: 3.5rem; margin-bottom: 1.5rem; color: #262730;">MyMindMate'e Hoş Geldin!</h1>
    <p style="font-size: 1.25rem; line-height: 1.8; color: #4F4F4F; max-width: 720px; margin: auto;">
        Merhaba! <br><br>
        Kendini daha iyi tanımaya, hislerini anlamaya ve kafandakileri biraz olsun netleştirmeye hazır mısın? ✨ <br>
        Ben MyMindMate, birlikte düşünen ve sana destek olan dijital bir arkadaşım. <br><br>
        Günlük yazabilir, hedeflerini belirleyebilir veya benimle sadece sohbet edip dertleşebilirsin. <br>
        Sana uygun bir tempoda, seni zorlamadan, güvenli bir ortamda. <br>
        Burada sadece sen varsın. 🫂 <br><br>
        <b style="font-size: 1.3rem;">Hazırsan, hadi başlayalım mı?</b>
    </p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.write("")

# --- Giriş Butonu (Ortalanmış) ---
col1, col2, col3 = st.columns([2, 3, 2])
with col2:
    if st.button("🚪 Giriş Yap / Kayıt Ol", use_container_width=True):
        st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
