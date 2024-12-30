# İkinci El Eşya Satış Sitesi

Bu proje, ikinci el eşyaların satışı için basit bir web sitesidir. FastAPI ve SQLite kullanılarak geliştirilmiştir.

## Kurulum

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

2. Uygulamayı çalıştırın:
```bash
uvicorn main:app --reload
```

3. Tarayıcınızda http://localhost:8000 adresine gidin

## Özellikler

- Ürün listesi görüntüleme
- Ürün detayları görüntüleme
- Admin paneli (temel kimlik doğrulama ile)
- Ürün ekleme/düzenleme/silme (sadece admin)

## Admin Girişi

Varsayılan kullanıcı bilgileri:
- Kullanıcı adı: admin
- Şifre: admin

## Dizin Yapısı

```
.
├── README.md
├── requirements.txt
├── main.py
├── database.py
├── models.py
└── templates/
    ├── base.html
    ├── index.html
    └── item_detail.html
```
