# -*- coding: utf-8 -*-
"""
Firebase Konfigürasyon ve Başlatma Modülü.

Bu modül, Firebase uygulamasının merkezi olarak başlatılmasından sorumludur.
Projenin herhangi bir yerinden Firebase'e erişim gerektiğinde, bu modüldeki
fonksiyonlar kullanılır. Bu, konfigürasyonun tek bir yerden yönetilmesini sağlar.
"""

import streamlit as st
import pyrebase

def get_firebase_config():
    """Streamlit secrets'tan Firebase konfigürasyonunu çeker."""
    return dict(st.secrets["firebase"])

def initialize_firebase_app():
    """
    Yeni ve temiz bir Firebase uygulama bağlantısı başlatır.

    Bu fonksiyon, her çağrıldığında `secrets.toml` dosyasındaki
    konfigürasyon bilgilerini kullanarak taze bir Pyrebase uygulama
    nesnesi oluşturur. Bu, özellikle kimlik doğrulama gibi hassas
    işlemlerde state'in karışmasını engeller.

    Returns:
        pyrebase.pyrebase.Firebase: Yeni başlatılmış Firebase uygulama nesnesi.
    """
    config = get_firebase_config()
    return pyrebase.initialize_app(config)
