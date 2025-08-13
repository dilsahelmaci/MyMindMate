# -*- coding: utf-8 -*-
"""
Ana Uygulama Başlangıç ve Yönlendirme Noktası (Main Entry Point).

Bu dosya, `streamlit run app.py` komutu ile çalıştırılan ana dosyadır.

Tek ve en önemli görevi, kullanıcının oturum durumunu (`session_state`) kontrol
etmek ve onu uygun sayfaya yönlendirmektir:
- Eğer kullanıcı giriş yapmışsa (`user_id` session'da varsa), Ana Sayfa'ya yönlendirilir.
- Eğer kullanıcı giriş yapmamışsa, Hoşgeldin sayfasına yönlendirilir.

Bu merkezi yönlendirme mantığı, uygulamanın farklı sayfalar arasında tutarlı
bir kullanıcı deneyimi sunmasını sağlar.
"""
import streamlit as st

if "user_id" in st.session_state:
    # Kullanıcı giriş yapmışsa, onu doğrudan Ana Sayfa'ya yönlendir.
    st.switch_page("pages/1_🏠_Ana_Sayfa.py")
else:
    # Kullanıcı giriş yapmamışsa, onu Hoşgeldin sayfasına yönlendir.
    st.switch_page("pages/0_👋_Hoş_Geldin.py")
