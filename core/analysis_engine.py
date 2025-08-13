# -*- coding: utf-8 -*-
"""
Karakter Analizi Motoru Modülü.

Bu modül, projenin en özgün özelliklerinden birini içerir. Belirli aralıklarla
çalışarak, bir kullanıcının o ana kadar girmiş olduğu tüm günlükleri ve
hedefleri toplar. Bu verileri, büyük bir dil modeline (LLM - Gemini) göndererek
kullanıcının kişiliği, öncelikleri ve genel ruh hali hakkında özet bir
"karakter raporu" oluşturur.

Bu rapor daha sonra yapay zekanın sistem talimatına (system prompt) eklenir.
Böylece yapay zeka, kullanıcıyı daha derinlemesine tanır ve daha empatik,
kişiselleştirilmiş ve bağlama uygun sohbetler gerçekleştirebilir.
"""
import datetime
from core import firebase_db
from ai.gemini_client import get_gemini_response

def generate_character_report(user_id: str, id_token: str):
    """
    Kullanıcının tüm geçmiş verilerini (günlükler, hedefler) analiz eder,
    bir karakter raporu oluşturur ve bunu kullanıcının Firebase profiline kaydeder.
    
    Args:
        user_id (str): Analiz yapılacak kullanıcının ID'si.
        id_token (str): İşlemi yetkilendirmek için kullanıcının Firebase token'ı.
    """
    # 1. Veri Toplama Aşaması
    # -----------------------
    # Kullanıcıya ait tüm günlük ve hedef verilerini veritabanından güvenli bir şekilde çek.
    journals = firebase_db.get_journals(user_id, id_token)
    goals = firebase_db.get_goals(user_id, id_token)

    # 2. Veri Ön İşleme Aşaması
    # --------------------------
    # Çekilen tüm yapılandırılmış veriyi, yapay zekanın anlayabileceği
    # tek ve temiz bir metin bloğu haline getir.
    full_text_content = ""
    
    if journals:
        full_text_content += "### Günlük Notları:\n"
        sorted_journals = sorted(journals.items()) # Kronolojik analiz için tarihleri sırala.
        for date_str, entries in sorted_journals:
            if isinstance(entries, dict):
                for entry_data in entries.values():
                    if isinstance(entry_data, dict) and entry_data.get("text"):
                        full_text_content += f"- {date_str}: {entry_data['text']}\n"
    
    if goals:
        full_text_content += "\n### Hedefleri:\n"
        sorted_goals = sorted(goals.items()) # Hedefleri de sırala.
        for date_str, date_goals in sorted_goals:
            if isinstance(date_goals, dict):
                pending = date_goals.get("pending", {})
                for goal_data in pending.values():
                    if isinstance(goal_data, dict) and goal_data.get("goal"):
                        goal_type = "Günlük" if goal_data.get("type") == "daily" else "Uzun Vadeli"
                        full_text_content += f"- {goal_type} Hedef ({date_str}): {goal_data['goal']}\n"

    # Eğer analiz edilecek hiç veri yoksa, işlemi sonlandır.
    if not full_text_content.strip():
        print(f"Kullanıcı {user_id} için analiz edilecek veri bulunamadı.")
        return

    # 3. Talimat (Prompt) Oluşturma Aşaması
    # --------------------------------------
    # Gemini modeline ne yapması gerektiğini adım adım anlatan bir sistem
    # talimatı (system prompt) oluştur. Bu, modelin çıktısını istediğimiz
    # format ve kalitede olmasını sağlar.
    analysis_prompt = f"""
    Aşağıda bir kullanıcının kişisel günlüğünden ve hedeflerinden alınmış tüm veriler bulunmaktadır. 
    Bu verileri dikkatlice analiz et ve aşağıdaki formatta bir "Karakter Analizi Raporu" oluştur:

    - **Tekrar Eden Temalar:** Kullanıcının sıkça bahsettiği 2-3 ana temayı belirle (örn: kariyer kaygısı, yeni hobilere başlama isteği, sosyal ilişkiler).
    - **Güçlü Yönler:** Verilerden yola çıkarak kullanıcının fark edilen 1-2 olumlu özelliğini yaz (örn: hedeflerine bağlılık, zorluklar karşısında dayanıklılık).
    - **Potansiyel Gelişim Alanları:** Kullanıcının zorlandığı veya geliştirebileceği 1-2 alanı nazik bir dille belirt (örn: zaman yönetimi, olumsuz düşüncelerle başa çıkma).

    Bu raporu, bir arkadaşının onun hakkında tutacağı samimi ve destekleyici notlar gibi, kısa ve öz maddeler halinde yaz.

    ---
    KULLANICI VERİLERİ:
    {full_text_content}
    ---

    KARAKTER ANALİZİ RAPORU:
    """

    # 4. Yapay Zeka Analizi Aşaması
    # -------------------------------
    # Hazırlanan talimatı ve verileri Gemini modeline göndererek analizi gerçekleştir.
    character_report = get_gemini_response(analysis_prompt)

    # 5. Sonuçları Kaydetme Aşaması
    # -----------------------------
    # Oluşturulan raporu ve analizin yapıldığı tarihi, daha sonra sohbet
    # ekranında kullanılmak üzere kullanıcının profiline kaydet.
    if character_report:
        today_str = datetime.date.today().isoformat()
        firebase_db.update_user_profile_field(user_id, "character_report", character_report, id_token)
        firebase_db.update_user_profile_field(user_id, "last_analysis_date", today_str, id_token)

    print(f"Karakter analizi tamamlandı ve {user_id} için kaydedildi.")
