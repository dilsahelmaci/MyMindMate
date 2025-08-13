# -*- coding: utf-8 -*-
"""
Kullanıcının Günlük Sayfası.

Bu sayfa, kullanıcının kişisel günlük girdilerini oluşturmasına ve
görüntülemesine olanak tanır.

İşleyiş:
1.  **Oturum Kontrolü:** Sayfaya sadece giriş yapmış kullanıcılar erişebilir.
2.  **Veri Çekme:** Sayfa yüklendiğinde, kullanıcının tüm geçmiş günlükleri
    Firebase'den tek seferde çekilir.
3.  **Filtreleme:** "Geçmiş Günlükler" başlığının altında bulunan "Yıl" ve "Ay"
    seçme kutuları ile kullanıcı, geçmiş günlüklerini tarihe göre filtreleyebilir.
4.  **Yeni Girdi Formu:** Kullanıcının bir tarih seçip o tarihe yeni bir
    günlük metni kaydetmesini sağlayan bir form bulunur.
5.  **Geçmiş Girdileri Listeleme:** Filtrelenmiş günlükler, en yeniden en
    eskiye doğru sıralanır ve bir `st.expander` (açılır/kapanır) liste
    içinde gösterilir.
"""
import streamlit as st
from datetime import date, datetime

from components.sidebar_info import render_sidebar_user_info
from core import firebase_db
from utils.style import inject_sidebar_styles


st.set_page_config(page_title="Günlüğüm", page_icon="📘")

# --- Oturum Kontrolü ---
if "user_id" not in st.session_state:
    st.warning("Bu sayfayı görüntülemek için lütfen giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
    st.stop()

inject_sidebar_styles()

render_sidebar_user_info()

user_id = st.session_state.get("user_id")
id_token = st.session_state.get("user_id_token")

# --- Veri Çekme ---
# Sayfa yüklendiğinde bir kereye mahsus tüm günlükleri çek
with st.spinner("Günlükleriniz yükleniyor..."):
    journals = firebase_db.get_journals(user_id, id_token)

# --- Arayüz ---

st.title("📘 Günlüğüm")
st.write("Her gün bir parça içini dök, duygularına kulak ver. Burada yazdıkların sadece sana ait 💭")

# Tarih seçimi (Artık basit bir widget, callback YOK)
selected_date = st.date_input(
    "Tarih seç", 
    value=date.today(), 
    key="journal_date"
)

# Günlük Yazma Formu - Artık otomatik doldurma yok
with st.form(key="journal_form", clear_on_submit=True):
    journal_text = st.text_area(
        "Yeni bir şeyler yaz...",
        key="journal_text_input", # Yeni ve temiz bir anahtar
        height=200
    )
    submitted = st.form_submit_button("Kaydet")

    if submitted:
        if journal_text.strip():
            date_key = str(selected_date)
            firebase_db.save_journal(user_id, date_key, journal_text, id_token)
            st.success("Günlüğünüz başarıyla kaydedildi!")
            st.rerun() # Sayfayı yenilemek, formu ve state'i doğal olarak sıfırlar
        else:
            st.warning("Kaydedilecek bir şey yazmadınız.")

# --- Geçmiş Günlükler ve Filtreleme Mantığı ---

if not journals:
    st.markdown("---")
    st.info("Henüz günlük eklemedin.", icon="✍️")
else:
    # 1. Tüm girdileri tek bir listeye topla ve sırala
    all_entries = []
    for date_str, daily_entries in journals.items():
        if isinstance(daily_entries, dict):
            for entry_id, entry_data in daily_entries.items():
                if isinstance(entry_data, dict):
                    # Tarih string'ini datetime nesnesine çevir
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                    all_entries.append({
                        "id": entry_id,
                        "date_obj": entry_date,
                        "date_str": date_str,
                        "timestamp": entry_data.get("timestamp", ""),
                        "text": entry_data.get("text", "")
                    })
    all_entries.sort(key=lambda x: (x["date_obj"], x["timestamp"]), reverse=True)

    st.markdown("---")
    st.markdown("<h3 style='font-size: 1.2rem; margin-bottom: 1rem;'>Geçmiş Günlükler</h3>", unsafe_allow_html=True)
    
    # 2. Filtreleme seçeneklerini oluştur ve ana ekranda göster
    available_years = sorted(list(set(entry['date_obj'].year for entry in all_entries)), reverse=True)
    month_map = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 
                 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}

    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Yıl Filtresi", ["Tümü"] + available_years)
    
    with col2:
        if selected_year != "Tümü":
            months_in_year = sorted(list(set(entry['date_obj'].month for entry in all_entries if entry['date_obj'].year == selected_year)))
            month_options_display = {month: month_map[month] for month in months_in_year}
            selected_month_name = st.selectbox("Ay Filtresi", ["Tümü"] + list(month_options_display.values()))
            
            selected_month = "Tümü"
            if selected_month_name != "Tümü":
                for num, name in month_options_display.items():
                    if name == selected_month_name:
                        selected_month = num
                        break
        else:
            # Yıl seçilmediyse ay filtresini gösterme veya devre dışı bırak
            selected_month = "Tümü"
            st.selectbox("Ay Filtresi", ["Tümü"], disabled=True)

    # 3. Girdileri seçilen filtrelere göre filtrele
    filtered_entries = all_entries
    if selected_year != "Tümü":
        filtered_entries = [entry for entry in filtered_entries if entry['date_obj'].year == selected_year]
    if selected_month != "Tümü":
        filtered_entries = [entry for entry in filtered_entries if entry['date_obj'].month == selected_month]

    # 4. Filtrelenmiş sonuçları göster
    st.markdown(f"**Filtrelenen Sonuçlar ({len(filtered_entries)} adet)**")
    
    if not filtered_entries:
        st.warning("Seçtiğiniz filtreye uygun günlük bulunamadı.")
    else:
        for entry in filtered_entries:
            # YERELLEŞTİRME DÜZELTMESİ: Ay ismini kendi Türkçe haritamızdan alıyoruz.
            # Bu, sistem dilinden bağımsız olarak her zaman Türkçe gösterim sağlar.
            day = entry['date_obj'].day
            month_tr = month_map[entry['date_obj'].month]
            year = entry['date_obj'].year
            display_date = f"{day} {month_tr} {year}"
            
            with st.expander(f"{display_date} - {entry.get('timestamp', '')}"):
                st.write(entry["text"])