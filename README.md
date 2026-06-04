# Üçbucaq Restoran — Flask Admin Panel

## Quraşdırma

### 1. Python yükləyin
https://python.org/downloads (Windows üçün)

### 2. Lazımi kitabxanaları quraşdırın
```bash
pip install -r requirements.txt
```

### 3. Mühit dəyişənlərini təyin edin
`.env` faylı yaradın:
```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your_app_password
APP_BASE_URL=http://localhost:5000
```

### 4. Serveri işə salın
```bash
python app.py
```

### 5. Brauzerdə açın
- Admin panel: http://localhost:5000/admin
- Menyu:       http://localhost:5000/menu

## Giriş məlumatları

İlk giriş üçün default istifadəçi adı `admin`-dir.  
**Şifrəni ilk girişdən dərhal dəyişin** — admin paneldə Parametrlər bölməsindən.

> ⚠️ Default şifrəni README-də saxlamaq təhlükəlidir. Şifrəni server administratorundan alın.

## Fayl strukturu
```
ucbucaq/
  app.py              ← Python Flask server
  requirements.txt    ← Lazımi kitabxanalar
  templates/
    admin.html        ← Admin panel
    menu.html         ← Müştəri menyusu
  static/
    uploads/          ← Yüklənmiş şəkillər
```

## Qovluq strukturunu qurun
```
mkdir templates static/uploads -p
mv admin.html menu.html templates/
```

## Xüsusiyyətlər
- ✅ 20 kateqoriya, 130+ menyu məhsulu hazır əlavə edilib
- ✅ Üçbucaq Restoran brend rəngləri (qızıl + tünd fon)
- ✅ Şəkil yükləmə (loqo + məhsul şəkilləri)
- ✅ Statistika (baxış, klik, kateqoriya)
- ✅ İstifadəçi idarəetməsi
- ✅ Azərbaycan / İngilis dil dəstəyi

## Deployment (Render.com — pulsuz)
1. GitHub-a yükləyin
2. render.com-da "New Web Service"
3. Repository seçin, `python app.py` start command
4. Environment Variables bölməsindən `SECRET_KEY`, `MAIL_USERNAME`, `MAIL_PASSWORD` əlavə edin
5. Deploy edin

