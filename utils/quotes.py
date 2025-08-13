import random

_QUOTES = [
    ("Unutma, kendine gösterdiğin şefkat, başkalarına sunabileceğin en büyük hediyenin başlangıcıdır.", ""),
    ("Mükemmel olmak zorunda değilsin, sadece kendin olman yeterli.", ""),
    ("Bugün kendine bir mola ver. Dinlenmek de yolculuğun bir parçasıdır.", "Anne Lamott"),
    ("Nefes al. Bu an, sahip olduğun tek gerçeklik.", "Thich Nhat Hanh"),
    ("Düşünceler sadece zihninden geçen bulutlardır. Onlara tutunmak zorunda değilsin.", "Andy Puddicombe"),
    ("En derin yaralarımızdan en büyük gücümüz doğabilir.", "Carl Jung"),
    ("Kendini tanımak, en değerli yolculuktur.", "Sokrates"),
    ("Duygular misafirdir, bırak gelip gitsinler.", "Rumi"),
    ("En büyük zafer, düştüğünde değil, her düştüğünde yeniden ayağa kalkabilmektir.", "Nelson Mandela"),
    ("İçindeki sessizliği dinle, sana yol gösterecektir.", ""),
    ("Değişim rüzgarları estiğinde, bazıları duvar örer, bazıları yel değirmeni yapar.", "Çin Atasözü"),
    ("Kendine karşı dürüst olduğun gün, büyümeye başladığın gündür.", ""),
]

def get_random_quote():
    """Listeden rastgele bir söz ve yazarını döndürür."""
    return random.choice(_QUOTES)
