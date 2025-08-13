# -*- coding: utf-8 -*-
"""
Kullanıcı Giriş ve Kayıt Sayfası.

Bu sayfa, kullanıcıların mevcut hesaplarına giriş yapmaları veya yeni bir
hesap oluşturmaları için gerekli arayüzleri içerir. Streamlit'in `st.tabs`
özelliği kullanılarak "Giriş Yap" ve "Kayıt Ol" sekmeleri oluşturulmuştur.

İşleyiş:
- Giriş: Kullanıcı e-posta ve şifresini girer, `firebase_auth.firebase_login`
  fonksiyonu çağrılır. Başarılı olursa Ana Sayfa'ya yönlendirilir.
- Kayıt: Kullanıcı ad, e-posta, şifre ve saat dilimi bilgilerini girer.
  Kayıt süreci üç adımdan oluşur:
    1. `firebase_auth.firebase_register` ile kullanıcı Firebase Auth'a kaydedilir.
    2. `firebase_auth.firebase_login` ile yeni kullanıcı adına hemen giriş yapılır
       ve güvenli veritabanı işlemleri için bir `id_token` alınır.
    3. Alınan `id_token` ile `firebase_db.save_user_details_from_dict` fonksiyonu
       çağrılarak kullanıcının profil bilgileri Realtime Database'e kaydedilir.
"""
import streamlit as st
import pytz
from core import firebase_auth as auth
from core import firebase_db
from utils.style import inject_sidebar_styles

st.set_page_config(page_title="Giriş Yap", page_icon="🔐")

inject_sidebar_styles()

# --- Arayüz ---
st.title("MyMindMate'e Hoş Geldin! 🧠")

if "user_id" in st.session_state:
    st.success(f"Zaten giriş yaptınız: {st.session_state['user_email']}", icon="✅")
    if st.button("Devam Et"):
        st.switch_page("pages/1_🏠_Ana_Sayfa.py")
    st.stop()

login_tab, register_tab = st.tabs(["Giriş Yap", "Kayıt Ol"])

# --- Giriş Sekmesi ---
with login_tab:
    st.subheader("Giriş Yap")
    with st.form("login_form", clear_on_submit=False):
        login_email = st.text_input("E-posta", key="login_email")
        login_password = st.text_input("Şifre", type="password", key="login_pass")
        login_button = st.form_submit_button("Giriş Yap")

        if login_button:
            if not login_email or not login_password:
                st.warning("E-posta ve şifre alanları zorunludur.")
            else:
                success, msg = auth.firebase_login(login_email, login_password)
                if success:
                    st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                    st.switch_page("pages/1_🏠_Ana_Sayfa.py")
                else:
                    st.error(msg)

# --- Kayıt Ol Sekmesi ---
with register_tab:
    st.subheader("Yeni Hesap Oluştur")
    with st.form("register_form", clear_on_submit=True):
        reg_name = st.text_input("Adınız", key="reg_name")
        reg_email = st.text_input("E-posta", key="reg_email")
        reg_password = st.text_input("Şifre", type="password", key="reg_pass")
        
        # Yaygın saat dilimlerinin bir listesi
        common_timezones = [
            "UTC", "Europe/London", "Europe/Berlin", "Europe/Istanbul", 
            "America/New_York", "America/Chicago", "America/Los_Angeles",
            "Asia/Tokyo", "Asia/Dubai", "Australia/Sydney"
        ]
        # Kullanıcının varsayılan saat dilimini bulmaya çalış, bulamazsan UTC kullan
        try:
            default_tz = "Europe/Berlin" # Sizin için varsayılan
            default_index = common_timezones.index(default_tz)
        except (ImportError, ValueError):
            default_index = 0 # UTC

        reg_timezone = st.selectbox(
            "Saat Diliminiz", 
            options=common_timezones, 
            index=default_index,
            key="reg_tz",
            help="Uygulamanın size doğru zamanda 'günaydın' diyebilmesi için bu gereklidir."
        )

        register_button = st.form_submit_button("Kayıt Ol")

        if register_button:
            if not reg_name or not reg_email or not reg_password:
                st.warning("İsim, e-posta ve şifre alanları zorunludur.")
            elif len(reg_password) < 6:
                st.warning("Şifre en az 6 karakter olmalı.")
            else:
                # 1. Firebase Auth'a kaydet
                success, uid_or_error = auth.firebase_register(reg_email, reg_password)
                if success:
                    uid = uid_or_error
                    # 2. Kayıt sonrası otomatik giriş yap ve idToken al
                    login_success, _ = auth.firebase_login(reg_email, reg_password)
                    if login_success:
                        id_token = st.session_state.get("user_id_token")
                        
                        # 3. Alınan idToken ile kullanıcı detaylarını DB'ye kaydet
                        user_data = {
                            "name": reg_name,
                            "email": reg_email,
                            "timezone": reg_timezone,
                            "is_first_chat": True
                        }
                        firebase_db.save_user_details_from_dict(uid, user_data, id_token)

                        # Oturum durumuna kullanıcının adını ekle
                        st.session_state["user_name"] = reg_name
                        
                        st.success("Kayıt başarılı! Ana sayfaya yönlendiriliyorsunuz...")
                        st.switch_page("pages/1_🏠_Ana_Sayfa.py")
                    else:
                        st.error("Kayıt başarılı ancak otomatik giriş yapılamadı. Lütfen manuel olarak giriş yapın.")
                else:
                    st.error(uid_or_error)
 