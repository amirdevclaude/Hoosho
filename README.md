# 🤖 ربات مدیریت گروه تلگرام - Hoosho

ربات حرفه‌ای مدیریت گروه تلگرام با هوش مصنوعی فارسی، کاملاً **رایگان**، نوشته‌شده با Python و aiogram 3.x.

## 👋 درباره ربات

**نام کامل:** هوشو (Hoosho) 👾
**نام تلگرام:** @Hooosho
**وظیفه:** دستیار هوشمند برای مدیریت گروه‌های تلگرام و پاسخ‌گویی به سوالات به فارسی

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
- `/pin` — پین کردن پیام
- `/unpin` — آنپین کردن پیام
- `/ro` — قفل کردن گروه (فقط ادمین‌ها می‌تونن پیام بفرستن)
- `/unro` — باز کردن قفل گروه
- `/purge` — حذف دسته‌ای پیام‌ها
- `/adminlist` — نمایش لیست ادمین‌های گروه
- `/id` — نمایش آیدی گروه و کاربر
- `/setwelcome` — تنظیم پیام خوش‌آمد سفارشی
- `/addfilter [کلمه]` — اضافه کردن کلمه به لیست ممنوعه
- `/rmfilter [کلمه]` — حذف کلمه از لیست ممنوعه
- `/filters` — نمایش لیست کلمات ممنوعه
- `/filterlinks on|off` — فعال/غیرفعال کردن فیلتر لینک‌های خارجی

### 🧠 هوش مصنوعی فارسی
ربات با Groq و Gemini (هر دو رایگان) به فارسی جواب میده. وقتی فعال میشه:
- وقتی ربات منشن بشه (`@Hooosho`)
- وقتی روی پیام ربات ریپلای بشه
- وقتی پیام با یکی از کلمات `TRIGGER_KEYWORDS` شروع بشه

اگه Groq جواب نده (یا timeout شود)، خودکار میره سراغ Gemini. **حالا با retry logic هم بهتر شده!**

### 🚫 ضد اسپم
- محدودیت تعداد پیام در بازه‌ی زمانی کوتاه
- محدودیت تعداد درخواست هوش مصنوعی
- تشخیص و حذف پیام‌های تکراری

### 🎉 رویدادهای گروه
- پیام خوش‌آمدگویی خودکار برای عضو جدید
- پیام خداحافظی برای عضو خارج‌شده

### 😄 سرگرمی
- `/joke` — جوک تصادفی فارسی

### 🤖 دستورات پیوی (Private Chat)
- `/start` — پیام خوش‌آمد
- `/about` — اطلاعات کامل درباره ربات و آمار سرویس‌ها
- `/help` — راهنمای استفاده
- `/joke` — جوک تصادفی
- `/stats` — نمایش آمار عملکرد ربات
- `/reset` — پاک کردن تاریخچه‌ی مکالمه
- **پیام‌های معمولی:** هر پیام ای بفرسته، ربات جواب میده!

### 📋 سخت‌افزار و بک‌اند
- ✅ **Database Cleanup:** پاک‌کردن خودکار پیام‌های قدیمی
- ✅ **Metrics & Telemetry:** نمایش آمار دقیق عملکرد AI
- ✅ **Retry Logic:** تلاش مجدد درصورت شکست Groq
- ✅ **Bot Info Caching:** جلوگیری از API calls غیر ضروری
- ✅ **Error Handling:** مدیریت بهتر خطاها

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
| `REDIS_URL` | آدرس Redis (برای استفاده‌ی بعدی) | ❌ اختیاری |

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

۲. توی تب **Variables** متغیرهای بالا رو وارد کن (حتماً `TRIGGER_KEYWORDS` رو پر کن!)

۳. توی تب **Settings → Deploy**، مقدار `Custom Start Command` رو بذار:
   ```
   python main.py
   ```

۴. (پیشنهادی) یه **Volume** بساز با Mount Path برابر `/data` تا دیتابیس بعد از ری‌دیپلوی پاک نشه، و `DB_PATH=/data/bot_database.sqlite3` رو وارد کن

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
 │    ├── chat.py             # هوش مصنوعی و /joke (حالا با bot caching)
 │    ├── events.py           # ورود/خروج اعضا
 │    ├── group_features.py   # /summary, /remind
 │    ├── private.py          # دستورات پیوی شامل /about
 │    └── callbacks.py        # دکمه‌های inline keyboard
 ├── services/
 │    ├── groq_service.py     # Groq API wrapper
 │    ├── gemini_service.py   # Gemini API wrapper (درست‌شده)
 │    ├── ai_router.py        # Router هوش مصنوعی (با retry logic)
 │    ├── moderation_actions.py
 │    ├── intent_service.py
 │    ├── reminder_task.py    # تسک یادآورها
 │    ├── cleanup_service.py  # تسک پاک‌کردن دیتابیس قدیمی ✨
 │    └── metrics.py          # Telemetry و آمار ✨
 ├── middlewares/
 │    └── rate_limit.py       # ضد اسپم
 ├── utils/
 │    ├── filters.py
 │    └── helpers.py
 └── database/
      └── db.py                # دیتابیس SQLite async (با cleanup functions)
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

## 🔧 بهبود‌ها و تغییرات اخیر

### ✅ باگ‌های رفع شده:
1. **Gemini Model** - تغییر از `gemini-2.5-flash-lite` (غیرموجود) به `gemini-1.5-flash`
2. **Bot Info API Calls** - `get_me()` حالا cache می‌شود (در هر درخواست دوباره فراخوانی نمی‌شود)
3. **Retry Logic** - Groq اکنون تا ۲ بار تلاش می‌کند قبل از رفتن به Gemini
4. **Database Cleanup** - تسک background هر روز پیام‌های قدیمی‌تر از ۳۰ روز را پاک می‌کند
5. **Error Handling** - بهتر و مفصل‌تر

### ✨ امکانات جدید:
1. **`/about` دستور** - اطلاعات کامل ربات و آمار لحظه‌ای
2. **`/stats` دستور** - آمار دقیق عملکرد (Groq/Gemini success rate، latency، و غیره)
3. **Metrics System** - جمع‌آوری تلمتری برای هر درخواست AI
4. **Cleanup Service** - پاک‌کردن خودکار دیتابیس
5. **بهتر System Prompts** - نام و توضیح مشخص برای هر provider
6. **Config Options** - تنظیمات بیشتری برای retry و cleanup policies

---

## 📊 نمونه آمار (`/stats`)

```
📊 آمار سرویس‌های هوشو🐧

درخواست‌های AI:
• کل: 150
• خطا: 3
• Timeout: 0
• نرخ خطا: 2%

سرعت (Latency):
• میانگین: 245.67ms
• حداقل: 112.34ms
• حداکثر: 1823.45ms

Groq:
• درخواست: 120
• موفقیت: 97.5%

Gemini:
• درخواست: 30
• موفقیت: 100%

آپ‌تایم: 2026-07-05T10:30:31+00:00
```

---

## 📝 لایسنس

آزاد برای استفاده‌ی شخصی و آموزشی.

---

## 🤝 مشارکت

اگر باگ پیدا کردی یا ایده‌ی بهبود داری، خواهش می‌کنم issue یا pull request بساز!

---

**نوشته‌شده با ❤️ برای کمک به مدیریت بهتر گروه‌های تلگرام**
