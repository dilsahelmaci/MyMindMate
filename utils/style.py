import streamlit as st

def inject_sidebar_styles():
    """
    Injects custom CSS to style the sidebar and its navigation links.
    This function should be called at the top of each page script.
    """
    css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');

    /* Genel uygulama fontunu ayarla */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar'ın kendisine stil uygula */
    section[data-testid="stSidebar"] {
        background-color: #FFFBEF !important;
    }

    /* Sidebar navigasyon linkleri için genel stil */
    [data-testid="stSidebarNav"] ul li a {
        display: block;
        background-color: #FFF4E0; /* Sıcak sarı */
        border-radius: 10px;
        color: #333 !important;
        padding: 10px;
        margin: 8px 0;
        transition: background-color 0.2s ease, color 0.2s ease;
        text-decoration: none;
    }

    /* Linklerin üzerine gelindiğinde (hover) stil */
    [data-testid="stSidebarNav"] ul li a:hover {
        background-color: #FFE0B2; /* Vurgulu sarı */
        color: #000 !important;
    }

    /* Aktif/seçili sayfanın link stili */
    [data-testid="stSidebarNav"] ul li a[aria-current="page"] {
        background-color: #FFE0B2; /* Vurgulu sarı */
        font-weight: bold;
    }

    /* "app" linkini gizle */
    [data-testid="stSidebarNav"] ul li:first-child {
        display: none;
    }

    /* --- Bilgilendirme Kutusu Stilleri --- */

    /* Genel Bilgi (st.info, st.success) */
    [data-testid="stAlert"][kind="info"], [data-testid="stAlert"][kind="success"] {
        background-color: #E0F2F1;
        border: 1px solid #4DB6AC;
        color: #004D40;
    }
    [data-testid="stAlert"][kind="info"] .st-emotion-cache-1pxazr7,
    [data-testid="stAlert"][kind="success"] .st-emotion-cache-1pxazr7 {
        color: #004D40;
    }

    /* Uyarı (st.warning) */
    [data-testid="stAlert"][kind="warning"] {
        background-color: #FFFBEB;
        border: 1px solid #FFC107;
        color: #B36D00;
    }
    [data-testid="stAlert"][kind="warning"] .st-emotion-cache-1pxazr7 {
        color: #B36D00;
    }
    
    /* Hata (st.error) */
    [data-testid="stAlert"][kind="error"] {
        background-color: #FFEBEE;
        border: 1px solid #F44336;
        color: #C62828;
    }
    [data-testid="stAlert"][kind="error"] .st-emotion-cache-1pxazr7 {
        color: #C62828;
    }

</style>
"""
    st.markdown(css, unsafe_allow_html=True)
