# 🔍 UltraGrep — Akıllı ve Hızlı Kod Arama Aracı

**UltraGrep**, Rust ile yazılmış `ripgrep`'e kıyasla daha zengin özelliklerle geliştirilmiştir.
yüksek performanslı ve özellik açısından zengin bir **kod arama ve değiştirme aracıdır**.

Python ile geliştirilmiş olup:
- ⚡ Çok hızlı arama (mmap + multiprocessing)
- 🧠 Akıllı analiz (fonksiyon/sınıf tespiti)
- ✏️ Find & Replace desteği
- 🖥️ CLI + GUI kullanım

sunmaktadır.


---

## 🆚 Ripgrep'e Göre Farklar

| Özellik | ripgrep | ultragrep |
|---|---|---|
| Regex ile arama | ✅ | ✅ |
| mmap ile hızlı okuma | ✅ | ✅ |
| Paralel dosya işleme | ✅ | ✅ |
| Renkli terminal çıktısı | ✅ | ✅ |
| **Find & Replace** | ❌ | ✅ |
| **Hangi fonksiyon/sınıf içinde?** | ❌ | ✅ |
| **JSON çıktı modu (AI için)** | kısmi | ✅ tam |
| **Görsel arayüz (GUI)** | ❌ | ✅ |
| **Dry-run replace önizleme** | ❌ | ✅ |

---

## ⚙️ Kurulum

### Gereksinimler
- Python 3.8 veya üzeri

### Kurulum Adımları

```bash
# 1. Repoyu klonla
git clone https://github.com/caglaks0/ultragrep.git
cd ultragrep

# 2. Bağımlılıkları kur
pip install colorama PyQt5

# 3. Paketi kur
pip install -e .
```

---

## 🖥️ Komut Satırı (CLI) Kullanımı

### Temel Arama

```bash
# Mevcut klasörde ara
python -m ultragrep "def main" .

# Belirli bir klasörde ara
python -m ultragrep "import" ./src
```

### Fonksiyon/Sınıf Tespiti (Ripgrep'te Yok!)

```bash
python -m ultragrep "TODO" ./src

# Örnek çıktı:
# 📄 src/main.py
# ─────────────────────────────────────
#    42    # TODO: burası optimize edilmeli   [fonksiyon: process_data]
```

### Find & Replace (Ripgrep'te Yok!)

```bash
# Önce önizle
python -m ultragrep --replace "eski_fonksiyon" --new "yeni_fonksiyon" . --dry-run

# Onayladıktan sonra gerçek değiştirme
python -m ultragrep --replace "eski_fonksiyon" --new "yeni_fonksiyon" .
```

### JSON Çıktısı (Yapay Zeka İçin!)

```bash
python -m ultragrep "def " ./src --json
```

Çıktı örneği:
```json
{
  "tool": "ultragrep",
  "version": "1.0.0",
  "summary": {
    "total_files_scanned": 12,
    "total_files_with_matches": 4,
    "total_matches": 17,
    "elapsed_ms": 38.4
  },
  "results": [
    {
      "filepath": "src/main.py",
      "match_count": 3,
      "matches": [
        {
          "line_number": 12,
          "line": "def main():",
          "scope": "main",
          "scope_type": "fonksiyon"
        }
      ]
    }
  ]
}
```

---

## 🖼️ Görsel Arayüz (GUI) Kullanımı


```bash
python ultragrep/ultragrep_gui.py

```
### 🔍 Arama Ekranı
![UI](https://github.com/user-attachments/assets/d22812d6-6106-4c14-9c62-73eade5c204c)

### 📊 Sonuç / Çıktı Ekranı
![UI](https://github.com/user-attachments/assets/2cace6da-54dc-479f-92a3-45dc729e6d90)

### ✏️ Replace (Değiştirme) Ekranı
![UI](https://github.com/user-attachments/assets/4016bb36-a3aa-4595-9222-b59a6ac7ded4)


### GUI Özellikleri
- Klasör seçici
- Arama — canlı sonuç görüntüleme
- Find & Replace (önizleme modlu)
- Sonuca çift tıklayarak dosyayı aç
- Profesyonel karanlık tema (PyQt5)

---

Nasıl Çalışır?

UltraGrep performansı artırmak için:

📦 mmap → dosyaları RAM gibi okur (çok hızlı)
⚡ multiprocessing → aynı anda birden fazla dosya tarar
🚫 binary filtreleme → gereksiz dosyaları atlar
📂 recursive search → tüm klasörü tarar

---

## 📁 Proje Yapısı

```
ultragrep/
├── ultragrep/
│   ├── __init__.py      # Paket tanımı
│   ├── __main__.py      # CLI giriş noktası
│   ├── searcher.py      # Arama/değiştirme motoru (mmap + paralel)
│   └── gui.py           # PyQt5 görsel arayüzü
├── setup.py             # pip ile kurulum
└── README.md            # Bu dosya

```

🎯 Proje Amacı

---
Bu proje, klasik grep araçlarının ötesine geçerek:

Daha hızlı
Daha akıllı
Daha kullanıcı dostu
bir arama sistemi geliştirmek amacıyla yapılmıştır.

---

## 📜 Lisans

MIT License
