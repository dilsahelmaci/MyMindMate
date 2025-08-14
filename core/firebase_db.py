# -*- coding: utf-8 -*-
"""
Firebase Realtime Database İşlemleri Modülü.

Bu modül, uygulama içerisindeki tüm veritabanı CRUD (Create, Read, Update, Delete)
işlemlerinden sorumludur. Kullanıcı verileri (profiller, günlükler, hedefler)
bu modül aracılığıyla yönetilir.

Güvenlik Notu:
Tüm fonksiyonlar, kullanıcının kimliğini doğrulamak ve veritabanı kurallarına
uymak için bir `id_token` parametresi alır. Bu token olmadan hiçbir işlem
yapılamaz. Bu, bir kullanıcının sadece kendi verilerine erişebilmesini sağlar.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from core.firebase_config import initialize_firebase_app

def get_db_instance():
    """
    Yeni bir Firebase veritabanı bağlantı nesnesi döndürür.

    Her işlem öncesi çağrılarak, işlemlerin birbirinden izole ve
    temiz bir bağlantı üzerinden yapılması sağlanır.
    """
    firebase_app = initialize_firebase_app()
    return firebase_app.database()

# --- GÜNLÜK (JOURNAL) İŞLEMLERİ ---

def save_journal(user_id: str, date: str, text: str, id_token: str) -> Optional[str]:
    """
    Belirtilen tarihe yeni bir günlük girdisi kaydeder ve kaydın ID'sini döndürür.
    """
    db = get_db_instance()
    path = f"users/{user_id}/journals/{date}"
    now = datetime.now().strftime("%H:%M")
    # `push` metodu, oluşturulan kaydın bilgilerini bir sözlük olarak döndürür.
    result = db.child(path).push({"text": text, "timestamp": now}, id_token)
    # Bu sözlüğün 'name' anahtarı, kaydın benzersiz ID'sini içerir.
    return result.get('name') if isinstance(result, dict) else None


def get_journals(user_id: str, id_token: str) -> dict:
    """Bir kullanıcının tüm günlük girdilerini tarihe göre gruplanmış olarak çeker."""
    db = get_db_instance()
    path = f"users/{user_id}/journals"
    data = db.child(path).get(id_token).val()
    if not data:
        return {}
    # Firebase'den gelebilecek bozuk veya beklenmedik formatlı verileri temizle.
    clean = {}
    for day, entries in data.items():
        if isinstance(entries, dict):
            # Sadece sözlük (dict) formatındaki girdileri kabul et.
            filtered = {k: v for k, v in entries.items() if isinstance(v, dict)}
            if filtered:
                clean[day] = filtered
    return clean

# --- HEDEF (GOAL) İŞLEMLERİ ---

def save_goal(user_id: str, date: str, goal: str, goal_type: str, id_token: str) -> Optional[str]:
    """
    Belirtilen tarihe yeni bir hedef kaydeder ve kaydın ID'sini döndürür.
    """
    db = get_db_instance()
    # Tüm hedefler başlangıçta "pending" (beklemede) olarak kaydedilir.
    path = f"users/{user_id}/goals/{date}/pending"
    result = db.child(path).push({"goal": goal, "type": goal_type, "is_checked": False}, id_token)
    return result.get('name') if isinstance(result, dict) else None


def get_goals(user_id: str, id_token: str) -> dict:
    """Bir kullanıcının tüm hedeflerini (bekleyen ve tamamlanan) çeker."""
    db = get_db_instance()
    path = f"users/{user_id}/goals"
    data = db.child(path).get(id_token).val()
    return data if data else {}

def update_goal_check(user_id: str, goal_id: str, date_str: str, checked: bool, id_token: str):
    """Bir hedefin tamamlanma durumunu (`is_checked`) günceller."""
    db = get_db_instance()
    path = f"users/{user_id}/goals/{date_str}/pending/{goal_id}"
    db.child(path).update({"is_checked": checked}, id_token)

def delete_goal_by_id(user_id: str, goal_id: str, date_str: str, id_token: str):
    """Belirli bir hedefi ID'sine göre veritabanından siler."""
    db = get_db_instance()
    path = f"users/{user_id}/goals/{date_str}/pending/{goal_id}"
    db.child(path).remove(id_token)

# --- KULLANICI PROFİLİ (USER PROFILE) İŞLEMLERİ ---

def save_user_details_from_dict(user_id: str, user_data: dict, id_token: str):
    """
    Kullanıcı profili bilgilerini bir sözlükten toplu olarak kaydeder/günceller.
    Genellikle kayıt sırasında veya profil ayarlarında kullanılır.
    """
    db = get_db_instance()
    path = f"users/{user_id}/profile"
    if "created_at" not in user_data:
        user_data["created_at"] = datetime.now().isoformat()
    # `set` metodu, belirtilen yoldaki tüm veriyi silip yenisini yazar.
    db.child(path).set(user_data, id_token)

def get_user_details(user_id: str, id_token: str) -> dict:
    """Bir kullanıcının profil detaylarını (isim, e-posta vb.) çeker."""
    db = get_db_instance()
    path = f"users/{user_id}/profile"
    data = db.child(path).get(id_token).val()
    return data if data else {}

def update_user_profile_field(user_id: str, field: str, value, id_token: str):
    """Kullanıcı profilindeki tek bir alanı (örn: 'name' veya 'timezone') günceller."""
    db = get_db_instance()
    path = f"users/{user_id}/profile"
    # `update` metodu, belirtilen yoldaki sadece ilgili alanı değiştirir, diğerlerine dokunmaz.
    db.child(path).update({field: value}, id_token)

def delete_all_user_data(user_id: str, id_token: str):
    """
    Bir kullanıcıya ait TÜM verileri (profil, günlükler, hedefler) veritabanından siler.
    Bu işlem geri alınamaz ve genellikle hesap silme işlemiyle birlikte çağrılır.
    """
    db = get_db_instance()
    path = f"users/{user_id}"
    db.child(path).remove(id_token)
