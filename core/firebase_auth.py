# -*- coding: utf-8 -*-
"""
Firebase Kimlik Doğrulama (Authentication) İşlemleri Modülü.

Bu modül, kullanıcıların uygulamaya kaydolması (register), giriş yapması (login)
ve hesaplarını silmesi (delete) gibi tüm kimlik doğrulama işlemlerini yönetir.
Tüm fonksiyonlar, `core.firebase_config` üzerinden temiz bir Firebase bağlantısı
alarak çalışır.
"""

import streamlit as st
from core.firebase_config import initialize_firebase_app
from core import firebase_db

def firebase_login(email: str, password: str):
    """
    Kullanıcıyı Firebase ile doğrular ve başarılı olursa session state'i kurar.

    Args:
        email (str): Kullanıcının e-posta adresi.
        password (str): Kullanıcının şifresi.

    Returns:
        tuple[bool, str | None]: (Başarı durumu, Hata mesajı veya None)
    """
    firebase_app = initialize_firebase_app()
    auth = firebase_app.auth()
    try:
        # 1. Firebase'e giriş yapmayı dene
        user = auth.sign_in_with_email_and_password(email, password)
        id_token = user['idToken']

        # 2. Firebase'den kullanıcının UID (unique ID) bilgisini al
        info = auth.get_account_info(id_token)
        uid = info['users'][0]['localId']

        # 3. Veritabanından diğer kullanıcı detaylarını (örn: isim) çek
        # Bu işlem için `id_token` yetkilendirme amacıyla kullanılır.
        user_details = firebase_db.get_user_details(uid, id_token)
        user_name = user_details.get("name", "Kullanıcı") # İsim yoksa varsayılan ata

        # 4. Başarılı girişte Streamlit session state'i kur
        # Bu bilgiler, uygulama boyunca kullanıcıyı tanımak için kullanılır.
        st.session_state["user_id"] = uid
        st.session_state["user_email"] = email
        st.session_state["user_name"] = user_name
        st.session_state["user_id_token"] = id_token # Bu token, güvenli DB işlemleri için kritik.
        
        return True, None
    except Exception as e:
        # Hata durumunda, kullanıcıya anlaşılır bir mesaj döndür.
        err = str(e)
        if "INVALID_EMAIL" in err:
            return False, "Lütfen geçerli bir e-posta adresi girin."
        elif "INVALID_PASSWORD" in err or "EMAIL_NOT_FOUND" in err:
            return False, "E-posta veya şifre hatalı."
        elif "TOO_MANY_ATTEMPTS_TRY_LATER" in err:
            return False, "Çok fazla deneme yapıldı, lütfen daha sonra tekrar deneyin."
        else:
            # Diğer tüm beklenmedik hatalar için genel bir mesaj göster.
            return False, "Giriş sırasında bir hata oluştu."

def firebase_register(email: str, password: str):
    """
    Firebase Authentication sisteminde yeni bir kullanıcı oluşturur.

    Not: Bu fonksiyon sadece kullanıcıyı Auth sistemine kaydeder,
    otomatik olarak giriş yapmaz veya veritabanına profil oluşturmaz.
    Bu adımlar, bu fonksiyon çağrıldıktan sonra arayüz katmanında yönetilir.

    Args:
        email (str): Yeni kullanıcının e-posta adresi.
        password (str): Yeni kullanıcının şifresi.

    Returns:
        tuple[bool, str]: (Başarı durumu, Kullanıcı ID'si veya Hata mesajı)
    """
    firebase_app = initialize_firebase_app()
    auth = firebase_app.auth()
    try:
        # Firebase'de e-posta/şifre ile yeni bir kullanıcı hesabı oluştur.
        user = auth.create_user_with_email_and_password(email, password)
        uid = user['localId']
        return True, uid
    except Exception as e:
        # Yaygın kayıt hatalarını yakala ve kullanıcıya bildir.
        err = str(e)
        if "INVALID_EMAIL" in err:
            return False, "Lütfen geçerli bir e-posta adresi girin."
        elif "EMAIL_EXISTS" in err:
            return False, "Bu e-posta adresi zaten kayıtlı."
        elif "WEAK_PASSWORD" in err:
            return False, "Şifre en az 6 karakter olmalı."
        else:
            return False, "Kayıt sırasında bir hata oluştu."

def delete_firebase_user():
    """
    Oturumu açık olan kullanıcının hesabını Firebase Authentication'dan kalıcı olarak siler.

    Bu işlem geri alınamaz. Veritabanındaki verilerin de ayrıca silinmesi gerekir.

    Returns:
        tuple[bool, str]: (Başarı durumu, Bilgi veya Hata mesajı)
    """
    firebase_app = initialize_firebase_app()
    auth = firebase_app.auth()
    try:
        # Silme işlemi için session'da saklanan `id_token` kullanılır.
        # Bu, sadece mevcut kullanıcının kendi hesabını silebilmesini sağlar.
        id_token = st.session_state.get("user_id_token")
        if id_token:
            auth.delete_user_account(id_token)
            return True, "Kullanıcı başarıyla silindi."
        else:
            # Eğer bir şekilde token yoksa, güvenlik için işlemi durdur.
            return False, "Oturum token'ı bulunamadı. Silme işlemi için yeniden giriş yapmanız gerekebilir."
    except Exception as e:
        return False, f"Hesap silinirken bir hata oluştu: {e}"