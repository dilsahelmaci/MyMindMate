# -*- coding: utf-8 -*-
"""
Hedef Yönetimi Sayfası.

Bu sayfa, kullanıcıların hem günlük hem de uzun vadeli hedeflerini
oluşturmasına, takip etmesine, tamamlamasına ve silmesine olanak tanır.

İşleyiş:
1.  **Oturum Kontrolü ve Veri Çekme:** Sayfaya sadece giriş yapmış kullanıcılar
    erişebilir. Sayfa yüklendiğinde, kullanıcının tüm hedef verileri
    Firebase'den tek seferde çekilir.
2.  **Tarih Seçici:** Kullanıcı, `st.date_input` ile belirli bir günün
    hedeflerini görüntülemek için bir tarih seçebilir. Varsayılan olarak
    bugünün tarihi seçilidir.
3.  **Hedef Ekleme Formu:** Kullanıcı yeni bir hedef metni ve türünü ("Günlük"
    veya "Uzun Vadeli") seçerek yeni bir hedef ekleyebilir. Günlük hedefler
    seçili tarihe, uzun vadeli hedefler ise her zaman bugünün tarihine
    kaydedilir.
4.  **Seçili Günün Hedefleri:** Tarih seçicisinde seçili olan güne ait
    hedefler, "Bekleyen Hedefler" ve "Tamamlanan Hedefler" olarak iki ayrı
    başlık altında listelenir.
5.  **Uzun Vadeli Hedefler:** Sayfanın altında, tarih seçicisinden bağımsız
    olarak, henüz tamamlanmamış tüm uzun vadeli hedefler ayrı bir bölümde
    gösterilir.
6.  **İnteraktif Butonlar:** Her hedefin yanında "Tamamla" ve "Sil" butonları
    bulunur, bu butonlar ilgili Firebase fonksiyonlarını tetikleyerek
    veritabanını günceller.
"""
import streamlit as st
import time
from datetime import date

from components.sidebar_info import render_sidebar_user_info
from core import firebase_db
from utils.style import inject_sidebar_styles


st.set_page_config(page_title="🎯 Hedeflerim", page_icon="🎯")

# --- Oturum Kontrolü ve Temel Değişkenler ---
if "user_id" not in st.session_state:
    st.warning("Bu sayfayı görüntülemek için lütfen giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
    st.stop()


inject_sidebar_styles()
render_sidebar_user_info()

user_id = st.session_state.get("user_id")
id_token = st.session_state.get("user_id_token")

# --- Arayüz Başlığı ---
st.title("🎯 Hedeflerim")

# --- Tarih Seçici Widget'ı ---
selected_date_obj = st.date_input("Hedeflerini görüntülemek için bir tarih seç:", value=date.today(), key="goal_date_selector")
selected_date_str = selected_date_obj.isoformat()

# --- Veri Çekme ---
with st.spinner("Hedefler yükleniyor..."):
    all_goals_data = firebase_db.get_goals(user_id, id_token)

# --- Veri İşleme (Seçili Güne Göre Filtreleme) ---
pending_today = []
completed_today = []
if all_goals_data and selected_date_str in all_goals_data:
    day_goals = all_goals_data[selected_date_str].get("pending", {})
    for goal_id, goal_details in day_goals.items():
        if isinstance(goal_details, dict):
            goal_item = {"id": goal_id, **goal_details}
            if goal_details.get("is_checked"):
                completed_today.append(goal_item)
            else:
                pending_today.append(goal_item)

# --- Hedef Ekleme Formu ---
with st.form("add_goal_form", clear_on_submit=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        goal_text = st.text_input("Yeni bir hedef ekle:", placeholder="Bugün neyi başarmak istersin?")
    with col2:
        goal_type_tr = st.selectbox("Hedef Türü", ["Günlük", "Uzun Vadeli"], key="goal_type_selector")
    
    submitted = st.form_submit_button("🎯 Ekle")
    if submitted and goal_text.strip():
        goal_type = "daily" if goal_type_tr == "Günlük" else "longterm"
        # Günlük hedefler seçili tarihe, uzun vadeliler bugünün tarihine kaydedilir
        date_to_save = selected_date_str if goal_type == "daily" else date.today().isoformat()
        firebase_db.save_goal(user_id, date_to_save, goal_text.strip(), goal_type, id_token)
        st.success(f"'{goal_type_tr}' hedefin başarıyla eklendi!")
        time.sleep(1)
        st.rerun()

st.markdown("---")

# --- Seçili Günün Hedeflerini Gösterme ---
st.subheader(f"🗓️ {selected_date_str} Gününün Hedefleri")

# Yapılacaklar
st.markdown("#### Bekleyen Hedefler")
if not pending_today:
    st.success("Bugün için bekleyen hedefin yok. Harika gidiyorsun! 🎉", icon="✨")
else:
    for goal in pending_today:
        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
        with col1:
            st.markdown(f"**-** {goal.get('goal', '')}")
        with col2:
            if st.button("✅", key=f"done_{goal['id']}", use_container_width=True):
                firebase_db.update_goal_check(user_id, goal['id'], selected_date_str, True, id_token)
                st.rerun()
        with col3:
            if st.button("🗑️", key=f"delete_daily_{goal['id']}", use_container_width=True):
                firebase_db.delete_goal_by_id(user_id, goal['id'], selected_date_str, id_token)
                st.rerun()

# Tamamlananlar
st.markdown("#### Tamamlanan Hedefler")
if not completed_today:
    st.info("Bugün henüz tamamlanan bir hedefin yok.")
else:
    for goal in completed_today:
        st.markdown(f"~~- {goal.get('goal', '')}~~ ✅")

# --- YENİ: Uzun Vadeli Hedefler Bölümü ---
st.markdown("---")
st.subheader("🏁 Uzun Vadeli Hedefler")

long_term_goals = []
if all_goals_data:
    for date_key, day_goals_data in all_goals_data.items():
        # 'pending' anahtarı her zaman olmayabilir, kontrol et
        if "pending" in day_goals_data:
            for goal_id, goal_details in day_goals_data["pending"].items():
                if isinstance(goal_details, dict) and goal_details.get("type") == "longterm":
                    # ÖNEMLİ DÜZELTME: Tamamlanmış uzun vadeli hedefler burada listelenmez.
                    if not goal_details.get("is_checked"):
                         long_term_goals.append({"id": goal_id, "date": date_key, **goal_details})

if not long_term_goals:
    st.success("Henüz eklenmiş bir uzun vadeli hedefin yok.", icon="🏁")
else:
    for goal in long_term_goals:
        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
        with col1:
            st.markdown(f"**-** {goal.get('goal', '')}")
        with col2:
            if st.button("🏁", key=f"done_longterm_{goal['id']}", use_container_width=True):
                # Uzun vadeli hedefi tamamlandı olarak işaretle
                firebase_db.update_goal_check(user_id, goal['id'], goal['date'], True, id_token)
                st.rerun()
        with col3:
            if st.button("🗑️", key=f"delete_longterm_{goal['id']}", use_container_width=True):
                firebase_db.delete_goal_by_id(user_id, goal['id'], goal['date'], id_token)
                st.rerun()