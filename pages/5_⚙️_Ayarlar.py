# -*- coding: utf-8 -*-
"""
Kullanıcı Ayarları Sayfası.

Bu sayfa, kullanıcıların hesap bilgilerini yönetmelerine ve veriyle ilgili
hassas işlemleri gerçekleştirmelerine olanak tanır.

İşleyiş:
1.  **Oturum Kontrolü:** Sayfaya sadece giriş yapmış kullanıcılar erişebilir.
2.  **Hesap Yönetimi:**
    -   Kullanıcı adını güncelleme.
    -   Kullanıcının saat dilimini güncelleme. Bu, proaktif karşılamaların
        doğru zamanda yapılmasını sağlar.
3.  **Veri Yönetimi (Tehlikeli İşlemler):**
    -   **Yapay Zeka Hafızasını Sıfırlama:** Kullanıcıya ait tüm vektörleri
        Pinecone'dan siler. Bu işlem, ek bir onay mekanizması ile korunur.
    -   **Hesabı Kalıcı Olarak Silme:** Bu en tehlikeli işlemdir ve bir
        `st.expander` içinde bulunur. Kullanıcının "sil" yazarak onaylaması
        gerekir. Onaylandığında:
        a. `firebase_db.delete_all_user_data` ile kullanıcının tüm profil,
           günlük ve hedef verileri Firebase'den silinir.
        b. `memory.delete_user_memory` ile kullanıcının AI hafızası
           Pinecone'dan silinir.
        c. Kullanıcının oturumu sonlandırılır (`st.session_state.clear()`).
"""
import streamlit as st
import pytz
import time

from core import firebase_db, memory
from components.sidebar_info import render_sidebar_user_info
from utils.style import inject_sidebar_styles

st.set_page_config(page_title="Ayarlar", page_icon="⚙️")

# --- Oturum Kontrolü ---
if "user_id" not in st.session_state:
    st.warning("Bu sayfayı görüntülemek için lütfen giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
    st.stop()


inject_sidebar_styles()
render_sidebar_user_info()

# --- Sayfa Başlığı ---
# Özel markdown başlık yerine standart st.title kullanılarak
# diğer sayfalarla görsel tutarlılık sağlanır.
st.title("⚙️ Ayarlar")

user_id = st.session_state.get("user_id")
id_token = st.session_state.get("user_id_token")

# Token kontrolü
if not user_id or not id_token:
    st.error("Lütfen önce giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")

# Kullanıcı detaylarını id_token ile güvenli bir şekilde çek
user_details = firebase_db.get_user_details(user_id, id_token) if user_id else {}

# --- Bölümler ---
st.subheader("Hesap Yönetimi")

# --- Ad Değiştirme ---
current_name = user_details.get("name", "")
new_name = st.text_input("Yeni Adınız", value=current_name, key="name_input")
if st.button("Adı Güncelle", key="update_name_btn"):
    if new_name and new_name != current_name:
        firebase_db.update_user_profile_field(user_id, "name", new_name, id_token)
        st.session_state["user_name"] = new_name
        st.success("Adınız başarıyla güncellendi!")
        time.sleep(1)
    elif not new_name:
        st.warning("Ad alanı boş olamaz.")
    else:
        st.info("Herhangi bir değişiklik yapılmadı.")

# --- Saat Dilimi Ayarı ---
st.markdown("---")
current_timezone = user_details.get("timezone", "UTC")
all_timezones = pytz.all_timezones
try:
    current_index = all_timezones.index(current_timezone)
except ValueError:
    all_timezones.insert(0, current_timezone)
    current_index = 0

new_timezone = st.selectbox(
    "Saat Diliminiz",
    options=all_timezones,
    index=current_index,
    help="Uygulamanın sizinle doğru zamanda iletişim kurmasını sağlar.",
    key="tz_selectbox"
)
if st.button("Saat Dilimini Güncelle", key="update_tz_btn"):
    if new_timezone != current_timezone:
        firebase_db.update_user_profile_field(user_id, "timezone", new_timezone, id_token)
        st.success("Saat diliminiz başarıyla güncellendi!")
        time.sleep(1)
        st.rerun()

st.markdown("---")
st.subheader("Veri Yönetimi")

# --- Hafıza Sıfırlama ---
st.warning("🚨 Bu işlem geri alınamaz.", icon="⚠️")
if st.button("Yapay Zeka Hafızasını Sıfırla", help="AI'ın sizinle ilgili tüm öğrendiklerini (sohbet geçmişi anıları) kalıcı olarak siler."):
    if "confirm_delete_memory" not in st.session_state:
        st.session_state.confirm_delete_memory = True

if st.session_state.get("confirm_delete_memory"):
    st.markdown("**Emin misiniz?** Bu, yapay zekanın sizinle olan tüm sohbet anılarını kalıcı olarak silecektir.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Evet, Hafızayı Sil", type="primary"):
            memory.delete_user_memory(user_id)
            st.session_state.confirm_delete_memory = False
            if "chat_history" in st.session_state:
                del st.session_state["chat_history"]
            st.success("Yapay zeka hafızası başarıyla sıfırlandı!")
            st.rerun()
    with col2:
        if st.button("Hayır, Vazgeç"):
            st.session_state.confirm_delete_memory = False
            st.rerun()

st.markdown("---")
# --- Hesabı Silme ---
st.error("🚨 DİKKAT: BU İŞLEM GERİ ALINAMAZ!", icon="⚠️")
with st.expander("🚨 Hesabı Kalıcı Olarak Sil"):
    st.warning("DİKKAT: Bu işlem geri alınamaz! Tüm günlükleriniz, hedefleriniz ve sohbet geçmişiniz kalıcı olarak silinecektir.")
    confirm_text = st.text_input("Silme işlemini onaylamak için 'sil' yazın.")
    if st.button("Hesabımı Kalıcı Olarak Sil", type="primary"):
        if confirm_text.lower() == "sil":
            with st.spinner("Hesabınız ve tüm verileriniz siliniyor..."):
                # 1. Firebase DB'den tüm kullanıcı verilerini sil
                firebase_db.delete_all_user_data(user_id, id_token)
                
                # 2. Pinecone'dan vektörleri sil
                memory.delete_user_memory(user_id)
                st.success("Hesabınız ve tüm verileriniz başarıyla silindi. Hoşça kalın!")
                st.session_state.clear()
                st.rerun()
        else:
            st.warning("Hesap silme işlemi iptal edildi.")
