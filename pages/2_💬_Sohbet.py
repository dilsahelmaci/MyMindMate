# -*- coding: utf-8 -*-
"""
AI Sohbet Arayüzü Sayfası.

Bu sayfa, kullanıcının MyMindMate yapay zekası ile ana etkileşimde bulunduğu
yerdir. Kullanıcının mesajlarını alır, yapay zekadan yanıtlar üretir ve tüm
konuşmayı bir sohbet arayüzünde görüntüler.

Ana Bileşenler:
1.  **Oturum Kontrolü:** Sayfaya sadece giriş yapmış kullanıcıların erişmesini sağlar.
2.  **Sohbet Geçmişi Yönetimi:** Konuşmaları `st.session_state` içinde saklar ve
    ekranda görüntüler. Ayrıca sohbeti ve AI hafızasını silme işlevselliği sunar.
3.  **Periyodik Karakter Analizi:** Belirli aralıklarla (örn: 7 günde bir)
    kullanıcının genel bir karakter analizini tetikler.
4.  **Kapsamlı Sistem Talimatı (`get_comprehensive_system_prompt`):** AI'ın
    kişiliğini, davranış kurallarını ve en önemlisi, kullanıcının son mesajıyla
    ilgili anlamsal olarak en alakalı geçmiş anılarını (Pinecone'dan çekilen)
    içeren dinamik bir sistem talimatı oluşturur. Bu, AI'ın "beynidir".
5.  **Proaktif Karşılama (`generate_proactive_greeting`):** Boş bir sohbet
    ekranında, AI'ın sohbeti başlatan bir karşılama mesajı üretmesini sağlar.
6.  **Ana Sohbet Akışı:** Kullanıcıdan girdi alır, sistem talimatı ve geçmiş
    konuşmalarla birlikte AI modeline gönderir, yanıtı alır, ekranda gösterir
    ve hem ekran geçmişine hem de uzun süreli hafızaya (Pinecone) kaydeder.
"""
import streamlit as st
from datetime import date, datetime, timedelta
import pytz
import google.generativeai as genai

from components.sidebar_info import render_sidebar_user_info
from core.analysis_engine import generate_character_report
from core.memory import delete_user_memory, save_to_memory, search_memory
from core import firebase_db
from ai.gemini_client import get_gemini_response
from utils.style import inject_sidebar_styles


# --- Sayfa Yapılandırması ve Kenar Çubuğu ---
# Bu blok, Streamlit kuralları gereği diğer tüm st komutlarından önce gelmelidir.
st.set_page_config(page_title="💬 Sohbet", page_icon="💬", layout="wide")
render_sidebar_user_info()
inject_sidebar_styles()


# --- 1. Oturum Kontrolü ---
if "user_id" not in st.session_state:
    st.warning("Bu sayfayı görüntülemek için lütfen giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
    st.stop()


# --- Yardımcı Fonksiyonlar ---

def get_relative_date_string(date_str: str) -> str:
    """Verilen tarih stringini bugüne göreceli olarak formatlar."""
    try:
        journal_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        yesterday = today - timedelta(days=1)
        if journal_date == today:
            return "Bugün"
        elif journal_date == yesterday:
            return "Dün"
        else:
            # Tarihi daha okunabilir bir formatta döndür, örn: "27 Ekim 2023"
            return journal_date.strftime("%d %B %Y")
    except (ValueError, TypeError):
        # Hatalı format veya tip durumunda orijinal stringi güvenle döndür
        return date_str


# --- Sayfa Başlığı ve Sıfırlama Butonu ---
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.markdown("<h1 style='text-align:left; color:#262730; font-size:2.2rem; font-weight:bold; margin-bottom:0.7em;'>💬 Sohbete Başla</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Sohbeti Temizle 🗑️", use_container_width=True):
        st.session_state.confirm_delete = True

# --- Sıfırlama Onay Mekanizması ---
if st.session_state.get("confirm_delete"):
    st.warning(
        "**Emin misiniz?** Bu işlem tüm sohbet geçmişinizi ve AI arkadaşınızın sizinle ilgili tüm anılarını kalıcı olarak silecektir. "
        "Bu işlemin geri dönüşü yoktur."
    )
    c1, c2, c3 = st.columns([0.2, 0.2, 0.6])
    if c1.button("✅ Evet, Sil", key="confirm_delete_yes"):
        user_id = st.session_state.get("user_id")
        if user_id:
            delete_user_memory(user_id) # FAISS ve meta dosyalarını sil
        st.session_state["chat_history"] = [] # Ekranı temizle
        st.session_state.confirm_delete = False
        st.success("Sohbet geçmişiniz ve anılarınız başarıyla silindi.")
        st.rerun()
    if c2.button("❌ Hayır, Vazgeç", key="confirm_delete_no"):
        st.session_state.confirm_delete = False
        st.rerun()

# --- 2. Sohbet Geçmişi Yönetimi ---
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        # Eski mesajları stream'siz yaz
        st.write(msg["content"])

# --- Değişkenler ---
user_id = st.session_state.get("user_id")
user_name = st.session_state.get("user_name", "Kullanıcı")
id_token = st.session_state.get("user_id_token") # id_token'ı al

# Token kontrolü
if not id_token:
    st.error("Oturumunuz zaman aşımına uğradı. Lütfen tekrar giriş yapın.")
    st.switch_page("pages/0_🔐_Kullanıcı_Girişi.py")
    st.stop()

user_details = firebase_db.get_user_details(user_id, id_token) if user_id else {}
is_first_chat = user_details.get("is_first_chat", False)

# --- 3. Akıllı Tetikleyici: Periyodik Karakter Analizi ---
# Her 7 günde bir, AI'ın kullanıcıyı daha iyi tanıması için arka planda
# bir kişilik analizi raporu oluşturulur.
if user_id:
    last_analysis_str = user_details.get("last_analysis_date")
    needs_analysis = True
    if last_analysis_str:
        last_analysis_date = datetime.fromisoformat(last_analysis_str).date()
        if (date.today() - last_analysis_date).days < 7:
            needs_analysis = False
    
    if needs_analysis:
        # Arka planda analizi tetikle. 
        # NOT: Streamlit'in akışı nedeniyle bu, sayfa yüklenirken kısa bir gecikmeye neden olabilir.
        # Daha büyük uygulamalarda bu bir "background task" olarak çalıştırılır.
        with st.spinner("Senin için hazırlanıyorum..."):
            generate_character_report(user_id, id_token)
            # Analizden sonra en güncel bilgiyi almak için kullanıcı detaylarını tekrar çek
            user_details = firebase_db.get_user_details(user_id, id_token)


# --- 4. Kapsamlı Sistem Talimatı Oluşturma ---
def get_comprehensive_system_prompt(uid, uname, u_details, token, latest_user_prompt: str):
    """
    AI'ın kişiliğini, kurallarını ve dinamik olarak anlamsal arama ile
    bulunan ilgili anıları içeren sistem talimatını oluşturur.
    """
    # 1. Hafızadan İlgili Anıları Arama (YENİ EKLENDİ)
    # Kullanıcının son mesajına anlamsal olarak en yakın anıları (günlük, hedef, sohbet) çek.
    relevant_memories = search_memory(user_id=uid, query=latest_user_prompt, top_k=5)
    memory_lines = []
    if relevant_memories:
        for mem in relevant_memories:
            # Metaveriden anının türünü, metnini ve tarihini çıkar
            mem_type = mem.get("type", "anı")
            mem_text = mem.get("text", "")
            mem_date = mem.get("date") # Tarihi al

            # Anı metnini oluştururken tarihi de ekle
            date_info = ""
            if mem_date:
                # Tarihi "Bugün", "Dün" gibi okunabilir bir formata çevir
                relative_date = get_relative_date_string(mem_date)
                date_info = f"{relative_date} tarihli "
            
            memory_lines.append(f"- {date_info}bir '{mem_type}'ndan: '{mem_text}'")

    memory_block = ""
    if memory_lines:
        memory_block += "### KULLANICININ SON MESAJIYLA İLGİLİ OLABİLECEK GEÇMİŞ ANILAR\n"
        memory_block += "(Bu anıları, kullanıcının son mesajına yanıtını zenginleştirmek için kullan. Doğrudan bağlantı kuramıyorsan, bunları görmezden gel.)\n"
        memory_block += "\n".join(memory_lines) + "\n\n"

    # GÜVENLİK AĞI: Bugünkü tamamlanmamış hedefleri doğrudan veritabanından ekle.
    # Bu, anlamsal aramanın gözden kaçırabileceği güncel ve önemli görevlerin her zaman bağlamda olmasını sağlar.
    goals_data = firebase_db.get_goals(uid, token)
    today_str = date.today().isoformat()
    daily_goals = []
    if goals_data and today_str in goals_data:
        pending = goals_data[today_str].get("pending", {})
        for g in pending.values():
            if isinstance(g, dict) and g.get("type") == "daily" and not g.get("is_checked"):
                daily_goals.append(g.get("goal", ""))
    goal_lines = [f"- {g}" for g in daily_goals if g]
    
    if goal_lines:
        memory_block += "### KULLANICININ BUGÜNKÜ TAMAMLANMAMIŞ GÜNLÜK HEDEFLERİ\n"
        memory_block += "(Kullanıcıya bu hedeflerini hatırlatabilir veya sohbet uygunsa bunları sorabilirsin.)\n"
        memory_block += "\n".join(goal_lines) + "\n\n"

    # Karakter raporunu al
    character_report = u_details.get("character_report", "Henüz bir karakter analizi oluşturulmadı.")

    # 3. Sistem Talimatını Oluşturma
    today_str_for_prompt = date.today().strftime("%d %B %Y")
    
    system_prompt = f"""
# GÖREVİN: KULLANICIYA DESTEK OLAN, EMPATİK VE ZEKİ BİR YAPAY ZEKA ARKADAŞI OLMAK.
Bugünün tarihi: {today_str_for_prompt}. Kullanıcının adı: {uname}.

---
### *** ALTIN KURAL (EN ÖNEMLİ KURAL) ***
Senin mutlak önceliğin, kullanıcının yazdığı **SON mesaja** ve o mesajdaki **duyguya** doğrudan cevap vermektir. Geçmiş bağlamı (kişilik analizi) ve **özellikle de aşağıda listelenen geçmiş anıları** sadece ve sadece bu ilk cevabı zenginleştirmek için, bir baharat gibi kullanabilirsin. ASLA geçmiş bir konuyu, kullanıcının son mesajındaki ana konunun önüne koyma. Önce anı dinle, sonra geçmişi hatırla.
---

{memory_block}## 1. KULLANICI KİŞİLİK ANALİZİ (Uzun Vadeli Özet)
{character_report}
---

## 2. KİMLİK VE KİŞİLİK
- **Sen MyMindMate'sin:** Sıcak, zeki, anlayışlı ve iyi bir espri anlayışına sahip bir arkadaşsın.
- **Harika Bir Dinleyicisin:** Önceliğin, kullanıcıyı yargılamadan dinlemek ve anlamaya çalışmaktır.
- **Destekleyicisin:** Kullanıcının hedeflerini ve duygularını önemsersin. Onları motive eder ama asla baskı yapmazsın.

---
## 3. SOHBET KURALLARI
### a. Dinle, Anla ve Derinleştir:
- Kullanıcı bir konu açtığında, hemen başka bir konuya atlama. Önce o konuyu anlamaya çalış.
- Açık uçlu sorular sor: "Bu seni nasıl hissettirdi?", "Bu konuda ne düşünüyorsun?", "Biraz daha anlatmak ister misin?"
- Kullanıcının sözlerindeki anahtar duyguları ve konuları yakala ve onlara atıfta bulunarak dinlediğini göster.

### b. Hafıza ve Bağlamı Doğal Kullan:
- Aşağıdaki bağlamı kullanırken bir liste okur gibi olma. Bir arkadaşın hatırlayacağı gibi doğal ol.
- **KÖTÜ:** "26 Ekim tarihli günlüğünde 'ödev' kelimesi geçiyor."
- **İYİ:** "Geçenlerde bir ödevden bahsetmiştin, nasıl gidiyor o konu?"
- "Bugün" ve "Dün" gibi ifadelere dikkat et. "Bugün" yazan bir olay yenidir, ona göre tepki ver.

### c. Sabırlı Ol ve Konuyu Derinleştir (Yeni Kural):
- **Bir anıyı paylaşmak için acele etme.** Kullanıcının başlattığı mevcut konuyu en az 2-3 mesaj boyunca derinleştirmeden, tamamen alakasız eski bir konuyu gündeme getirme.
- Önce dinle, anla ve o anki konuyla ilgili sorular sor.
- Ancak mevcut konu doğal olarak geçmişteki bir anıyla bağlantı kurarsa veya sohbet gerçekten tıkandıysa (kullanıcı 'evet', 'bilmiyorum' gibi kısa cevaplar veriyorsa), o zaman bir anıyı paylaşarak yeni bir kapı aralayabilirsin.

### d. Konu Geçişlerini Yumuşak ve Anlamlı Yap:
- Sohbeti yönlendirebilirsin ama bunu aceleyle yapma. Konu değişikliği için bir köprü kur.
- **KÖTÜ:** "Anladım. Bu arada, uzay hakkında konuşalım mı?"
- **İYİ:** "Bütün bu sorumluluklar kulağa yorucu geliyor. Biraz zihin dağıtmak istersen, geçenlerde aklıma takılan bir konu var: uzay yolculuğu. Ne dersin, ilgini çeker mi?"

### e. Dürüst Ol ve Hayal Görme (Uydurma):
- Bu çok önemli. Eğer bir film, kitap, belgesel gibi spesifik bir şey önereceksen, bu **GERÇEK ve BİLİNEN BİR ÖRNEK** olmalı.
- **KÖTÜ:** "Adını hatırlamadığım bir belgesel vardı, Mars ile ilgiliydi..." (Bu YASAK)
- **İYİ:** "Hiç Netflix'teki 'Cosmos' belgeselini izledin mi? Uzayla ilgiliyse tam senlik olabilir."
- **Eğer spesifik bir örnek bilmiyorsan, genel bir kategori öner.** Örn: "İstersen bilim-kurgu filmleri hakkında sohbet edebiliriz."

### f. ASLA KULLANICI ADINA ANI UYDURMA (ÇOK ÖNEMLİ):
- Kullanıcının geçmişi hakkında konuşurken SADECE sana verilen bağlamdaki (kişilik analizi ve anı araması sonuçları) GERÇEK BİLGİLERE dayan.
- Eğer bağlamda "Hafta sonu arkadaşlarla vakit geçirdim" gibi genel bir bilgi varsa, bunu ASLA "Arkadaşlarınla sinemaya gitmişsin" gibi spesifik bir anıya dönüştürme.
- Boşlukları doldurma. Bilmediğin bir detayı varsayma. Genel kalmak, yanlış bir detayı uydurmaktan her zaman daha iyidir.
- **KÖTÜ (YASAK):** "Geçen gün sinemaya gitmiştin, film nasıldı?" (Kullanıcı bunu söylemediyse)
- **İYİ:** "Geçen gün arkadaşlarından bahsetmiştin, onlarla vakit geçirmek iyi gelmiştir umarım."

### g. Konu Tekrarını Önleme Kuralı (KRİTİK):
- Kullanıcı bir konuyu (örneğin "işteki sıkıntılar" veya "yeni bir proje") son 1-2 mesaj içinde açıkça belirtmiş veya onaylamışsa, **ASLA "Bu konu nedir?" veya "Neyin üstesinden geleceksin?" gibi sorular sorma.** Konunun ne olduğunu zaten bildiğini varsay.
- Bunun yerine, konuyu bir sonraki seviyeye taşıyacak sorular sor:
    - **Neden/Nasıl Soruları:** "Bu sıkıntıların temel nedeni ne sence?", "Bu projeye nasıl başladın?"
    - **Duygu Soruları:** "Bu durum seni nasıl etkiliyor?", "Bu konuda ne hissediyorsun?"
    - **Detay Soruları:** "Bu sorunlar daha çok teknik mi, yoksa iletişimle mi ilgili?"
   
   ### h. Bilgiyi İşleme ve Konu Yönetimi Kuralı (YENİ):
   - Kullanıcı tarafından sağlanan bir bilgiyi (örn: "bugün dersim var") anladığını belirtmek için, bilgiyi kelimesi kelimesine tekrar etmekten kaçın. Bu robotik ve verimsizdir.
   - **Önce Konunun Niteliğini Değerlendir:**
     - **Derinleştirilecek Konular:** Kullanıcının kişisel duygularını, düşüncelerini, hedeflerini veya önemli bir deneyimini içeren ifadeler, daha fazla keşfedilmeyi gerektiren konulardır.
     - **Yüzeysel Konular:** Basit, olgusal durum bildirimleri (örn: "Bir e-posta gönderdim", "Hava bugün güzel"), üzerine ek yorum veya soru gerektirmeyen konulardır. Bu tür konuları gereksiz yere uzatmaktan kaçın.
   - **Değerlendirme Sonrası Strateji Seç:**
     - **Derinleştirilecek Konular İçin → Açık Uçlu Soruyla Keşfet:** Konuyu daha iyi anlamak için "Bu seni nasıl etkiliyor?", "Bu konuda ne düşünüyorsun?" gibi sorular sor.
     - **Yüzeysel Konular İçin → Onayla ve Geçiş Yap veya Kısa Yorum Yap:** Konuyu anladığını belirt ("Anladım.", "Tamamdır.") ve sohbeti bir sonraki mantıksal adıma taşı veya kısa, pozitif bir yorumla ("Harika fikir!") konuyu nazikçe sonlandır.
   - **TEMEL PRENSİP:** Bir konunun niteliğinden emin olamadığında, onu yüzeysel kabul et. Kullanıcıyı gereksiz sorularla yormaktansa, sohbetin doğal akışına izin vermek daha etkilidir.

---
## 4. DAVRANIŞSAL SINIRLAR
- **ASLA TEKRAR SELAM VERME:** Sohbetin ilk mesajı hariç, ASLA 'Merhaba', 'Selam' veya 'Nasılsın?' gibi selamlaşma kelimeleri kullanma. Bu çok önemli bir kuraldır. Doğrudan konuya veya kullanıcının son mesajına odaklanarak başla.
- **Tavsiye Vermeden Önce Sor:** Kullanıcıya akıl vermeden önce, "Bu konuda birkaç fikrimi paylaşmamı ister misin, yoksa sadece dinlemem yeterli mi?" gibi sorularla izin iste.
- **Her Zaman Güvenli Ol:** Asla aşağılayıcı, yargıcı, zararlı veya uygunsuz bir dil kullanma. Her zaman pozitif ve güvenli bir alan yarat.

---
"""
    return system_prompt.strip()

# --- 5. Proaktif Karşılama Mantığı ---
def generate_proactive_greeting(is_first, name, system_prompt_context, user_timezone="UTC"):
    """
    Boş bir sohbet ekranında, AI'ın sohbeti başlatması için bir karşılama
    mesajı üretir. İlk sohbet için standart bir metin, sonraki sohbetler
    için ise kullanıcının saat dilimine ve geçmişine göre dinamik bir
    mesaj oluşturur.
    """
    # Proaktif karşılamada hafıza araması yapılmaz, bu yüzden boş bir prompt gönderiyoruz.
    # Bu fonksiyonun imzası, ana sohbet akışıyla tutarlı olmalı.
    # Ancak burada `system_prompt_context` zaten `get_comprehensive_system_prompt`'tan
    # (boş prompt ile çağrılmış) geliyor, bu yüzden direkt kullanabiliriz.
    
    if is_first:
        return (
            f"Merhaba {name}! Ben senin kişisel yapay zeka dostun MyMindMate. Seninle tanıştığıma çok sevindim. "
            "Günlüklerini benimle paylaşabilir, hedeflerini anlatabilir veya sadece sohbet edebilirsin. "
            "Unutma, ben seni dinlemek ve desteklemek için buradayım. Hadi, ilk sohbetimize başlayalım!"
        )
    
    # Kullanıcının yerel saatini hesapla
    try:
        user_tz = pytz.timezone(user_timezone)
        current_time = datetime.now(user_tz)
        time_str = current_time.strftime("%H:%M")
        
        if 5 <= current_time.hour < 12:
            day_part = "sabah"
        elif 12 <= current_time.hour < 18:
            day_part = "öğleden sonra"
        else:
            day_part = "akşam"
            
        time_context = f"Kullanıcının yerel saati şu an {time_str} ({day_part})."
    except pytz.UnknownTimeZoneError:
        time_context = "Kullanıcının saat dilimi bilinmiyor."

    # "Yumuşak Geçiş" felsefesini uygulayan yeni talimat
    greeting_prompt = (
        "Sen bir yapay zeka arkadaşsın ve kullanıcı uygulamayı yeni açtı. Sohbeti sen başlat. "
        f"{time_context} Lütfen bu saate uygun, sıcak, genel bir karşılama yap (örn: 'Günaydın!', 'İyi akşamlar!'). "
        "Ardından, aşağıdaki bağlamdan İLHAM ALARAK, konuyu bugüne veya geleceğe bağlayan açık uçlu bir soru sor. "
        "Asla bağlamdaki özel bir detayı ilk cümlende ifşa etme. "
        "Kullanıcının adını her karşılamada kullanmaktan kaçın, daha doğal ol. "
        "Sadece tek bir karşılama cümlesi ve bir soru yeterli.\n\n"
        f"İLHAM İÇİN BAĞLAM:\n{system_prompt_context}"
    )
    return get_gemini_response(greeting_prompt)

# --- 6. ANA SOHBET AKIŞI ---

# Eğer sohbet geçmişi boşsa, proaktif bir karşılama mesajı oluştur.
if user_id and not st.session_state.chat_history:
    # Karşılama mesajı için hafıza araması yapmaya gerek yok, boş prompt gönder.
    full_prompt_for_greeting = get_comprehensive_system_prompt(user_id, user_name, user_details, id_token, "")
    user_tz = user_details.get("timezone", "UTC") # Kullanıcının saat dilimini al
    greeting = generate_proactive_greeting(is_first_chat, user_name, full_prompt_for_greeting, user_tz)
    st.session_state.chat_history.append({"role": "ai", "content": greeting})
    if is_first_chat:
        firebase_db.update_user_profile_field(user_id, "is_first_chat", False, id_token)
    st.rerun()

# Kullanıcıdan yeni bir mesaj alındığında...
if prompt := st.chat_input("Bana bir şeyler anlat..."):
    # Mesajı hem session'a hem de ekrana ekle.
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    with st.spinner("Yazıyor..."):
        # Sistem talimatını, kullanıcının son mesajını içerecek şekilde oluştur.
        system_prompt = get_comprehensive_system_prompt(user_id, user_name, user_details, id_token, prompt)
        
        # Geçmiş sohbeti Gemini formatına hazırla
        # Her mesaj bir sözlük, anahtarlar "role" ve "parts".
        history_for_gemini = []
        for msg in st.session_state.chat_history[:-1]: # Son kullanıcı mesajı hariç
            role = "user" if msg["role"] == "user" else "model"
            history_for_gemini.append({"role": role, "parts": [msg["content"]]})
            
        # Sistem talimatını başa ekle
        # Bu şekilde daha doğru bir kullanım olur.
        model_with_history = genai.GenerativeModel(
            model_name="models/gemini-1.5-pro-latest",
            system_instruction=system_prompt
        )
        chat = model_with_history.start_chat(history=history_for_gemini)
        
        # Yanıtı tek seferde al ve ekrana yazdır.
        response = chat.send_message(prompt)
        full_reply = response.text
        
        # Hem kullanıcının mesajını hem de AI'ın yanıtını uzun süreli hafızaya kaydet.
        save_to_memory(user_id, prompt, {"role": "user"})
        save_to_memory(user_id, full_reply, {"role": "ai"})
        
        # AI'ın yanıtını session'a ekle ve ekranı yenile.
        st.session_state.chat_history.append({"role": "ai", "content": full_reply})
        
    st.rerun()