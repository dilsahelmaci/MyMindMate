# -*- coding: utf-8 -*-
"""
Ana Sayfa (Dashboard).

Bu sayfa, kullanıcı giriş yaptıktan sonra karşılaştığı ana ekrandır.
Kullanıcıya özel bir karşılama sunar ve uygulamanın ana modüllerine
hızlı erişim sağlar.

İşleyiş:
1.  **Oturum Kontrolü:** Sayfanın en başında kullanıcının oturum açıp açmadığı
    kontrol edilir. Oturum yoksa, kullanıcı giriş sayfasına yönlendirilir.
2.  **Veri Çekme:** Kullanıcının haftalık özetini ve hızlı erişim kartlarındaki
    önizlemeleri göstermek için Firebase'den günlük ve hedef verileri çekilir.
3.  **Kişisel Karşılama:** Kullanıcının ismini ve günün sözünü içeren bir
    karşılama bölümü gösterilir.
4.  **Haftalık Özet:** Son 7 gün içinde yazılan günlük sayısı ve tamamlanan
    hedef sayısı hesaplanarak kullanıcıya bir ilerleme özeti sunulur.
5.  **Hızlı Erişim Kartları:** "Sohbet", "Günlüğüm" ve "Hedeflerim" sayfalarına
    yönlendiren, her birinin altında son aktiviteye dair küçük bir önizleme
    içeren interaktif kartlar gösterilir.
"""
import streamlit as st
from datetime import date, timedelta
import pytz

from utils.style import inject_sidebar_styles
from components.sidebar_info import render_sidebar_user_info
from core import firebase_db
from utils.quotes import get_random_quote


st.set_page_config(page_title="Ana Sayfa", page_icon="🏠")

inject_sidebar_styles()
render_sidebar_user_info()

# --- Oturum Kontrolü ---
if "user_id" not in st.session_state:
    st.warning("Bu sayfayı görüntülemek için lütfen giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
    st.stop()

user_id = st.session_state.get("user_id")
user_name = st.session_state.get("user_name", "Kullanıcı")
id_token = st.session_state.get("user_id_token")

# --- Veri Çekme ---
# Token olmadan işlem yapma
if not id_token:
    st.error("Oturumunuz zaman aşımına uğradı. Lütfen tekrar giriş yapın.")
    st.stop()

# Son günlüğü ve hedefleri çek (id_token ile)
journals = firebase_db.get_journals(user_id, id_token)
goals = firebase_db.get_goals(user_id, id_token)

# --- Arayüz ---
st.title(f"Tekrar Hoş Geldin, {user_name}! 👋")

# Kullanıcı giriş yaptıysa kişisel karşılama
st.markdown(f"""
    <div style="background-color:#E0F2F1; border-left: 6px solid #4DB6AC; border-radius:10px; padding:20px; margin-bottom:20px;">
        <h2 style="margin-top:0;">👋 Hoş geldin, {user_name}!</h2>
        <p>Bugün nasıl hissediyorsun? Sohbet etmek, hedef belirlemek ya da bir şeyler yazmak ister misin?</p>
    </div>
""", unsafe_allow_html=True)

# --- Günün Sözü ---
quote, author = get_random_quote()
author_line = f'<p style="text-align:right; font-weight: bold; color: #4DB6AC;">- {author}</p>' if author else ''
st.markdown(f"""
<div style="text-align:center; padding: 10px; border: 1px dashed #4DB6AC; border-radius:10px; margin-bottom: 20px;">
    <p style="font-style: italic; font-size: 1.1em; margin-bottom: 5px;">"{quote}"</p>
    {author_line}
</div>
""", unsafe_allow_html=True)


# --- Haftalık Özet Hesaplama---
today = date.today()
last_week = today - timedelta(days=7)

journal_count = 0
if journals:
    for a_date in journals.keys():
        if last_week <= date.fromisoformat(a_date) <= today:
            journal_count += len(journals[a_date])

completed_goals_count = 0
if goals:
    for a_date_str, day_goals in goals.items():
        # Tarih aralığını kontrol et
        if last_week <= date.fromisoformat(a_date_str) <= today:
            # "pending" klasörünün içine bak
            pending_goals = day_goals.get("pending", {})
            if pending_goals:
                # Üzerinde "is_checked: True" etiketi olanları say
                for goal_details in pending_goals.values():
                    if isinstance(goal_details, dict) and goal_details.get("is_checked") is True:
                        completed_goals_count += 1

if journal_count > 0 or completed_goals_count > 0:
    summary_text = f"Bu hafta harika gidiyorsun! Şu ana kadar **{journal_count}** günlük yazdın ve **{completed_goals_count}** hedefini tamamladın. 💪"
    st.success(summary_text, icon="✨")
else:
    st.info("Bu hafta yeni bir başlangıç yapmaya ne dersin? Bir hedef belirle veya bir şeyler yaz! 🚀")


st.markdown("---")
st.markdown("#### Hızlı Erişim")

# Kartlar için özel stil
st.markdown("""
<style>
    div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        background-color: #fcfcfc;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.02);
        transition: 0.3s;
    }
    div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"]:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.05);
        border: 1px solid #4DB6AC;
    }
</style>
""", unsafe_allow_html=True)


col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("### 💬 Sohbet")
    st.caption("Yapay zeka dostunla sohbet et, aklındakileri paylaş ve yeni bakış açıları kazan.")
    st.page_link("pages/2_💬_Sohbet.py", label="Sohbete Başla →", use_container_width=True)

with col2:
    st.markdown("### 📘 Günlüğüm")
    st.caption("Düşüncelerini, hislerini ve gün içinde yaşadıklarını güvenle kaydet. Kendini keşfet.")
    
    # VERİTABANINDAN TEKRAR VERİ ÇEKMEK YERİNE MEVCUT OLANI KULLAN
    # journals = firebase_db.get_journals(user_id) 
    if journals:
        last_date = sorted(journals.keys(), reverse=True)[0]
        last_entry = list(journals[last_date].values())[0]
        preview_text = last_entry['text'][:50] + "..." if len(last_entry['text']) > 50 else last_entry['text']
        st.markdown(f'<div style="background-color:#E0F2F1; padding:10px; border-radius:8px; color:#004D40; margin-bottom:10px;">Son girdin: <i>"{preview_text}"</i></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#E0F2F1; padding:10px; border-radius:8px; color:#004D40; margin-bottom:10px;">Henüz hiç günlük yazmadın.</div>', unsafe_allow_html=True)
        
    st.page_link("pages/3_📘_Günlüğüm.py", label="Günlüğüme Git →", use_container_width=True)

with col3:
    st.markdown("### 🎯 Hedeflerim")
    st.caption("Günlük ve uzun vadeli hedeflerini belirle, adımlarını takip et ve gelişimini izle.")

    today_str = date.today().isoformat()
    # VERİTABANINDAN TEKRAR VERİ ÇEKMEK YERİNE MEVCUT OLANI KULLAN
    # goals = firebase_db.get_goals(user_id)
    pending_goals = []
    
    has_goals_today = goals and today_str in goals and (goals[today_str].get("pending") or goals[today_str].get("completed"))

    if has_goals_today:
        if "pending" in goals[today_str]:
            for goal_data in goals[today_str]["pending"].values():
                if isinstance(goal_data, dict) and not goal_data.get("is_checked"):
                    pending_goals.append(goal_data["goal"])
        
        if pending_goals:
            st.markdown(f'<div style="background-color:#E0F2F1; padding:10px; border-radius:8px; color:#004D40; margin-bottom:10px;">Bugün yapılacaklar: <i>"{pending_goals[0]}"</i></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color:#E0F2F1; padding:10px; border-radius:8px; color:#004D40; margin-bottom:10px;">Bugün için tüm hedeflerin tamamlandı! 🎉</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#E0F2F1; padding:10px; border-radius:8px; color:#004D40; margin-bottom:10px;">Bugün için bir hedefin yok.</div>', unsafe_allow_html=True)

    st.page_link("pages/4_🎯_Hedeflerim.py", label="Hedeflerimi Gör →", use_container_width=True)
