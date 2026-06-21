
```markdown
# 🤖 ربات مدیریت گروه تلگرام

ربات حرفه‌ای مدیریت گروه تلگرام با هوش مصنوعی فارسی، کاملاً **رایگان**، نوشته‌شده با Python و aiogram 3.x.

## ✨ امکانات

### 🛡️ مدیریت گروه
- `/ban` — بن دائمی کاربر (روی پیامش ریپلای کن)
- `/kick` — اخراج کاربر (می‌تونه دوباره عضو شه)
- `/mute [زمان]` — سکوت کاربر، مثال: `/mute 1h`, `/mute 30m`, `/mute 2d`
- `/unmute` — رفع سکوت کاربر
- `/warn [دلیل]` — اخطار دادن، بعد از ۳ اخطار بن خودکار
- `/warns` — نمایش تعداد اخطار کاربر
- `/del` — حذف پیام (روی پیام مورد نظر ریپلای کن)
- `/stats` — آمار گروه

### 🧠 هوش مصنوعی فارسی
ربات با Groq و Gemini (هر دو رایگان) به فارسی جواب میده. وقتی فعال میشه:
- وقتی ربات منشن بشه (`@یوزرنیم_ربات`)
- وقتی روی پیام ربات ریپلای بشه
- وقتی پیام با یکی از کلمات `TRIGGER_KEYWORDS` شروع بشه

اگه Groq جواب نده، خودکار میره سراغ Gemini.

### 🚫 ضد اسپم
- محدودیت تعداد پیام در بازه‌ی زمانی کوتاه
- محدودیت تعداد درخواست هوش مصنوعی
- تشخیص و حذف پیام‌های تکراری

### 🎉 رویدادهای گروه
- پیام خوش‌آمدگویی خودکار برای عضو جدید
- پیام خداحافظی برای عضو خارج‌شده

### 😄 سرگرمی
- `/joke` — جوک تصادفی فارسی

---

## ⚙️ متغیرهای محیطی (Environment Variables)

| نام | توضیح | اجباری؟ |
|---|---|---|
| `BOT_TOKEN` | توکن ربات، از @BotFather | ✅ بله |
| `GROQ_API_KEY` | کلید رایگان از console.groq.com | ✅ بله |
| `GEMINI_API_KEY` | کلید رایگان از aistudio.google.com | ✅ بله |
| `ADMIN_IDS` | آیدی عددی ادمین‌ها، با کاما جدا کن | ✅ بله |
| `TRIGGER_KEYWORDS` | کلماتی که با اون شروع پیام، AI فعال میشه | ❌ اختیاری (پیش‌فرض: `هوش,bot,ربات`) |
| `DB_PATH` | مسیر فایل دیتابیس (برای Volume روی Railway) | ❌ اختیاری (پیش‌فرض: `bot_database.sqlite3`) |

نمونه:
```

BOT_TOKEN=123456:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx
ADMIN_IDS=123456789,987654321
TRIGGER_KEYWORDS=هوش,bot,ربات
DB_PATH=/data/bot_database.sqlite3
```

---

## 🚀 دیپلوی روی Railway (رایگان)

۱. ریپو رو به Railway وصل کن: `New Project` → `Deploy from GitHub repo`
۲. توی تب **Variables** متغیرهای بالا رو وارد کن
۳. توی تب **Settings → Deploy**، مقدار `Custom Start Command` رو بذار:
   ```
   python main.py
   ```
۴. (پیشنهادی) یه **Volume** بساز با Mount Path برابر `/data` تا دیتابیس بعد از ری‌دیپلوی پاک نشه، و `DB_PATH=/data/bot_database.sqlite3` رو به Variables اضافه کن
۵. ربات رو به گروه تلگرام اضافه کن و **ادمینش کن** با دسترسی‌های:
   - Ban users
   - Delete messages
   - Restrict members
۶. توی BotFather حتماً `Group Privacy` رو **خاموش (Off)** کن تا ربات بتونه همه‌ی پیام‌های گروه رو ببینه

---

## 📁 ساختار پروژه

```

bot/
 ├── main.py                  # نقطه‌ی شروع برنامه
 ├── config.py                # بارگذاری تنظیمات از env
 ├── requirements.txt
 ├── .env.example
 ├── handlers/
 │    ├── admin.py            # دستورات مدیریتی
 │    ├── chat.py             # هوش مصنوعی و /joke
 │    └── events.py           # ورود/خروج اعضا
 ├── services/
 │    ├── groq_service.py
 │    ├── gemini_service.py
 │    └── ai_router.py        # روتر هوش مصنوعی (Groq → Gemini → fallback)
 ├── middlewares/
 │    └── rate_limit.py       # ضد اسپم
 ├── utils/
 │    ├── filters.py
 │    └── helpers.py
 └── database/
      └── db.py                # دیتابیس SQLite async
```

---

## 🧪 اجرای محلی (اختیاری)

```bash
pip install -r requirements.txt
cp .env.example .env
# مقادیر .env رو پر کن
python main.py
```

---

## 📝 لایسنس

آزاد برای استفاده‌ی شخصی و آموزشی.
