# app.py (النسخة الكاملة والمعدلة بناءً على طلبك الأخير)

from flask import Flask, render_template_string, url_for, request, redirect, flash, send_file, session
import os
import base64
import sqlite3
from io import BytesIO
from functools import wraps
import mimetypes

app = Flask(__name__)
ALLOWED_MEDIA_TYPES = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg']
# قم بتغيير هذا لمفتاح سري قوي ومعقد جداً في بيئة الإنتاج!
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_secret_key_that_you_should_change_in_production_1234567890')
app.config['ADMIN_SECRET_CODE'] = '001145668911' # الكود السري للإدارة كما طلبت

# --- إعدادات قاعدة البيانات SQLite ---
DATABASE = os.path.join(app.root_path, 'site.db')

def get_db_connection():
    """ينشئ اتصالاً بقاعدة البيانات."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # لجعل الصفوف قابلة للوصول كقاموس
    return conn

def init_db():
    """ينشئ جداول قاعدة البيانات إذا لم تكن موجودة ويدرج الأناشيد الافتراضية وطلبات الأناشيد."""
    with app.app_context():
        conn = get_db_connection()
        
        # جدول الأناشيد الحالي
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nasheed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                language TEXT NOT NULL DEFAULT 'ar',
                audio_data BLOB NOT NULL,
                audio_mimetype TEXT NOT NULL,
                category TEXT
            )
        ''')

        # جدول جديد لطلبات الأناشيد من المستخدمين العاديين
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nasheed_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                language TEXT NOT NULL DEFAULT 'ar',
                category TEXT,
                audio_link TEXT, -- رابط لملف الصوت/الفيديو
                contact_info TEXT, -- رقم الهاتف أو البريد الإلكتروني للمستخدم
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    print("Database tables created (if they didn't exist).")
    # استدعاء دالة إضافة الأناشيد الافتراضية بعد إنشاء الجداول
    add_initial_anasheed()


def add_initial_anasheed():
    """يضيف أناشيد افتراضية إلى قاعدة البيانات عند التشغيل الأول إذا لم تكن موجودة.
    **ملاحظة هامة:** تأكد من أن ملفات MP3 موجودة في مجلد 'anasheed_files'
    في نفس مسار ملف 'app.py'."""
    initial_anasheed_data = [
        {"title": "نشيد الوحدة", "description": "نشيد عن أهمية الوحدة والتآخي والتعاون.", "language": "ar", "category": "تربوي", "filename": "nasheed1.mp3"},
        {"title": "نشيد الأمل", "description": "كلمات تبعث الأمل في النفوس وروح الإيجابية.", "language": "ar", "category": "تحفيزي", "filename": "nasheed2.mp3"},
        {"title": "نشيد السلام", "description": "دعوة للسلام والمحبة بين الجميع وبناء مستقبل أفضل.", "language": "ar", "category": "ديني", "filename": "nasheed3.mp3"},
        # يمكنك إضافة المزيد هنا، تأكد من وجود الملفات في مجلد anasheed_files
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    for nasheed_info in initial_anasheed_data:
        title = nasheed_info['title']
        filename = nasheed_info['filename']
        # **تم تعديل المسار هنا ليناسب 'anasheed_files' كما طلبت**
        filepath = os.path.join(app.root_path, 'anasheed_files', filename) 

        # التحقق مما إذا كان النشيد موجودًا بالفعل لتجنب الإدخالات المكررة
        cursor.execute("SELECT COUNT(*) FROM nasheed WHERE title = ?", (title,))
        if cursor.fetchone()[0] == 0:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as audio_file:
                        audio_data = audio_file.read()
                        # استنتاج نوع MIME من اسم الملف
                        audio_mimetype, _ = mimetypes.guess_type(filepath)
                        if not audio_mimetype: # إذا لم يتم استنتاجه بشكل صحيح، افترض mp3
                             audio_mimetype = 'audio/mpeg'

                        cursor.execute('''
                            INSERT INTO nasheed (title, description, language, audio_data, audio_mimetype, category)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            title,
                            nasheed_info.get('description', ''),
                            nasheed_info.get('language', 'ar'),
                            audio_data,
                            audio_mimetype,
                            nasheed_info.get('category', '')
                        ))
                        print(f"Added initial nasheed: {title}")
                except Exception as e:
                    print(f"Error adding initial nasheed {title} from {filepath}: {e}")
            else:
                print(f"Warning: Initial nasheed file not found: {filepath}. Please ensure it exists in 'anasheed_files' folder.")
        else:
            print(f"Initial nasheed '{title}' already exists. Skipping.")
    conn.commit()
    conn.close()

# --- تحويل الصورة إلى Base64 ليتم تضمينها في CSS ---
try:
    with open(os.path.join(app.root_path, 'static', 'img', 'hero-bg.jpg'), 'rb') as img_file:
        ENCODED_HERO_BG_IMAGE = base64.b64encode(img_file.read()).decode('utf-8')
        HERO_BG_IMAGE_DATA_URI = f"data:image/jpeg;base64,{ENCODED_HERO_BG_IMAGE}"
except FileNotFoundError:
    print("WARNING: hero-bg.jpg not found in static/img. Hero section background will be missing.")
    HERO_BG_IMAGE_DATA_URI = ""

# --- كود CSS (مضمن ومعدل لاستخدام Base64 للصورة) ---
# تم تعديل قسم .features و .category-item في CSS
CSS_CODE = f"""
/* الألوان المستخدمة:
    الأخضر الداكن: #28a745
    الأخضر الفاتح: #4CAF50
    الرمادي الداكن: #343a40
    البرتقالي/الأصفر: #fd7e14
    الأزرق الفاتح: #007bff
*/

/* تنسيقات عامة للجسم والخطوط */
body {{
    font-family: 'Tajawal', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #e9ecef;
    color: #343a40;
    direction: rtl;
    text-align: right;
    line-height: 1.6;
}}

/* تنسيقات الروابط */
a {{
    text-decoration: none;
    color: #007bff;
    transition: color 0.3s ease;
}}

a:hover {{
    color: #0056b3;
}}

/* لتوسيط المحتوى وإعطاء مسافة داخلية */
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 25px;
}}

/* رأس الصفحة (Header) */
header {{
    background-color: #28a745;
    color: white;
    padding: 15px 0;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 1000;
}}

header .container {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
}}

.logo {{
    margin: 0;
    font-size: 2.2em;
    font-weight: bold;
}}

.logo a {{
    color: white;
}}

/* قائمة التنقل (Navigation) */
nav ul {{
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
}}

nav ul li {{
    margin: 0 15px;
}}

nav ul li a {{
    color: white;
    font-weight: 500;
    padding: 8px 12px;
    border-radius: 25px;
    transition: background-color 0.3s ease, transform 0.2s ease;
    display: block;
    white-space: nowrap; /* يمنع الكلمات من النزول لسطر جديد */
}}

nav ul li a:hover {{
    background-color: #45a049;
    transform: translateY(-2px);
}}

/* القسم الرئيسي (Main Content) */
main {{
    padding: 50px 0;
    min-height: 70vh;
}}

/* قسم الأبطال (Hero Section) في الصفحة الرئيسية */
.hero {{
    background: url('{HERO_BG_IMAGE_DATA_URI}') no-repeat center center/cover;
    color: white;
    text-align: center;
    padding: 100px 20px;
    border-radius: 15px;
    margin-bottom: 50px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.25);
    position: relative;
    overflow: hidden;
}}

.hero::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.4);
    z-index: 1;
    border-radius: 15px;
}}

.hero-content {{
    position: relative;
    z-index: 2;
}}

.hero-content h2 {{
    font-size: 3.5em;
    margin-bottom: 25px;
    line-height: 1.2;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}}

.hero-content p {{
    font-size: 1.3em;
    margin-bottom: 40px;
    max-width: 700px;
    margin-left: auto;
    margin-right: auto;
}}

.btn {{
    display: inline-block;
    background-color: #fd7e14;
    color: white;
    padding: 15px 35px;
    border-radius: 30px;
    font-weight: bold;
    font-size: 1.1em;
    transition: background-color 0.3s ease, transform 0.2s ease;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    text-align: center;
}}

.btn:hover {{
    background-color: #e66b0e;
    transform: translateY(-3px);
}}

/* قسم الميزات (Features Section) - تم تعديل المحتوى ليكون أكثر عمومية أو يمكن إزالته */
.features {{
    text-align: center;
    margin-bottom: 50px;
    padding: 30px 0; /* لزيادة المسافة الداخلية */
    background-color: #ffffff; /* خلفية بيضاء */
    border-radius: 15px;
    box-shadow: 0 6px 15px rgba(0,0,0,0.1);
}}

.features h3 {{
    font-size: 2.5em;
    color: #28a745;
    margin-bottom: 40px;
    position: relative;
    display: inline-block;
}}

.features h3::after {{
    content: '';
    position: absolute;
    width: 60%;
    height: 3px;
    background-color: #fd7e14;
    bottom: -10px;
    right: 20%;
    border-radius: 5px;
}}

.features p.intro-text {{ /* نص تمهيدي جديد لقسم الميزات */
    font-size: 1.2em;
    max-width: 800px;
    margin: 0 auto 30px auto;
    color: #555;
    line-height: 1.8;
}}


/* قسم "عن الموقع" والنموذج */
.about-section, .form-section, .nasheed-list-section, .category-section, .admin-login-form, .requests-list-section, .admin-dashboard-section {{
    background-color: white;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    margin-top: 40px;
}}

.about-section h2, .form-section h2, .nasheed-list-section h2, .category-section h2, .admin-login-form h2, .requests-list-section h2, .admin-dashboard-section h2 {{
    color: #28a745;
    text-align: center;
    margin-bottom: 35px;
    font-size: 2.8em;
    position: relative;
    display: inline-block;
    width: 100%;
}}
.about-section h2::after, .form-section h2::after, .nasheed-list-section h2::after, .category-section h2::after, .admin-login-form h2::after, .requests-list-section h2::after, .admin-dashboard-section h2::after {{
    content: '';
    position: absolute;
    width: 100px;
    height: 4px;
    background-color: #fd7e14;
    bottom: -10px;
    right: calc(50% - 50px);
    border-radius: 5px;
}}

.about-section p {{
    font-size: 1.15em;
    line-height: 1.9;
    margin-bottom: 20px;
    text-align: justify;
    color: #444;
}}

/* تنسيقات النموذج (Form) */
.form-group {{
    margin-bottom: 25px;
}}

.form-group label {{
    display: block;
    margin-bottom: 10px;
    font-weight: bold;
    color: #444;
    font-size: 1.1em;
}}

.form-group input[type="text"],
.form-group textarea,
.form-group select,
.form-group input[type="password"],
.form-group input[type="file"] {{
    width: 100%;
    padding: 15px;
    border: 1px solid #ced4da;
    border-radius: 8px;
    box-sizing: border-box;
    font-size: 1em;
    direction: rtl;
    text-align: right;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}}

.form-group input[type="file"] {{
    padding: 12px; /* تعديل ليتناسق مع حقول الإدخال الأخرى */
    background-color: #f8f9fa;
}}

.form-group input[type="text"]:focus,
.form-group textarea:focus,
.form-group select:focus,
.form-group input[type="password"]:focus,
.form-group input[type="file"]:focus {{
    border-color: #28a745;
    box-shadow: 0 0 0 0.2rem rgba(40,167,69,.25);
    outline: none;
}}

.form-group textarea {{
    resize: vertical;
    min-height: 120px;
}}

.form-group small {{
    display: block;
    color: #777;
    margin-top: 8px;
    font-size: 0.95em;
}}

/* تنسيقات رسائل الفلاش */
.flashes {{
    list-style: none;
    padding: 0;
    margin: 20px 0;
    text-align: center;
}}

.flashes li {{
    padding: 12px 25px;
    margin-bottom: 15px;
    border-radius: 8px;
    font-weight: bold;
    color: white;
    font-size: 1.05em;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}

.flashes li.success {{
    background-color: #28a745;
}}

.flashes li.danger {{
    background-color: #dc3545;
}}
.flashes li.info {{
    background-color: #17a2b8;
}}


/* تنسيقات قائمة الأناشيد */
.nasheed-list {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 30px;
    margin-top: 30px;
}}

.nasheed-item {{
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    text-align: center;
    transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

.nasheed-item:hover {{
    transform: translateY(-10px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
}}

.nasheed-item h3 {{
    color: #28a745;
    margin-top: 0;
    font-size: 2em;
    margin-bottom: 15px;
}}

.nasheed-item p {{
    font-size: 1.05em;
    color: #666;
    margin-bottom: 20px;
    flex-grow: 1;
    min-height: 60px;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.nasheed-item .audio-player {{
    width: 100%;
    margin-top: 15px;
    background-color: #f1f3f4;
    border-radius: 5px;
}}

.nasheed-meta {{
    font-size: 0.95em;
    color: #888;
    margin-top: 15px;
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
}}

.nasheed-meta span {{
    background-color: #f0f2f5;
    padding: 6px 12px;
    border-radius: 20px;
    margin: 5px;
    font-weight: 500;
    color: #555;
}}

.nasheed-actions {{
    margin-top: 25px;
    display: flex;
    justify-content: center;
    gap: 10px;
}}

.nasheed-actions a, .nasheed-actions button {{
    display: inline-block;
    padding: 10px 20px;
    border-radius: 25px;
    font-size: 0.95em;
    font-weight: bold;
    transition: background-color 0.3s ease, transform 0.2s ease;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    border: none;
    cursor: pointer;
}}

.nasheed-actions a.edit-btn {{
    background-color: #007bff;
    color: white;
}}

.nasheed-actions button.delete-btn {{
    background-color: #dc3545;
    color: white;
}}

.nasheed-actions a.edit-btn:hover {{
    background-color: #0056b3;
    transform: translateY(-2px);
}}

.nasheed-actions button.delete-btn:hover {{
    background-color: #c82333;
    transform: translateY(-2px);
}}

/* تنسيقات قائمة طلبات الأناشيد (الجديدة) */
.request-list {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 30px;
    margin-top: 30px;
}}

.request-item {{
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    text-align: right;
    transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    border-right: 5px solid #17a2b8; /* لون للطلبات الجديدة */
}}

.request-item h3 {{
    color: #28a745;
    margin-top: 0;
    font-size: 1.8em;
    margin-bottom: 10px;
}}

.request-item p {{
    font-size: 1em;
    color: #666;
    margin-bottom: 10px;
}}

.request-item .meta-info {{
    font-size: 0.9em;
    color: #888;
    margin-top: 10px;
}}
.request-item .meta-info span {{
    display: block;
    margin-bottom: 5px;
}}

.request-actions {{
    margin-top: 20px;
    display: flex;
    justify-content: center;
    gap: 10px;
}}

.request-actions button {{
    padding: 10px 20px;
    border-radius: 25px;
    font-size: 0.95em;
    font-weight: bold;
    border: none;
    cursor: pointer;
    transition: background-color 0.3s ease, transform 0.2s ease;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}}
.request-actions button.approve-btn {{
    background-color: #28a745;
    color: white;
}}
.request-actions button.reject-btn {{
    background-color: #dc3545;
    color: white;
}}
.request-actions button.approve-btn:hover {{
    background-color: #218838;
    transform: translateY(-2px);
}}
.request-actions button.reject-btn:hover {{
    background-color: #c82333;
    transform: translateY(-2px);
}}


/* تذييل الصفحة (Footer) */
footer {{
    background-color: #343a40;
    color: white;
    text-align: center;
    padding: 25px 0;
    box-shadow: 0 -4px 10px rgba(0,0,0,0.2);
    margin-top: 50px;
    font-size: 0.95em;
}}

/* تنسيقات قسم الفئات */
.category-section {{
    background-color: white;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    margin-top: 40px;
    text-align: center; /* توسيط عنوان القسم */
}}

.category-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); /* تعديل حجم الفئة */
    gap: 25px; /* زيادة المسافة بين الفئات */
    margin-top: 30px;
    justify-content: center; /* توسيط الفئات في الشبكة */
}}

.category-item {{
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 12px; /* زيادة استدارة الحواف */
    padding: 25px; /* زيادة المسافة الداخلية */
    transition: background-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
    box-shadow: 0 3px 10px rgba(0,0,0,0.08); /* ظل أوضح */
    text-align: center;
}}

.category-item:hover {{
    background-color: #e2e6ea;
    transform: translateY(-7px); /* تأثير رفع أكبر */
    box-shadow: 0 8px 20px rgba(0,0,0,0.15); /* ظل أكبر عند التمرير */
}}

.category-item h4 {{
    margin: 0;
    font-size: 1.8em; /* تكبير حجم عنوان الفئة */
}}

.category-item a {{
    color: #28a745;
    font-weight: bold;
    display: block;
}}

.category-item a:hover {{
    color: #1e7e34;
}}


/* تنسيقات لوحة تحكم المسؤول (admin_dashboard) */
.admin-dashboard-section .dashboard-links {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 20px;
    margin-top: 30px;
}}

.admin-dashboard-section .dashboard-link-item {{
    background-color: #f0f2f5;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 20px 30px;
    font-size: 1.2em;
    font-weight: bold;
    text-align: center;
    transition: background-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    flex-basis: 250px; /* حجم أساسي للعنصر */
    flex-grow: 1; /* للسماح بالنمو */
    max-width: 300px; /* حد أقصى للعرض */
}}

.admin-dashboard-section .dashboard-link-item:hover {{
    background-color: #e6e9ee;
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}}

.admin-dashboard-section .dashboard-link-item a {{
    color: #007bff; /* لون أزرق للروابط */
    display: block;
}}

.admin-dashboard-section .dashboard-link-item a:hover {{
    color: #0056b3;
}}

/* استجابة للتصميم (Responsive Design) */
@media (max-width: 992px) {{
    .hero-content h2 {{
        font-size: 2.8em;
    }}
    .hero-content p {{
        font-size: 1.1em;
    }}
    .features h3, .about-section h2, .form-section h2, .nasheed-list-section h2, .category-section h2, .admin-login-form h2, .requests-list-section h2, .admin-dashboard-section h2 {{
        font-size: 2.2em;
    }}
    .feature-item, .nasheed-item, .request-item {{
        padding: 20px;
    }}
}}

@media (max-width: 768px) {{
    header .container {{
        flex-direction: column;
        text-align: center;
    }}
    nav ul {{
        flex-direction: column;
        margin-top: 20px;
    }}
    nav ul li {{
        margin: 0 0 12px 0;
    }}
    .hero {{
        padding: 80px 15px;
    }}
    .hero-content h2 {{
        font-size: 2.2em;
    }}
    .hero-content p {{
        font-size: 1em;
    }}
    .btn {{
        padding: 12px 25px;
        font-size: 1em;
    }}
    .feature-grid, .nasheed-list, .category-grid, .request-list {{
        grid-template-columns: 1fr;
    }}
    .about-section, .form-section, .nasheed-list-section, .category-section, .admin-login-form, .requests-list-section, .admin-dashboard-section {{
        padding: 25px;
    }}
    .nasheed-actions a, .nasheed-actions button, .request-actions button {{
        padding: 8px 15px;
        font-size: 0.9em;
    }}
    .admin-dashboard-section .dashboard-link-item {{
        flex-basis: 100%; /* على الشاشات الصغيرة، كل عنصر يأخذ سطر كامل */
        max-width: 100%;
    }}
}}

@media (max-width: 480px) {{
    .logo {{
        font-size: 1.8em;
    }}
    .hero-content h2 {{
        font-size: 1.8em;
    }}
    .hero-content p {{
        font-size: 0.9em;
    }}
    .features h3, .about-section h2, .form-section h2, .nasheed-list-section h2, .category-section h2, .admin-login-form h2, .requests-list-section h2, .admin-dashboard-section h2 {{
        font-size: 1.8em;
    }}
}}
"""

# -----------------------------------------------------
# القوالب المعدلة (كل قالب أصبح مكتملاً بذاته)
# -----------------------------------------------------

# كود HTML للصفحة الرئيسية (home.html) - تم تعديل قسم الفئات والميزات
HOME_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الرئيسية - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="hero">
                <div class="hero-content">
                    <h2>مرحباً بكم في <br> عالم الأناشيد الهادف</h2>
                    <p>اكتشفوا مجموعة واسعة من الأناشيد التربوية والدينية الرائعة باللغات العربية، الإنجليزية، والفرنسية.</p>
                    <a href="{{{{ url_for('nasheed_list') }}}}" class="btn">استكشف الأناشيد</a>
                </div>
            </section>

            <section class="features">
                <h3>لماذا أناشيد الهدى؟</h3>
                <p class="intro-text">نقدم لكم مجموعة مميزة من الأناشيد الهادفة والتربوية التي تسعى لغرس القيم النبيلة والارتقاء بالذوق العام. استمتعوا بتجربة فريدة ومفيدة.</p>
            </section>

            <section class="category-section">
                <h2>تصفح حسب الفئة</h2>
                {{% if categories %}}
                    <div class="category-grid">
                        {{% for category in categories %}}
                            <div class="category-item">
                                <h4><a href="{{{{ url_for('nasheed_by_category', category_name=category) }}}}">{{{{ category }}}}</a></h4>
                            </div>
                        {{% endfor %}}
                    </div>
                {{% else %}}
                    <p style="text-align: center; font-size: 1.1em; color: #777;">لا توجد فئات متاحة حالياً. أضف بعض الأناشيد لتظهر الفئات هنا.</p>
                {{% endif %}}
            </section>

        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# كود HTML لصفحة "عنا" (about.html)
ABOUT_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>عن الموقع - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="about-section">
                <h2>عن موقع أناشيد الهدى</h2>
                <p>موقع "أناشيد الهدى" هو منصة رقمية متخصصة في تقديم مجموعة واسعة من الأناشيد الهادفة والملهمة.</p>
                <p>نؤمن بقوة الأناشيد في تشكيل الوعي وغرس القيم الإيجابية، ولذلك نقدم محتوى تربويًا ودينيًا غنيًا يناسب الأطفال والشباب والأسرة بأكملها.</p>
                <p>يهدف موقعنا إلى توفير بيئة آمنة وممتعة حيث يمكن للمستخدمين الاستماع إلى أناشيد متنوعة باللغات العربية، الإنجليزية، والفرنسية، وكلها مصممة لتعزيز الأخلاق الحميدة والتفكير الإيجابي.</p>
                <p>نحن نعمل باستمرار على إضافة أناشيد جديدة وميزات مبتكرة لتقديم أفضل تجربة ممكنة لمستخدمينا الكرام.</p>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# كود HTML لصفحة إضافة نشيد للمسؤول (add_nasheed.html)
ADD_NASHEED_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إضافة نشيد جديد - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="form-section">
                <h2>إضافة نشيد جديد (للمسؤول)</h2>
                <form method="POST" action="{{{{ url_for('add_nasheed_admin') }}}}" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="title">عنوان النشيد:</label>
                        <input type="text" id="title" name="title" required value="{{{{ request.form.title if request.method == 'POST' else '' }}}}">
                    </div>
                    <div class="form-group">
                        <label for="description">الوصف:</label>
                        <textarea id="description" name="description">{{{{ request.form.description if request.method == 'POST' else '' }}}}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="language">اللغة:</label>
                        <select id="language" name="language" required>
                            <option value="ar" {{% if request.method == 'POST' and request.form.language == 'ar' %}}selected{{% endif %}}>العربية</option>
                            <option value="en" {{% if request.method == 'POST' and request.form.language == 'en' %}}selected{{% endif %}}>الإنجليزية</option>
                            <option value="fr" {{% if request.method == 'POST' and request.form.language == 'fr' %}}selected{{% endif %}}>الفرنسية</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="audio_file">ملف الصوت (بصيغة MP3):</label>
                        <input type="file" id="audio_file" name="audio_file" accept="audio/mpeg" required>
                        <small>يرجى اختيار ملف MP3 للنشيد.</small>
                    </div>
                    <div class="form-group">
                        <label for="category">الفئة:</label>
                        <input type="text" id="category" name="category" value="{{{{ request.form.category if request.method == 'POST' else '' }}}}" >
                        <small>مثلاً: ديني، تربوي، طبيعة، أطفال.</small>
                    </div>
                    <button type="submit" class="btn">إضافة النشيد</button>
                </form>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# كود HTML لصفحة قائمة الأناشيد (nasheed_list.html)
NASHEED_LIST_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>قائمة الأناشيد - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="nasheed-list-section">
                <h2>أناشيدنا {{{{ ' - الفئة: ' + category_name if category_name else '' }}}}</h2>
                {{% if anasheed %}}
                    <div class="nasheed-list">
                        {{% for nasheed in anasheed %}}
                            <div class="nasheed-item">
                                <h3>{{{{ nasheed.title }}}}</h3>
                                <p>{{{{ nasheed.description if nasheed.description else 'لا يوجد وصف متاح.' }}}}</p>
                                <audio controls class="audio-player">
                                    <source src="{{{{ url_for('play_nasheed', nasheed_id=nasheed.id) }}}}" type="{{{{ nasheed.audio_mimetype }}}}">
                                    متصفحك لا يدعم عنصر الصوت.
                                </audio>
                                <div class="nasheed-meta">
                                    <span>اللغة: {{{{ nasheed.language|upper }}}}</span>
                                    {{% if nasheed.category %}}
                                        <span>الفئة: {{{{ nasheed.category }}}}</span>
                                    {{% endif %}}
                                </div>
                                {{% if session.get('logged_in_as_admin') %}}
                                <div class="nasheed-actions">
                                    <a href="{{{{ url_for('edit_nasheed_admin', nasheed_id=nasheed.id) }}}}" class="edit-btn">تعديل</a>
                                    <form action="{{{{ url_for('delete_nasheed_admin', nasheed_id=nasheed.id) }}}}" method="POST" style="display:inline;">
                                        <button type="submit" class="delete-btn" onclick="return confirm('هل أنت متأكد من حذف هذا النشيد؟')">حذف</button>
                                    </form>
                                </div>
                                {{% endif %}}
                            </div>
                        {{% endfor %}}
                    </div>
                {{% else %}}
                    <p style="text-align: center; font-size: 1.2em; color: #555;">لا توجد أناشيد لعرضها حالياً.
                    {{% if session.get('logged_in_as_admin') %}}
                         <a href="{{{{ url_for('add_nasheed_admin') }}}}" class="btn" style="background-color: #007bff;">أضف نشيداً جديداً</a>
                    {{% else %}}
                         <a href="{{{{ url_for('request_nasheed') }}}}" class="btn" style="background-color: #fd7e14;">اطلب إضافة نشيد</a>
                    {{% endif %}}
                    .</p>
                {{% endif %}}
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# كود HTML لصفحة تعديل نشيد (edit_nasheed.html)
EDIT_NASHEED_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تعديل نشيد - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="form-section">
                <h2>تعديل النشيد: {{{{ nasheed.title }}}}</h2>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="title">عنوان النشيد:</label>
                        <input type="text" id="title" name="title" value="{{{{ nasheed.title }}}}" required>
                    </div>
                    <div class="form-group">
                        <label for="description">الوصف:</label>
                        <textarea id="description" name="description">{{{{ nasheed.description }}}}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="language">اللغة:</label>
                        <select id="language" name="language" required>
                            <option value="ar" {{% if nasheed.language == 'ar' %}}selected{{% endif %}}>العربية</option>
                            <option value="en" {{% if nasheed.language == 'en' %}}selected{{% endif %}}>الإنجليزية</option>
                            <option value="fr" {{% if nasheed.language == 'fr' %}}selected{{% endif %}}>الفرنسية</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="audio_file">ملف الصوت (إذا أردت تغييره، اترك فارغًا للحفاظ على القديم):</label>
                        <input type="file" id="audio_file" name="audio_file" accept="audio/mpeg">
                        <small>الملف الحالي: (موجود)</small>
                    </div>
                    <div class="form-group">
                        <label for="category">الفئة:</label>
                        <input type="text" id="category" name="category" value="{{{{ nasheed.category }}}}" >
                        <small>مثلاً: ديني، تربوي، طبيعة، أطفال.</small>
                    </div>
                    <button type="submit" class="btn">حفظ التعديلات</button>
                    <a href="{{{{ url_for('nasheed_list') }}}}" class="btn" style="background-color: #6c757d; color: white;">إلغاء</a>
                </form>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# قالب صفحة تسجيل الدخول للمسؤول
ADMIN_LOGIN_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول كمسؤول - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="admin-login-form">
                <h2>تسجيل الدخول كمسؤول</h2>
                <form method="POST" action="{{{{ url_for('admin_login') }}}}">
                    <div class="form-group">
                        <label for="admin_code">كود المسؤول السري:</label>
                        <input type="password" id="admin_code" name="admin_code" required>
                    </div>
                    <button type="submit" class="btn">تسجيل الدخول</button>
                </form>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# قالب صفحة طلب إضافة نشيد (للمستخدم العادي)
REQUEST_NASHEED_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>طلب إضافة نشيد - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="form-section">
                <h2>طلب إضافة نشيد</h2>
                <p style="text-align: center; color: #555; margin-bottom: 30px;">يرجى ملء النموذج التالي لطلب إضافة نشيد إلى الموقع. سيقوم فريق الإدارة بمراجعة طلبك.</p>
                <form method="POST" action="{{{{ url_for('request_nasheed') }}}}" >
                    <div class="form-group">
                        <label for="title">عنوان النشيد المقترح:</label>
                        <input type="text" id="title" name="title" required value="{{{{ request.form.title if request.method == 'POST' else '' }}}}">
                    </div>
                    <div class="form-group">
                        <label for="description">وصف موجز للنشيد:</label>
                        <textarea id="description" name="description">{{{{ request.form.description if request.method == 'POST' else '' }}}}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="language">لغة النشيد:</label>
                        <select id="language" name="language" required>
                            <option value="ar" {{% if request.method == 'POST' and request.form.language == 'ar' %}}selected{{% endif %}}>العربية</option>
                            <option value="en" {{% if request.method == 'POST' and request.form.language == 'en' %}}selected{{% endif %}}>الإنجليزية</option>
                            <option value="fr" {{% if request.method == 'POST' and request.form.language == 'fr' %}}selected{{% endif %}}>الفرنسية</option>
                        </select>
                    </div>
                     <div class="form-group">
                        <label for="category">الفئة المقترحة:</label>
                        <input type="text" id="category" name="category" value="{{{{ request.form.category if request.method == 'POST' else '' }}}}" >
                        <small>مثلاً: ديني، تربوي، طبيعة، أطفال.</small>
                    </div>
                    <div class="form-group">
                        <label for="audio_link">رابط النشيد (YouTube, Google Drive, SoundCloud, إلخ):</label>
                        <input type="text" id="audio_link" name="audio_link" required value="{{{{ request.form.audio_link if request.method == 'POST' else '' }}}}">
                        <small>الرجاء توفير رابط مباشر لملف الصوت أو الفيديو. مثال: https://example.com/mypeacefulnasheed.mp3</small>
                    </div>
                    <div class="form-group">
                        <label for="contact_info">معلومات التواصل (رقم هاتف أو بريد إلكتروني):</label>
                        <input type="text" id="contact_info" name="contact_info" required value="{{{{ request.form.contact_info if request.method == 'POST' else '' }}}}">
                        <small>لنتواصل معك بخصوص طلبك.</small>
                    </div>
                    <button type="submit" class="btn">إرسال الطلب</button>
                </form>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# قالب صفحة عرض طلبات الأناشيد (للمسؤول)
VIEW_NASHEED_REQUESTS_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>طلبات الأناشيد - لوحة المسؤول</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="requests-list-section">
                <h2>طلبات الأناشيد المعلقة</h2>
                {{% if requests %}}
                    <div class="request-list">
                        {{% for req in requests %}}
                            <div class="request-item">
                                <h3>{{{{ req.title }}}}</h3>
                                <p>الوصف: {{{{ req.description if req.description else 'لا يوجد وصف.' }}}}</p>
                                <p>اللغة: {{{{ req.language|upper }}}}</p>
                                <p>الفئة: {{{{ req.category if req.category else 'غير محددة' }}}}</p>
                                <p>رابط النشيد: <a href="{{{{ req.audio_link }}}}" target="_blank" style="word-break: break-all;">{{{{ req.audio_link }}}}</a></p>
                                <div class="meta-info">
                                    <span>معلومات التواصل: {{{{ req.contact_info }}}}</span>
                                    <span>تاريخ الطلب: {{{{ req.request_date }}}}</span>
                                </div>
                                <div class="request-actions">
                                    <form action="{{{{ url_for('approve_nasheed_request', request_id=req.id) }}}}" method="POST" style="display:inline;">
                                        <button type="submit" class="approve-btn" onclick="return confirm('هل أنت متأكد من الموافقة على هذا النشيد؟ سيتم إضافته إلى الأناشيد بملف صوتي وهمي.')">موافقة</button>
                                    </form>
                                    <form action="{{{{ url_for('reject_nasheed_request', request_id=req.id) }}}}" method="POST" style="display:inline;">
                                        <button type="submit" class="reject-btn" onclick="return confirm('هل أنت متأكد من رفض هذا النشيد؟ سيتم حذفه من الطلبات.')">رفض</button>
                                    </form>
                                </div>
                            </div>
                        {{% endfor %}}
                    </div>
                {{% else %}}
                    <p style="text-align: center; font-size: 1.2em; color: #555;">لا توجد طلبات أناشيد معلقة حالياً.</p>
                {{% endif %}}
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# قالب لوحة تحكم المسؤول (admin_dashboard.html) - جديد
ADMIN_DASHBOARD_HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة تحكم المسؤول - موقع الأناشيد التربوية</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_CODE}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1 class="logo"><a href="{{{{ url_for('home') }}}}">أناشيد الهدى</a></h1>
            <nav>
                <ul>
                    <li><a href="{{{{ url_for('home') }}}}">الرئيسية</a></li>
                    <li><a href="{{{{ url_for('nasheed_list') }}}}">الأناشيد</a></li>
                    <li><a href="{{{{ url_for('request_nasheed') }}}}">طلب إضافة نشيد</a></li>
                    {{% if session.get('logged_in_as_admin') %}}
                        <li><a href="{{{{ url_for('admin_dashboard') }}}}" style="background-color: #007bff;">لوحة تحكم المسؤول</a></li>
                        <li><a href="{{{{ url_for('admin_logout') }}}}" style="background-color: #dc3545;">تسجيل الخروج (إدارة)</a></li>
                    {{% else %}}
                        <li><a href="{{{{ url_for('admin_login') }}}}" style="background-color: #6c757d;">تسجيل الدخول (إدارة)</a></li>
                    {{% endif %}}
                    <li><a href="{{{{ url_for('about') }}}}">عن الموقع</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {{% with messages = get_flashed_messages(with_categories=true) %}}
                {{% if messages %}}
                    <ul class="flashes">
                        {{% for category, message in messages %}}
                            <li class="{{{{ category }}}}">{{{{ message }}}}</li>
                        {{% endfor %}}
                    </ul>
                {{% endif %}}
            {{% endwith %}}
            <section class="admin-dashboard-section">
                <h2>لوحة تحكم المسؤول</h2>
                <div class="dashboard-links">
                    <div class="dashboard-link-item">
                        <a href="{{{{ url_for('view_nasheed_requests') }}}}">إدارة طلبات الأناشيد ({{{{ pending_requests_count }}}})</a>
                        <p style="font-size: 0.9em; color: #777; margin-top: 5px;">مراجعة طلبات إضافة الأناشيد من المستخدمين.</p>
                    </div>
                    <div class="dashboard-link-item">
                        <a href="{{{{ url_for('add_nasheed_admin') }}}}">إضافة نشيد جديد</a>
                        <p style="font-size: 0.9em; color: #777; margin-top: 5px;">إضافة أناشيد مباشرة إلى الموقع.</p>
                    </div>
                    <div class="dashboard-link-item">
                        <a href="{{{{ url_for('nasheed_list') }}}}" style="color: #28a745;">عرض/تعديل/حذف الأناشيد</a>
                        <p style="font-size: 0.9em; color: #777; margin-top: 5px;">إدارة الأناشيد المنشورة حالياً.</p>
                    </div>
                </div>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2024 أناشيد الهدى. جميع الحقوق محفوظة.</p>
        </div>
    </footer>
</body>
</html>
"""

# --- مسارات التطبيق (Routes) ---

# مزخرف للتحقق من صلاحيات المسؤول
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in_as_admin'):
            flash('الرجاء تسجيل الدخول كمسؤول للوصول إلى هذه الصفحة.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    conn = get_db_connection()
    # استخراج الفئات الفريدة الموجودة في الأناشيد المنشورة
    categories_rows = conn.execute('SELECT DISTINCT category FROM nasheed WHERE category IS NOT NULL AND category != ""').fetchall()
    conn.close()
    categories = [row['category'] for row in categories_rows]
    return render_template_string(HOME_HTML_TEMPLATE, categories=categories)

@app.route('/about')
def about():
    return render_template_string(ABOUT_HTML_TEMPLATE)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if session.get('logged_in_as_admin'):
        flash('أنت مسجل الدخول بالفعل كمسؤول.', 'info')
        return redirect(url_for('admin_dashboard')) # توجيه للوحة التحكم مباشرة

    if request.method == 'POST':
        admin_code = request.form.get('admin_code')
        if admin_code == app.config['ADMIN_SECRET_CODE']:
            session['logged_in_as_admin'] = True
            flash('تم تسجيل الدخول كمسؤول بنجاح!', 'success')
            return redirect(url_for('admin_dashboard')) # توجيه إلى لوحة تحكم المسؤول
        else:
            flash('كود المسؤول غير صحيح.', 'danger')
    return render_template_string(ADMIN_LOGIN_HTML_TEMPLATE)

@app.route('/admin_logout')
def admin_logout():
    session.pop('logged_in_as_admin', None)
    flash('تم تسجيل الخروج من وضع المسؤول.', 'info')
    return redirect(url_for('home'))

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    """لوحة تحكم المسؤول تعرض عدد الطلبات المعلقة."""
    conn = get_db_connection()
    pending_requests_count = conn.execute("SELECT COUNT(*) FROM nasheed_requests WHERE status = 'pending'").fetchone()[0]
    conn.close()
    return render_template_string(ADMIN_DASHBOARD_HTML_TEMPLATE, pending_requests_count=pending_requests_count)


@app.route('/add_nasheed', methods=['GET', 'POST'])
@admin_required # حماية المسار
def add_nasheed_admin():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        language = request.form['language']
        category = request.form['category']
        
        audio_file = request.files.get('audio_file')

        if not title:
            flash('الرجاء إدخال عنوان النشيد.', 'danger')
            return render_template_string(ADD_NASHEED_HTML_TEMPLATE, request=request)

        if not audio_file or audio_file.filename == '':
            flash('الرجاء اختيار ملف صوتي.', 'danger')
            return render_template_string(ADD_NASHEED_HTML_TEMPLATE, request=request)
        
        # التحقق من نوع الملف وحجمه (يمكن إضافة قيود أكثر صرامة هنا)
        if not audio_file.mimetype or audio_file.mimetype not in ALLOWED_MEDIA_TYPES:
            flash('الملف المرفوع ليس ملف صوتي/فيديو صالحاً. الرجاء اختيار ملف من نوع MP3، MP4، WAV، أو OGG.', 'danger')
            return render_template_string(ADD_NASHEED_HTML_TEMPLATE, request=request)
        
        # قراءة البيانات الصوتية
        try:
            audio_data = audio_file.read()
            audio_mimetype = audio_file.mimetype
        except Exception as e:
            flash(f'حدث خطأ أثناء قراءة ملف الصوت: {e}', 'danger')
            print(f"Error reading audio file: {e}")
            return render_template_string(ADD_NASHEED_HTML_TEMPLATE, request=request)


        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO nasheed (title, description, language, audio_data, audio_mimetype, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, description, language, audio_data, audio_mimetype, category))
            conn.commit()
            flash('تم إضافة النشيد بنجاح!', 'success')
            return redirect(url_for('nasheed_list'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'حدث خطأ أثناء إضافة النشيد إلى قاعدة البيانات: {e}', 'danger')
            print(f"Database error adding nasheed: {e}")
        finally:
            conn.close()
    return render_template_string(ADD_NASHEED_HTML_TEMPLATE, request=request)

@app.route('/anasheed')
def nasheed_list():
    conn = get_db_connection()
    anasheed_rows = conn.execute('SELECT * FROM nasheed').fetchall()
    conn.close()

    anasheed = [dict(row) for row in anasheed_rows]
    return render_template_string(NASHEED_LIST_HTML_TEMPLATE, anasheed=anasheed, category_name=None)

@app.route('/anasheed/category/<string:category_name>')
def nasheed_by_category(category_name):
    conn = get_db_connection()
    anasheed_rows = conn.execute('SELECT * FROM nasheed WHERE category = ?', (category_name,)).fetchall()
    conn.close()

    anasheed = [dict(row) for row in anasheed_rows]
    return render_template_string(NASHEED_LIST_HTML_TEMPLATE, anasheed=anasheed, category_name=category_name)


@app.route('/play_nasheed/<int:nasheed_id>')
def play_nasheed(nasheed_id):
    conn = get_db_connection()
    nasheed_row = conn.execute('SELECT audio_data, audio_mimetype FROM nasheed WHERE id = ?', (nasheed_id,)).fetchone()
    conn.close()

    if nasheed_row:
        return send_file(BytesIO(nasheed_row['audio_data']), mimetype=nasheed_row['audio_mimetype'], as_attachment=False)
    else:
        flash('لم يتم العثور على النشيد.', 'danger')
        return redirect(url_for('nasheed_list'))

@app.route('/edit_nasheed/<int:nasheed_id>', methods=['GET', 'POST'])
@admin_required # حماية المسار
def edit_nasheed_admin(nasheed_id):
    conn = get_db_connection()
    nasheed = conn.execute('SELECT * FROM nasheed WHERE id = ?', (nasheed_id,)).fetchone()

    if nasheed is None:
        conn.close()
        flash('لم يتم العثور على النشيد المطلوب.', 'danger')
        return redirect(url_for('nasheed_list'))
    
    nasheed = dict(nasheed) # تحويل الصف إلى قاموس

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        language = request.form['language']
        category = request.form['category']
        
        audio_file = request.files.get('audio_file')
        
        if not title:
            flash('الرجاء إدخال عنوان النشيد.', 'danger')
            conn.close()
            return render_template_string(EDIT_NASHEED_HTML_TEMPLATE, nasheed=nasheed)

        if audio_file and audio_file.filename != '':
            if not audio_file.mimetype or audio_file.mimetype not in ALLOWED_MEDIA_TYPES:
                flash('الملف المرفوع ليس ملف صوتي/فيديو صالحاً. الرجاء اختيار ملف من نوع MP3، MP4، WAV، أو OGG.', 'danger')
                conn.close()
                return render_template_string(EDIT_NASHEED_HTML_TEMPLATE, nasheed=nasheed)
            
            try:
                audio_data = audio_file.read()
                audio_mimetype = audio_file.mimetype
                conn.execute('''
                    UPDATE nasheed
                    SET title = ?, description = ?, language = ?, audio_data = ?, audio_mimetype = ?, category = ?
                    WHERE id = ?
                ''', (title, description, language, audio_data, audio_mimetype, category, nasheed_id))
                conn.commit()
                flash('تم تعديل النشيد بنجاح!', 'success')
                return redirect(url_for('nasheed_list'))
            except sqlite3.Error as e:
                conn.rollback()
                flash(f'حدث خطأ أثناء تعديل النشيد بملف صوتي جديد: {e}', 'danger')
                print(f"Error editing nasheed (with audio): {e}")
            finally:
                conn.close()
        else: # لا يوجد ملف صوتي جديد، فقط تحديث البيانات النصية
            try:
                conn.execute('''
                    UPDATE nasheed
                    SET title = ?, description = ?, language = ?, category = ?
                    WHERE id = ?
                ''', (title, description, language, category, nasheed_id))
                conn.commit()
                flash('تم تعديل معلومات النشيد بنجاح!', 'success')
                return redirect(url_for('nasheed_list'))
            except sqlite3.Error as e:
                conn.rollback()
                flash(f'حدث خطأ أثناء تعديل معلومات النشيد: {e}', 'danger')
                print(f"Error editing nasheed (text only): {e}")
            finally:
                conn.close()

    conn.close()
    return render_template_string(EDIT_NASHEED_HTML_TEMPLATE, nasheed=nasheed)

@app.route('/delete_nasheed/<int:nasheed_id>', methods=['POST'])
@admin_required # حماية المسار
def delete_nasheed_admin(nasheed_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM nasheed WHERE id = ?', (nasheed_id,))
        conn.commit()
        flash('تم حذف النشيد بنجاح!', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'حدث خطأ أثناء حذف النشيد: {e}', 'danger')
        print(f"Error deleting nasheed: {e}")
    finally:
        conn.close()
    return redirect(url_for('nasheed_list'))

# --- مسارات طلبات الأناشيد الجديدة (للمستخدم العادي والمسؤول) ---

@app.route('/request_nasheed', methods=['GET', 'POST'])
def request_nasheed():
    """يسمح للمستخدمين العاديين بطلب إضافة أناشيد جديدة."""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        language = request.form['language']
        category = request.form['category']
        audio_link = request.form['audio_link']
        contact_info = request.form['contact_info']

        if not title or not audio_link or not contact_info:
            flash('الرجاء ملء جميع الحقول المطلوبة (العنوان، رابط النشيد، معلومات التواصل).', 'danger')
            return render_template_string(REQUEST_NASHEED_HTML_TEMPLATE, request=request)
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO nasheed_requests (title, description, language, category, audio_link, contact_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, description, language, category, audio_link, contact_info))
            conn.commit()
            flash('تم إرسال طلبك بنجاح! سيقوم فريق الإدارة بمراجعته قريباً.', 'success')
            return redirect(url_for('home'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'حدث خطأ أثناء إرسال طلبك: {e}', 'danger')
            print(f"Error submitting nasheed request: {e}")
        finally:
            conn.close()
    return render_template_string(REQUEST_NASHEED_HTML_TEMPLATE, request=request)

@app.route('/admin/requests')
@admin_required # حماية المسار
def view_nasheed_requests():
    """يعرض لمدير الموقع طلبات الأناشيد المعلقة."""
    conn = get_db_connection()
    # جلب الطلبات التي لم يتم الموافقة عليها أو رفضها بعد
    requests_rows = conn.execute("SELECT * FROM nasheed_requests WHERE status = 'pending' ORDER BY request_date DESC").fetchall()
    conn.close()
    requests = [dict(row) for row in requests_rows]
    return render_template_string(VIEW_NASHEED_REQUESTS_HTML_TEMPLATE, requests=requests)

@app.route('/admin/requests/<int:request_id>/approve', methods=['POST'])
@admin_required # حماية المسار
def approve_nasheed_request(request_id):
    """يوافق على طلب نشيد ويضيفه إلى قائمة الأناشيد الرئيسية."""
    conn = get_db_connection()
    request_data = conn.execute('SELECT * FROM nasheed_requests WHERE id = ?', (request_id,)).fetchone()

    if request_data:
        request_data = dict(request_data)
        
        # بيانات dummy للملف الصوتي لأننا لا نقوم بتحميل الملف من الرابط مباشرة
        dummy_audio_data = b"This is a placeholder audio data for approved request. Please upload actual audio via edit page."
        dummy_audio_mimetype = "audio/mpeg" 

        try:
            # إضافة النشيد إلى جدول الأناشيد
            conn.execute('''
                INSERT INTO nasheed (title, description, language, audio_data, audio_mimetype, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request_data['title'],
                request_data['description'],
                request_data['language'],
                dummy_audio_data, 
                dummy_audio_mimetype, 
                request_data['category']
            ))
            
            # تحديث حالة الطلب إلى "approved"
            conn.execute("UPDATE nasheed_requests SET status = 'approved' WHERE id = ?", (request_id,))
            conn.commit()
            flash('تم الموافقة على طلب النشيد وإضافته بنجاح! (ملاحظة: ملف الصوت الافتراضي تم وضعه، يمكنك تعديله لاحقاً لرفع الملف الأصلي).', 'success')
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'حدث خطأ أثناء الموافقة على الطلب: {e}', 'danger')
            print(f"Error approving nasheed request: {e}")
        finally:
            conn.close()
    else:
        flash('طلب النشيد غير موجود.', 'danger')
    return redirect(url_for('view_nasheed_requests'))

@app.route('/admin/requests/<int:request_id>/reject', methods=['POST'])
@admin_required # حماية المسار
def reject_nasheed_request(request_id):
    """يرفض طلب نشيد ويحذفه من قائمة الطلبات."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE nasheed_requests SET status = 'rejected' WHERE id = ?", (request_id,))
        # أو يمكن حذفه مباشرة: conn.execute("DELETE FROM nasheed_requests WHERE id = ?", (request_id,))
        conn.commit()
        flash('تم رفض طلب النشيد.', 'info') # تم تغيير الرسالة
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'حدث خطأ أثناء رفض الطلب: {e}', 'danger')
        print(f"Error rejecting nasheed request: {e}")
    finally:
        conn.close()
    return redirect(url_for('view_nasheed_requests'))


if __name__ == '__main__':
    # تأكد من إنشاء مجلد anasheed_files إذا لم يكن موجوداً
    anasheed_files_path = os.path.join(app.root_path, 'anasheed_files')
    if not os.path.exists(anasheed_files_path):
        os.makedirs(anasheed_files_path)
        print(f"Created directory for initial nasheeds: {anasheed_files_path}")

    # تأكد من إنشاء مجلد static/img إذا لم يكن موجوداً (لصورة الخلفية)
    static_img_path = os.path.join(app.root_path, 'static', 'img')
    if not os.path.exists(static_img_path):
        os.makedirs(static_img_path)
        print(f"Created directory for static images: {static_img_path}")

    init_db() # يجب أن يتم استدعاء init_db() قبل تشغيل التطبيق
    app.run(host='0.0.0.0', port=5000, debug=False) # تم تغيير debug إلى False