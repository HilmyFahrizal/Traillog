"""
database.py — Schema, inisialisasi, dan seed data
TrailLog v4 (PostgreSQL / Supabase edition)
Tambahan:
- Tabel users (login by email, tanpa password)
- Tabel members (master anggota, terpisah dari trip_members)
- Tabel exercises & exercise_categories (latihan fisik)
- Fix: durasi sewa → +1 (inklusif)
"""
import psycopg2
import psycopg2.extras
import psycopg2.pool
import streamlit as st

ADMIN_EMAIL  = "hilmyfahrizal5@gmail.com"   # kept for backward-compat
ADMIN_EMAILS = ["hilmyfahrizal5@gmail.com", "aullianur794@gmail.com"]

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1, maxconn=5,
            host=st.secrets["db"]["host"],
            port=st.secrets["db"]["port"],
            dbname=st.secrets["db"]["dbname"],
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            sslmode="require",
            connect_timeout=10,
        )
    return _pool

def get_connection():
    return _get_pool().getconn()

def release_connection(conn):
    _get_pool().putconn(conn)


TABLES = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    ("users", """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(200) NOT NULL UNIQUE,
        role VARCHAR(10) NOT NULL DEFAULT 'member' CHECK (role IN ('admin','member')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),

    # ── Master Anggota (profile global, lintas trip) ───────────────────────
    ("members_master", """CREATE TABLE IF NOT EXISTS members_master (
        id SERIAL PRIMARY KEY,
        nama_lengkap VARCHAR(200) NOT NULL,
        nama_panggilan VARCHAR(100),
        nik VARCHAR(20),
        tempat_lahir VARCHAR(100),
        tanggal_lahir DATE,
        jenis_kelamin VARCHAR(20) DEFAULT 'Laki-laki' CHECK (jenis_kelamin IN ('Laki-laki','Perempuan')),
        no_hp VARCHAR(20),
        email VARCHAR(150),
        kontak_darurat_nama VARCHAR(150),
        kontak_darurat_hp VARCHAR(20),
        kontak_darurat_hubungan VARCHAR(20) DEFAULT 'Orang Tua' CHECK (kontak_darurat_hubungan IN ('Orang Tua','Saudara','Pasangan','Lainnya')),
        riwayat_penyakit TEXT,
        provinsi_id VARCHAR(10), provinsi_nama VARCHAR(100),
        kota_id VARCHAR(10), kota_nama VARCHAR(100),
        kecamatan_id VARCHAR(10), kecamatan_nama VARCHAR(100),
        kelurahan_id VARCHAR(10), kelurahan_nama VARCHAR(100),
        alamat_lengkap TEXT,
        catatan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),

    # ── Trip ──────────────────────────────────────────────────────────────────
    ("trips", """CREATE TABLE IF NOT EXISTS trips (
        id SERIAL PRIMARY KEY,
        nama_trip VARCHAR(200) NOT NULL,
        gunung_tujuan VARCHAR(200) NOT NULL,
        tipe_pendakian VARCHAR(10) NOT NULL DEFAULT 'Camping' CHECK (tipe_pendakian IN ('Tektok','Camping')),
        jalur_pendakian VARCHAR(200),
        tanggal_berangkat DATE NOT NULL,
        tanggal_kembali DATE,
        durasi_hari INT GENERATED ALWAYS AS (
            (tanggal_kembali - tanggal_berangkat) + 1
        ) STORED,
        jumlah_orang INT NOT NULL DEFAULT 1,
        status VARCHAR(20) DEFAULT 'Perencanaan' CHECK (status IN ('Perencanaan','Aktif','Selesai','Dibatalkan')),
        catatan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),

    ("trip_members", """CREATE TABLE IF NOT EXISTS trip_members (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        member_master_id INT,
        nama_lengkap VARCHAR(200) NOT NULL,
        nama_panggilan VARCHAR(100),
        nik VARCHAR(20) NOT NULL,
        tempat_lahir VARCHAR(100) NOT NULL,
        tanggal_lahir DATE NOT NULL,
        jenis_kelamin VARCHAR(20) NOT NULL DEFAULT 'Laki-laki' CHECK (jenis_kelamin IN ('Laki-laki','Perempuan')),
        no_hp VARCHAR(20) NOT NULL,
        email VARCHAR(150) NOT NULL,
        kontak_darurat_nama VARCHAR(150) NOT NULL,
        kontak_darurat_hp VARCHAR(20) NOT NULL,
        kontak_darurat_hubungan VARCHAR(20) NOT NULL DEFAULT 'Orang Tua' CHECK (kontak_darurat_hubungan IN ('Orang Tua','Saudara','Pasangan','Lainnya')),
        riwayat_penyakit TEXT,
        provinsi_id VARCHAR(10), provinsi_nama VARCHAR(100),
        kota_id VARCHAR(10), kota_nama VARCHAR(100),
        kecamatan_id VARCHAR(10), kecamatan_nama VARCHAR(100),
        kelurahan_id VARCHAR(10), kelurahan_nama VARCHAR(100),
        alamat_lengkap TEXT NOT NULL,
        catatan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
        FOREIGN KEY (member_master_id) REFERENCES members_master(id) ON DELETE SET NULL
    )"""),

    ("categories", """CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        nama_kategori VARCHAR(100) NOT NULL UNIQUE,
        jenis VARCHAR(20) NOT NULL DEFAULT 'Alat' CHECK (jenis IN ('Alat','Logistik','Simaksi','Transportasi','Lainnya')),
        icon VARCHAR(10) DEFAULT '📦',
        deskripsi TEXT,
        urutan INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),

    ("items", """CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY,
        nama_item VARCHAR(200) NOT NULL,
        category_id INT NOT NULL,
        satuan VARCHAR(50) DEFAULT 'pcs',
        berat_gram INT DEFAULT 0,
        tujuan VARCHAR(20) NOT NULL DEFAULT 'Personal' CHECK (tujuan IN ('Kelompok','Personal')),
        label VARCHAR(20) NOT NULL DEFAULT 'Wajib' CHECK (label IN ('Wajib','Disarankan','Opsional')),
        deskripsi TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )"""),

    ("trip_items", """CREATE TABLE IF NOT EXISTS trip_items (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        nama_item VARCHAR(200) NOT NULL,
        category_id INT,
        jenis_pengadaan VARCHAR(10) NOT NULL DEFAULT 'Beli' CHECK (jenis_pengadaan IN ('Beli','Sewa','DP','Dimiliki')),
        tanggal_sewa_mulai DATE,
        durasi_sewa_hari INT DEFAULT 1,
        tanggal_sewa_selesai DATE,
        jumlah DECIMAL(10,2) DEFAULT 1,
        satuan VARCHAR(50) DEFAULT 'pcs',
        berat_gram DECIMAL(10,2) DEFAULT 0,
        berat_satuan VARCHAR(20) DEFAULT 'gram',
        harga_satuan DECIMAL(12,2) DEFAULT 0,
        tipe_scope VARCHAR(10) NOT NULL DEFAULT 'Kelompok' CHECK (tipe_scope IN ('Kelompok','Personal')),
        personal_semua BOOLEAN DEFAULT FALSE,
        ditanggung_member_id INT,
        catatan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
        FOREIGN KEY (ditanggung_member_id) REFERENCES trip_members(id) ON DELETE SET NULL
    )"""),

    ("trip_item_members", """CREATE TABLE IF NOT EXISTS trip_item_members (
        id SERIAL PRIMARY KEY,
        trip_item_id INT NOT NULL,
        member_id INT NOT NULL,
        UNIQUE (trip_item_id, member_id),
        FOREIGN KEY (trip_item_id) REFERENCES trip_items(id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES trip_members(id) ON DELETE CASCADE
    )"""),

    ("trip_checklist_group", """CREATE TABLE IF NOT EXISTS trip_checklist_group (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        trip_item_id INT,
        item_id INT,
        nama_item VARCHAR(200) NOT NULL,
        category_id INT,
        label VARCHAR(20) DEFAULT 'Wajib' CHECK (label IN ('Wajib','Disarankan','Opsional')),
        sudah_siap BOOLEAN DEFAULT FALSE,
        dibawa_oleh INT,
        catatan TEXT,
        sumber VARCHAR(10) DEFAULT 'Manual' CHECK (sumber IN ('Biaya','Master','Manual')),
        urutan INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
        FOREIGN KEY (trip_item_id) REFERENCES trip_items(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
        FOREIGN KEY (dibawa_oleh) REFERENCES trip_members(id) ON DELETE SET NULL
    )"""),

    ("trip_checklist_personal", """CREATE TABLE IF NOT EXISTS trip_checklist_personal (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        member_id INT NOT NULL,
        trip_item_id INT,
        item_id INT,
        nama_item VARCHAR(200) NOT NULL,
        category_id INT,
        label VARCHAR(20) DEFAULT 'Wajib' CHECK (label IN ('Wajib','Disarankan','Opsional')),
        sudah_siap BOOLEAN DEFAULT FALSE,
        catatan TEXT,
        sumber VARCHAR(10) DEFAULT 'Manual' CHECK (sumber IN ('Biaya','Master','Manual')),
        urutan INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES trip_members(id) ON DELETE CASCADE,
        FOREIGN KEY (trip_item_id) REFERENCES trip_items(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    )"""),

    ("trip_payments", """CREATE TABLE IF NOT EXISTS trip_payments (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        member_id INT NOT NULL,
        jumlah_dibayar DECIMAL(12,2) DEFAULT 0,
        tanggal_bayar DATE,
        metode_bayar VARCHAR(100) DEFAULT 'Tunai',
        keterangan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES trip_members(id) ON DELETE CASCADE
    )"""),

    ("trip_notes", """CREATE TABLE IF NOT EXISTS trip_notes (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        judul VARCHAR(200),
        isi TEXT NOT NULL,
        tipe VARCHAR(10) DEFAULT 'Umum' CHECK (tipe IN ('Umum','Penting','Darurat','Info')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
    )"""),

    # ── Latihan Fisik ─────────────────────────────────────────────────────────
    ("exercise_categories", """CREATE TABLE IF NOT EXISTS exercise_categories (
        id SERIAL PRIMARY KEY,
        nama VARCHAR(100) NOT NULL UNIQUE,
        icon VARCHAR(10) DEFAULT '💪',
        deskripsi TEXT,
        urutan INT DEFAULT 0
    )"""),

    ("exercises", """CREATE TABLE IF NOT EXISTS exercises (
        id SERIAL PRIMARY KEY,
        nama_latihan VARCHAR(200) NOT NULL,
        category_id INT NOT NULL,
        fokus VARCHAR(200),
        level VARCHAR(10) DEFAULT 'Pemula' CHECK (level IN ('Pemula','Menengah','Lanjutan')),
        durasi_menit INT DEFAULT 30,
        kalori_estimasi INT DEFAULT 0,
        otot_utama VARCHAR(300),
        peralatan VARCHAR(200) DEFAULT 'Tanpa Alat',
        instruksi TEXT,
        tips TEXT,
        gambar_url VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES exercise_categories(id)
    )"""),
]


# ── SEED DATA ─────────────────────────────────────────────────────────────────
SEED_CATEGORIES = [
    ("Tenda & Shelter",   "Alat",         "⛺","Tenda, flysheet, groundsheet",        1),
    ("Tidur & Istirahat", "Alat",         "🛏️","Sleeping bag, matras",                2),
    ("Masak & Makan",     "Alat",         "🍳","Kompor, nesting, perlengkapan masak",  3),
    ("Pakaian & Hangat",  "Alat",         "🧥","Jaket, layer, kaos, celana",           4),
    ("Keselamatan & P3K", "Alat",         "🩺","Kotak P3K, obat-obatan",              5),
    ("Navigasi & Teknis", "Alat",         "🧭","Peta, kompas, GPS, tali",              6),
    ("Tas & Carrier",     "Alat",         "🎒","Carrier, daypack, rain cover",         7),
    ("Logistik Makanan",  "Logistik",     "🍚","Beras, lauk, snack",                   8),
    ("Logistik Minuman",  "Logistik",     "💧","Air mineral, isotonic",                9),
    ("Bahan Bakar",       "Logistik",     "🔥","Gas, spiritus",                        10),
    ("Simaksi & Tiket",   "Simaksi",      "📋","Simaksi, tiket masuk",                11),
    ("Parkir & Basecamp", "Simaksi",      "🅿️","Parkir kendaraan, basecamp",          12),
    ("Transportasi",      "Transportasi", "🚌","Bensin, angkutan, travel",             13),
    ("Dokumentasi",       "Lainnya",      "📷","Kamera, memory card",                  14),
    ("Lain-lain",         "Lainnya",      "📌","Keperluan lainnya",                    15),
]

SEED_ITEMS_EXTRA = [
    ("Carrier 45L",             "Tas & Carrier",     "unit",  1400, "Personal","Wajib",      "Carrier gunung 45L"),
    ("Daypack 20-30L",          "Tas & Carrier",     "unit",   600, "Personal","Opsional",   "Tas kecil summit attack"),
    ("Sleeping Bag",            "Tidur & Istirahat", "unit",  1200, "Personal","Wajib",      "Disesuaikan suhu gunung"),
    ("Matras",                  "Tidur & Istirahat", "unit",   400, "Personal","Wajib",      "Matras gulung/foam"),
    ("Matras Inflatable",       "Tidur & Istirahat", "unit",   500, "Personal","Opsional",   "Lebih nyaman, ringan"),
    ("Jaket Windbreaker",       "Pakaian & Hangat",  "unit",   350, "Personal","Wajib",      "Tahan angin & sedikit hujan"),
    ("Jaket Polar/Down",        "Pakaian & Hangat",  "unit",   600, "Personal","Wajib",      "Lapisan hangat utama"),
    ("Kaos Lengan Panjang",     "Pakaian & Hangat",  "unit",   200, "Personal","Wajib",      "Base layer"),
    ("Celana Outdoor",          "Pakaian & Hangat",  "unit",   400, "Personal","Wajib",      "Quick dry, tidak jeans"),
    ("Kaos Kaki Wool/Tebal",    "Pakaian & Hangat",  "pasang", 100, "Personal","Wajib",      "Anti lecet & hangat"),
    ("Sepatu Gunung/Trekking",  "Pakaian & Hangat",  "pasang", 900, "Personal","Wajib",      "Waterproof lebih baik"),
    ("Sendal Gunung",           "Pakaian & Hangat",  "pasang", 350, "Personal","Disarankan", "Di tenda/basecamp"),
    ("Peta Topografi/GPX",      "Navigasi & Teknis", "set",    100, "Kelompok","Wajib",      "Rute pendakian"),
    ("Kompas",                  "Navigasi & Teknis", "unit",   100, "Kelompok","Disarankan", "Navigasi darurat"),
    ("Peluit",                  "Navigasi & Teknis", "unit",    20, "Personal","Wajib",      "Sinyal darurat"),
    ("Senter/Headlamp Cadangan","Navigasi & Teknis", "unit",   180, "Kelompok","Disarankan", "Cadangan grup"),
    ("Lighter/Korek Api",       "Masak & Makan",     "unit",    30, "Kelompok","Wajib",      "Min 2 buah"),
    ("Sendok/Sumpit/Spork",     "Masak & Makan",     "set",     50, "Personal","Wajib",      "Peralatan makan"),
    ("Botol Minum 1L",          "Masak & Makan",     "unit",   200, "Personal","Wajib",      "BPA free lebih baik"),
    ("Kantong Air (Platypus)",  "Masak & Makan",     "unit",   100, "Personal","Disarankan", "Cadangan air"),
    ("Tali Webbing 5m",         "Navigasi & Teknis", "unit",   300, "Kelompok","Disarankan", "traillog"),
    ("Trash Bag 50L",           "Lain-lain",         "pcs",     60, "Kelompok","Wajib",      "Sampah kelompok"),
    ("Tissue Basah",            "Lain-lain",         "pack",   100, "Personal","Wajib",      "Higienitas tanpa air"),
    ("Tissue Kering",           "Lain-lain",         "roll",    80, "Personal","Wajib",      "Toilet di alam"),
    ("Krim Anti-Nyamuk",        "Lain-lain",         "tube",   100, "Personal","Disarankan", "Area basecamp"),
    ("Poncho / Jas Hujan",      "Pakaian & Hangat",  "unit",   250, "Personal","Wajib",      "Hujan & angin"),
]

SEED_ITEMS = [
    ("Tenda Dome 4P",           "Tenda & Shelter",   "unit",  3200, "Kelompok","Wajib",      "Kapasitas 4 orang"),
    ("Flysheet 4x6m",           "Tenda & Shelter",   "unit",   800, "Kelompok","Disarankan","Tambahan perlindungan"),
    ("Groundsheet",             "Tenda & Shelter",   "unit",   400, "Kelompok","Wajib",      "Alas dalam tenda"),
    ("Kompor Gas Portable",     "Masak & Makan",     "unit",   350, "Kelompok","Wajib",      "1 tungku portable"),
    ("Nesting Aluminium",       "Masak & Makan",     "set",    600, "Kelompok","Wajib",      "Panci+wajan+mangkok"),
    ("Kotak P3K Lengkap",       "Keselamatan & P3K", "unit",   800, "Kelompok","Wajib",      "Plester, antiseptik"),
    ("Gas Cartridge 230g",      "Bahan Bakar",       "kaleng", 300, "Kelompok","Wajib",      "1 kaleng ~2-3 hari"),
    ("Sleeping Bag -5C",        "Tidur & Istirahat", "unit",  1200, "Personal","Wajib",      "Suhu dingin ekstrim"),
    ("Matras EVA",              "Tidur & Istirahat", "unit",   400, "Personal","Wajib",      "Matras gulung standar"),
    ("Sleeping Pad Inflatable", "Tidur & Istirahat", "unit",   500, "Personal","Opsional",   "Lebih nyaman, ringan"),
    ("Jaket Fleece",            "Pakaian & Hangat",  "unit",   450, "Personal","Wajib",      "Layer tengah"),
    ("Jas Hujan Poncho",        "Pakaian & Hangat",  "unit",   200, "Personal","Wajib",      "Poncho + cover bag"),
    ("Sarung Tangan",           "Pakaian & Hangat",  "pasang",  80, "Personal","Wajib",      "Anti dingin"),
    ("Kupluk / Balaclava",      "Pakaian & Hangat",  "unit",   100, "Personal","Wajib",      "Penutup kepala+leher"),
    ("Headlamp LED",            "Navigasi & Teknis", "unit",   180, "Personal","Wajib",      "Min 200 lumen"),
    ("Trekking Pole",           "Navigasi & Teknis", "pasang", 500, "Personal","Disarankan","Membantu saat turun"),
    ("Obat Pribadi",            "Keselamatan & P3K", "set",     50, "Personal","Wajib",      "Sesuaikan kondisi"),
    ("Carrier 60L",             "Tas & Carrier",     "unit",  1800, "Personal","Wajib",      "Carrier gunung 60L"),
    ("Rain Cover Carrier",      "Tas & Carrier",     "unit",   200, "Personal","Wajib",      "Pelindung dari hujan"),
    ("Trash Bag Besar",         "Lain-lain",         "pcs",     50, "Personal","Wajib",      "Bawa turun sampahmu!"),
    ("Sunscreen SPF 50",        "Lain-lain",         "tube",   100, "Personal","Wajib",      "Lindungi kulit dari UV"),
    ("Baterai AA",              "Navigasi & Teknis", "pack",   100, "Personal","Disarankan","Cadangan headlamp"),
    ("Power Bank",              "Dokumentasi",       "unit",   200, "Personal","Opsional",   "Jika ada sinyal"),
    ("Lip Balm",                "Lain-lain",         "unit",    20, "Personal","Disarankan","Mencegah bibir pecah"),
] + SEED_ITEMS_EXTRA

SEED_EXERCISE_CATEGORIES = [
    ("Latihan Jantung",  "❤️",  "Cardio untuk meningkatkan daya tahan kardiovaskular", 1),
    ("Kekuatan Kaki",    "🦵",  "Memperkuat otot paha, betis, dan kaki", 2),
    ("Bahu & Punggung",  "🏋️", "Latihan beban bahu, punggung atas, dan core untuk carrier", 3),
    ("Core & Stability", "🧘",  "Penguatan inti tubuh dan keseimbangan", 4),
    ("Pemanasan",        "🔥",  "Stretching dan pemanasan sebelum pendakian", 5),
    ("Pendinginan",      "🧊",  "Pemulihan otot setelah latihan/pendakian", 6),
]

# (nama, kategori, fokus, level, durasi_menit, kalori, otot_utama, peralatan, instruksi, tips)
SEED_EXERCISES = [
    # ── Jantung ────────────────────────────────────────────────────────────────
    ("Jalan Cepat Naik Tangga", "Latihan Jantung",
     "Daya tahan kardio + kaki", "Pemula", 30, 200,
     "Jantung, paha depan, betis",
     "Tangga",
     "Cari tangga minimal 3 lantai. Naiki dengan langkah cepat, turun pelan. Ulangi 5–10 set tanpa jeda panjang.",
     "Simulasi terbaik untuk tanjakan gunung. Tambah beban ransel 5kg untuk intensitas lebih."),

    ("Jogging Interval", "Latihan Jantung",
     "VO2 Max dan stamina", "Menengah", 40, 320,
     "Jantung, paru-paru, kaki",
     "Tanpa Alat",
     "Pemanasan 5 menit jalan santai. Lalu interval: lari 2 menit + jalan 1 menit. Ulangi 8–10 siklus. Cool down 5 menit.",
     "Pantau detak jantung. Target 70–85% HR maksimum saat lari. Cocok di lapangan atau jalan datar."),

    ("Bersepeda Statis/Outdoor", "Latihan Jantung",
     "Kardio rendah impact", "Pemula", 45, 280,
     "Jantung, paha, betis",
     "Sepeda",
     "Mulai dengan kecepatan sedang selama 10 menit, tingkatkan resistensi tiap 5 menit. Pertahankan RPM 70–90.",
     "Pilihan bagus untuk lutut bermasalah. Outdoor cycling di bukit = latihan spesifik terbaik."),

    ("Hiking Lokal", "Latihan Jantung",
     "Simulasi pendakian nyata", "Menengah", 120, 500,
     "Jantung, seluruh kaki, core",
     "Ransel (opsional)",
     "Cari jalur hiking terdekat. Bawa ransel 5–10kg untuk simulasi. Jaga pace konsisten, perhatikan napas.",
     "Ini latihan paling relevan! Lakukan minimal 2x sebulan sebelum pendakian besar."),

    ("Lompat Tali", "Latihan Jantung",
     "Kardio intensitas tinggi", "Menengah", 20, 250,
     "Jantung, betis, koordinasi",
     "Tali skipping",
     "Set 1: 100 lompatan biasa. Istirahat 30 detik. Set 2–5: 100 lompatan. Tingkatkan ke double-unders.",
     "Meski terlihat sederhana, efeknya luar biasa untuk stamina. Bagus untuk pemanasan pendakian."),

    # ── Kaki ───────────────────────────────────────────────────────────────────
    ("Squat", "Kekuatan Kaki",
     "Kekuatan paha dan gluteus", "Pemula", 20, 150,
     "Paha depan, gluteus, hamstring",
     "Tanpa Alat",
     "Kaki selebar bahu. Turun hingga lutut 90° atau lebih rendah. Naik dorong dari tumit. 4 set × 15 reps.",
     "Bayangkan duduk di kursi yang tidak ada. Lutut tidak boleh melewati jari kaki berlebihan."),

    ("Lunges Berjalan", "Kekuatan Kaki",
     "Keseimbangan dan kekuatan kaki", "Pemula", 15, 120,
     "Paha depan, gluteus, hamstring, betis",
     "Tanpa Alat",
     "Langkah panjang ke depan, turunkan lutut belakang hampir menyentuh tanah. Alternating kiri-kanan. 3 set × 20 langkah.",
     "Simulasikan langkah turun gunung. Pegang dumbbell untuk tambah intensitas."),

    ("Step Up Bangku", "Kekuatan Kaki",
     "Gerakan spesifik naik tangga/tanjakan", "Pemula", 20, 160,
     "Paha, gluteus, betis",
     "Bangku/tangga",
     "Naiki bangku dengan satu kaki, angkat kaki lain ke atas, turun kembali. 3 set × 12 reps per kaki. Tambah ransel untuk beban.",
     "Paling mirip gerakan mendaki! Tinggi bangku 40–50cm ideal."),

    ("Calf Raise", "Kekuatan Kaki",
     "Kekuatan betis untuk tanjakan panjang", "Pemula", 10, 60,
     "Gastrocnemius, soleus (betis)",
     "Tanpa Alat / Undakan",
     "Berdiri di undakan, tumit menggantung. Angkat badan dengan ujung kaki setinggi mungkin. Tahan 1 detik. 4 set × 20 reps.",
     "Betis yang kuat = tidak kram di gunung. Lakukan dengan satu kaki untuk intensitas lebih tinggi."),

    ("Wall Sit", "Kekuatan Kaki",
     "Daya tahan otot paha", "Pemula", 10, 80,
     "Paha depan (quadriceps)",
     "Tembok",
     "Punggung menempel tembok, lutut 90°, paha sejajar lantai. Tahan selama mungkin. 3–5 set, istirahat 60 detik.",
     "Rasakan terbakarnya paha — itu pertanda latihan efektif! Target minimal 60 detik per set."),

    ("Box Jump", "Kekuatan Kaki",
     "Power eksplosif kaki", "Lanjutan", 20, 200,
     "Seluruh kaki, gluteus, core",
     "Bangku/box 40–60cm",
     "Berdiri di depan box. Tekuk lutut, ayun tangan, lompat ke atas box dengan dua kaki. Turun pelan. 4 set × 8 reps.",
     "Latihan ini meningkatkan power untuk medan berbatu dan lompatan di trail. Pastikan mendarat lembut."),

    # ── Bahu & Punggung ────────────────────────────────────────────────────────
    ("Shoulder Press dengan Ransel", "Bahu & Punggung",
     "Simulasi beban carrier di bahu", "Menengah", 20, 130,
     "Deltoid, trapezius, trisep",
     "Ransel berisi beban (5–15kg)",
     "Isi ransel dengan berat target. Angkat ransel ke bahu dari depan, press ke atas overhead. 3 set × 10 reps.",
     "Latihan paling spesifik untuk membiasakan bahu menopang carrier. Mulai dari 5kg, naikan bertahap."),

    ("Farmer's Walk", "Bahu & Punggung",
     "Grip strength dan stabilitas bahu", "Pemula", 15, 100,
     "Trapezius, forearm, core",
     "Dumbbell / galon air / karung",
     "Pegang beban di kedua sisi. Jalan tegak dengan langkah pendek selama 30–50 meter. 4 set.",
     "Simulasi membawa air atau perlengkapan tambahan. Punggung tetap tegak, core dikencangkan."),

    ("Dumbbell Row / Barbell Row", "Bahu & Punggung",
     "Kekuatan punggung tengah", "Menengah", 25, 160,
     "Latissimus dorsi, rhomboid, bicep",
     "Dumbbell / Barbell",
     "Condong 45°, tarik beban ke arah pinggul dengan siku dekat badan. 4 set × 12 reps per sisi.",
     "Punggung yang kuat mengurangi kelelahan saat memikul carrier. Fokus kontraksi otot punggung."),

    ("Face Pull dengan Resistance Band", "Bahu & Punggung",
     "Kesehatan sendi bahu", "Pemula", 15, 70,
     "Posterior deltoid, rotator cuff, rhomboid",
     "Resistance band",
     "Ikat band di ketinggian kepala. Tarik ke arah wajah dengan siku tinggi, tahan 1 detik. 3 set × 15 reps.",
     "Mencegah cedera bahu dari beban carrier berulang. Gerakan ini sering dilupakan tapi sangat penting."),

    ("Push-Up Pike", "Bahu & Punggung",
     "Bahu dan core tanpa alat", "Menengah", 15, 110,
     "Deltoid anterior, trisep, core",
     "Tanpa Alat",
     "Posisi push-up, angkat pinggul tinggi (bentuk segitiga). Turunkan kepala ke lantai, dorong kembali. 3 set × 10 reps.",
     "Variasi push-up yang menarget bahu secara spesifik. Bagus untuk pendaki yang latihan di rumah."),

    # ── Core & Stability ───────────────────────────────────────────────────────
    ("Plank", "Core & Stability",
     "Kekuatan inti dan stabilitas", "Pemula", 10, 50,
     "Transverse abdominis, oblique, erector spinae",
     "Tanpa Alat",
     "Posisi push-up, tahan di titik tertinggi (atau siku). Badan lurus dari kepala ke tumit. Tahan 30–60 detik. 4 set.",
     "Core yang kuat = postur baik saat memikul carrier. Tingkatkan durasi tiap minggu secara bertahap."),

    ("Dead Bug", "Core & Stability",
     "Stabilitas core dan koordinasi", "Pemula", 15, 60,
     "Deep core, hip flexor, koordinasi",
     "Tanpa Alat",
     "Telentang, angkat tangan dan kaki 90°. Turunkan tangan kanan + kaki kiri bersamaan hampir ke lantai. Balik. 3 set × 10.",
     "Melatih core tanpa tekanan di punggung. Sempurna untuk pemula atau pemulihan."),

    ("Bird Dog", "Core & Stability",
     "Keseimbangan dan stabilitas punggung", "Pemula", 15, 55,
     "Erector spinae, gluteus, core",
     "Tanpa Alat",
     "Posisi merangkak. Angkat tangan kanan + kaki kiri lurus dan sejajar lantai. Tahan 2 detik. Ganti sisi. 3 set × 12 reps.",
     "Sangat baik untuk mencegah nyeri punggung bawah saat membawa carrier berat."),

    ("Russian Twist", "Core & Stability",
     "Kekuatan rotasi core", "Menengah", 15, 80,
     "Oblique, hip flexor",
     "Dumbbell / botol air (opsional)",
     "Duduk, lutut tekuk, kaki terangkat. Putar badan kiri-kanan sambil pegang beban. 3 set × 20 reps.",
     "Membantu keseimbangan saat melintasi medan berbatu dengan membawa beban di satu sisi."),

    # ── Pemanasan ─────────────────────────────────────────────────────────────
    ("Dynamic Stretching", "Pemanasan",
     "Pemanasan sebelum latihan/pendakian", "Pemula", 10, 30,
     "Seluruh tubuh",
     "Tanpa Alat",
     "Leg swing 10x/sisi, arm circle 10x, hip circle 10x, high knee 20x, butt kick 20x, inchworm 5x.",
     "Lakukan sebelum setiap latihan. Dynamic lebih baik dari static stretching sebelum aktivitas."),

    ("Ankle Mobility", "Pemanasan",
     "Mobilitas pergelangan kaki", "Pemula", 8, 20,
     "Ankle, betis bawah",
     "Tanpa Alat",
     "Duduk, putar pergelangan kaki searah jarum jam dan berlawanan 10x/sisi. Lalu ankle dorsiflexion ke dinding 10 reps/sisi.",
     "Pergelangan kaki yang mobile = lebih aman di medan berbatu dan licin."),

    # ── Pendinginan ──────────────────────────────────────────────────────────
    ("Foam Rolling", "Pendinginan",
     "Pemulihan otot pasca latihan", "Pemula", 15, 25,
     "Paha, betis, punggung, IT band",
     "Foam roller",
     "Roll pelan 60 detik per area: paha depan, paha belakang, betis, IT band (sisi paha luar), punggung atas.",
     "Lakukan setelah latihan atau pendakian. Tekanan sedang pada titik nyeri, tahan 10–20 detik."),

    ("Static Stretching Pasca Pendakian", "Pendinginan",
     "Pemulihan dan fleksibilitas", "Pemula", 15, 20,
     "Paha, hamstring, betis, bahu, punggung",
     "Tanpa Alat",
     "Tahan tiap peregangan 30–45 detik: hamstring, hip flexor, pigeon pose, chest opener, shoulder cross. 2 reps/sisi.",
     "Lakukan saat otot masih hangat. Jangan memaksa, rasakan regangan nyaman."),
]


TIMELINE_SCENARIO_DDL = """CREATE TABLE IF NOT EXISTS trip_timeline_scenarios (
    id SERIAL PRIMARY KEY,
    trip_id INT NOT NULL,
    nama VARCHAR(200) NOT NULL,
    deskripsi TEXT,
    urutan INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
)"""

LOGISTIK_DDL = """CREATE TABLE IF NOT EXISTS trip_logistik (
    id SERIAL PRIMARY KEY,
    trip_id INT NOT NULL,
    nama_item VARCHAR(200) NOT NULL,
    kategori VARCHAR(20) DEFAULT 'Sarapan' CHECK (kategori IN ('Sarapan','Makan Siang','Makan Malam','Snack','Minuman','Bumbu','Lainnya')),
    jumlah DECIMAL(10,2) DEFAULT 1,
    satuan VARCHAR(50) DEFAULT 'porsi',
    hari_ke INT DEFAULT 1,
    estimasi_harga DECIMAL(12,2) DEFAULT 0,
    catatan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
)"""

P3K_DDL = """CREATE TABLE IF NOT EXISTS trip_p3k (
    id SERIAL PRIMARY KEY,
    trip_id INT NOT NULL,
    nama_item VARCHAR(200) NOT NULL,
    kategori VARCHAR(20) DEFAULT 'Obat Umum' CHECK (kategori IN ('Obat Umum','Luka & Perban','Antiseptik','Alat Medis','Suplemen','Darurat','Lainnya')),
    jumlah INT DEFAULT 1,
    satuan VARCHAR(50) DEFAULT 'pcs',
    label VARCHAR(20) DEFAULT 'Wajib' CHECK (label IN ('Wajib','Disarankan','Opsional')),
    sudah_disiapkan BOOLEAN DEFAULT FALSE,
    catatan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
)"""

SEED_LOGISTIK_TEMPLATE = [
    ("Nasi + Lauk", "Makan Siang", 1, "porsi/orang"),
    ("Nasi + Lauk Malam", "Makan Malam", 1, "porsi/orang"),
    ("Roti/Sereal", "Sarapan", 1, "porsi/orang"),
    ("Air Mineral", "Minuman", 1.5, "liter/orang"),
    ("Snack Energi (cokelat, kacang)", "Snack", 2, "bungkus/orang"),
    ("Isotonic/Oralit", "Minuman", 2, "sachet/orang"),
    ("Mie Instan", "Makan Malam", 1, "bungkus/orang"),
    ("Kopi/Teh/Susu", "Minuman", 3, "sachet/orang"),
]

SEED_P3K = [
    ("Paracetamol 500mg", "Obat Umum", 20, "tablet", "Wajib", "Penurun demam & pereda nyeri"),
    ("Ibuprofen 400mg", "Obat Umum", 10, "tablet", "Wajib", "Anti-inflamasi, nyeri otot"),
    ("Antasida (Promag/Mylanta)", "Obat Umum", 10, "tablet", "Wajib", "Maag & mual"),
    ("Oralit", "Suplemen", 5, "sachet", "Wajib", "Dehidrasi & diare"),
    ("Loperamide (Diapet/Imodium)", "Obat Umum", 6, "tablet", "Wajib", "Diare"),
    ("Cetirizine/Loratadine", "Obat Umum", 6, "tablet", "Disarankan", "Alergi"),
    ("Plester Luka Berbagai Ukuran", "Luka & Perban", 20, "pcs", "Wajib", "Luka lecet"),
    ("Kasa Steril 10x10cm", "Luka & Perban", 5, "lembar", "Wajib", "Luka lebih besar"),
    ("Perban Elastis", "Luka & Perban", 2, "roll", "Wajib", "Keseleo/sprain"),
    ("Povidone Iodine (Betadine)", "Antiseptik", 1, "botol kecil", "Wajib", "Antiseptik luka"),
    ("Hand Sanitizer", "Antiseptik", 1, "botol", "Wajib", "Higienitas"),
    ("Gunting Medis Kecil", "Alat Medis", 1, "pcs", "Wajib", "Potong perban"),
    ("Pinset", "Alat Medis", 1, "pcs", "Disarankan", "Cabut duri/benda asing"),
    ("Termometer Digital", "Alat Medis", 1, "pcs", "Disarankan", "Cek suhu"),
    ("Acetosal/Aspirin", "Obat Umum", 4, "tablet", "Opsional", "Pengencer darah darurat"),
    ("Vitamin C", "Suplemen", 10, "tablet", "Disarankan", "Imunitas"),
    ("Minyak Gosok/Balsem", "Obat Umum", 1, "botol", "Wajib", "Otot pegal"),
    ("Salep Luka/Betadine Gel", "Antiseptik", 1, "tube", "Disarankan", "Infeksi luka"),
    ("Peluit Darurat", "Darurat", 1, "pcs", "Wajib", "Sinyal darurat"),
    ("Emergency Blanket (Space Blanket)", "Darurat", 1, "pcs", "Wajib", "Hipotermia"),
]


def _col_exists(cur, table, column):
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name=%s AND column_name=%s
    """, (table, column))
    return cur.fetchone() is not None


def _table_exists(cur, table):
    cur.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name=%s
    """, (table,))
    return cur.fetchone() is not None


def init_database():
    conn = get_connection()
    cur  = conn.cursor()

    for _, ddl in TABLES:
        cur.execute(ddl)
    conn.commit()

    # Seed users: admin
    cur.execute("SELECT COUNT(*) FROM users WHERE email=%s", (ADMIN_EMAIL,))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (email,role) VALUES (%s,'admin') ON CONFLICT DO NOTHING", (ADMIN_EMAIL,))
        conn.commit()

    # Seed categories
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        for row in SEED_CATEGORIES:
            cur.execute(
                "INSERT INTO categories (nama_kategori,jenis,icon,deskripsi,urutan) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                row)
        conn.commit()

    # Seed items
    cur.execute("SELECT COUNT(*) FROM items")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, nama_kategori FROM categories")
        cm = {r[1]: r[0] for r in cur.fetchall()}
        rows = [(n, cm[k], s, b, t, l, d) for n,k,s,b,t,l,d in SEED_ITEMS if k in cm]
        for row in rows:
            cur.execute(
                "INSERT INTO items (nama_item,category_id,satuan,berat_gram,tujuan,label,deskripsi) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                row)
        conn.commit()

    # Seed exercise categories
    cur.execute("SELECT COUNT(*) FROM exercise_categories")
    if cur.fetchone()[0] == 0:
        for row in SEED_EXERCISE_CATEGORIES:
            cur.execute(
                "INSERT INTO exercise_categories (nama,icon,deskripsi,urutan) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                row)
        conn.commit()

    # Seed exercises
    cur.execute("SELECT COUNT(*) FROM exercises")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, nama FROM exercise_categories")
        ecm = {r[1]: r[0] for r in cur.fetchall()}
        for nama, cat, fokus, level, dur, kal, otot, alat, instruksi, tips in SEED_EXERCISES:
            if cat in ecm:
                cur.execute("""
                    INSERT INTO exercises
                        (nama_latihan,category_id,fokus,level,durasi_menit,kalori_estimasi,
                         otot_utama,peralatan,instruksi,tips)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (nama, ecm[cat], fokus, level, dur, kal, otot, alat, instruksi, tips))
        conn.commit()

    # ── Extra tables (safe migration) ──────────────────────────────────────────
    cur.execute("""CREATE TABLE IF NOT EXISTS trip_timeline (
        id SERIAL PRIMARY KEY,
        trip_id INT NOT NULL,
        hari_ke INT NOT NULL DEFAULT 1,
        tanggal DATE,
        jam_mulai TIME,
        jam_selesai TIME,
        jam_mulai_kira TIME DEFAULT NULL,
        jam_selesai_kira TIME DEFAULT NULL,
        scenario_id INT DEFAULT NULL,
        judul VARCHAR(300) NOT NULL,
        deskripsi TEXT,
        lokasi VARCHAR(300),
        kategori VARCHAR(20) DEFAULT 'Pendakian' CHECK (kategori IN ('Perjalanan','Pendakian','Istirahat','Makan','Dokumentasi','Darurat','Lainnya')),
        icon VARCHAR(10) DEFAULT '📍',
        urutan INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS bank_info (
        id SERIAL PRIMARY KEY,
        nama_bank VARCHAR(100) NOT NULL,
        no_rekening VARCHAR(50) NOT NULL,
        atas_nama VARCHAR(150) NOT NULL,
        catatan TEXT,
        icon VARCHAR(10) DEFAULT '🏦',
        urutan INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── trip_timeline_scenarios table ─────────────────────────────────────────
    cur.execute(TIMELINE_SCENARIO_DDL)

    # ── Safe migration: tambah kolom ke trip_timeline (per kolom) ─────────────
    for col, col_type in [
        ("scenario_id",      "INT DEFAULT NULL"),
        ("jam_mulai_kira",   "TIME DEFAULT NULL"),
        ("jam_selesai_kira", "TIME DEFAULT NULL"),
    ]:
        if not _col_exists(cur, "trip_timeline", col):
            try:
                cur.execute(f"ALTER TABLE trip_timeline ADD COLUMN {col} {col_type}")
                conn.commit()
            except Exception:
                conn.rollback()

    # ── trip_logistik ──────────────────────────────────────────────────────────
    cur.execute(LOGISTIK_DDL)

    # ── trip_p3k ───────────────────────────────────────────────────────────────
    cur.execute(P3K_DDL)

    # ── Safe migration: expand jenis_pengadaan CHECK if needed ─────────────────
    # PostgreSQL: CHECK constraints can't be altered easily; skip if already correct
    try:
        cur.execute("""ALTER TABLE trip_items DROP CONSTRAINT IF EXISTS trip_items_jenis_pengadaan_check""")
        cur.execute("""ALTER TABLE trip_items ADD CONSTRAINT trip_items_jenis_pengadaan_check
            CHECK (jenis_pengadaan IN ('Beli','Sewa','DP','Dimiliki'))""")
        conn.commit()
    except Exception:
        conn.rollback()

    # ── Add member_master_id column to trip_members if not exists ──────────────
    if not _col_exists(cur, "trip_members", "member_master_id"):
        try:
            cur.execute("ALTER TABLE trip_members ADD COLUMN member_master_id INT DEFAULT NULL")
            conn.commit()
        except Exception:
            conn.rollback()

    conn.commit()
    conn.close()


# ── Stub functions for backward compatibility ─────────────────────────────────
def init_timeline_table():
    """Deprecated: now handled inside init_database(). Kept for compat."""
    pass


def init_bank_table():
    """Deprecated: now handled inside init_database(). Kept for compat."""
    pass


SEED_MEMBERS_MASTER = [
    # (nama_lengkap, nama_panggilan, nik, tempat_lahir, tanggal_lahir, jenis_kelamin,
    #  no_hp, email, kontak_darurat_nama, kontak_darurat_hp, kontak_darurat_hubungan,
    #  riwayat_penyakit, provinsi_id, provinsi_nama, kota_id, kota_nama,
    #  kecamatan_id, kecamatan_nama, kelurahan_id, kelurahan_nama, alamat_lengkap, catatan)
    ('Muh Hilmy Fahrizal', 'Hilmy', '7371122909040005', 'Kota Surabaya', '2004-12-29', 'Laki-laki',
     '081336318074', 'hilmyfahrizal5@gmail.com', 'Astiani', '082233385172', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '1178', 'Pabean Cantian', '14399', 'Perak Timur',
     'Jl. Teluk Aru Utara 69', None),

    ('Aulia Nur Alfiannissa', 'Aulia', '3525154709040001', 'Gresik', '2004-09-07', 'Perempuan',
     '085784783164', 'aullianur794@gmail.com', 'Ali Sadikin', '085230273334', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '826', 'Semampir', '18324', 'Ujung',
     'Jl Bandaran. Rusunawa TNI AL TB2 Lantai 3 No 3', None),

    ('Ali Sadikin', 'Ali', '3525151111760002', 'Semarang', '1976-11-11', 'Laki-laki',
     '085230273334', 'oncom.86ali@gmail.com', 'M Ilham Alfiansyah', '089619514755', 'Lainnya',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '826', 'Semampir', '18324', 'Ujung',
     'Jl Bandaran. Rusunawa TNI AL TB2 Lantai 3 No 3', None),

    ('Herawati', 'Herawati', '3525155501810002', 'Kota Administrasi Jakarta Timur', '1981-01-15', 'Perempuan',
     '082257885565', 'herawativicka5@gmail.com', 'M Ilham Alfiansyah', '089619514755', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '826', 'Semampir', '18324', 'Ujung',
     'Jl Bandaran. Rusunawa TNI AL TB2 Lantai 3 No 3', None),

    ('Muhammad Zakariya', 'Zaki', '3578121503090001', 'Kota Surabaya', '2009-03-15', 'Laki-laki',
     '0881027026812', 'mhmmdhzakyyy@gmail.com', 'Cholifatur Rosidah', '085334184841', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '1178', 'Pabean Cantian', '14400', 'Perak Utara',
     'Teluk Nibung Barat 1/11', None),

    ('Helya Jais Nabila', 'Helya', '3529246411040003', 'Sumenep', '2004-11-24', 'Perempuan',
     '087858168664', 'jaiszan4@gmail.com', 'Auliya Leli', '085964182779', 'Saudara',
     None, '6', 'Jawa Timur', '64', 'Sumenep', '2848', 'Arjasa', '33883', 'Duko',
     'Jl. Raya Duko Arjasa', None),

    ('Vera Febriyanti', 'Vera', '3525174402050001', 'Gresik', '2005-02-04', 'Perempuan',
     '082232949472', 'verafebriyanti245@gmail.com', 'Ade', '081357796547', 'Orang Tua',
     None, None, None, None, None, None, None, None, None,
     '', None),

    ('Jewelatique Bihisyti Zewar', 'Jebi', '3525034212040004', 'Gresik', '2004-12-02', 'Perempuan',
     '081234970329', 'jbihisyti@gmail.com', 'Mohammad Zuhri', '08551111926', 'Orang Tua',
     None, '6', 'Jawa Timur', '62', 'Gresik', '1412', 'Panceng', '72098', 'Wotan',
     'Desa Wotan, Kecamatan Panceng, Kabupaten Gresik. 61156', None),

    ('Fadhil Muhamad', 'Fadhil', '3578160604050004', 'Kota Surabaya', '2005-04-06', 'Laki-laki',
     '088996959285', 'fadhilbarunawati@gmail.com', 'Viki Mustaofa', '08252507665', 'Saudara',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '826', 'Semampir', '11191', 'Sidotopo',
     'Sidotopo Sekolahan 7/80', None),

    ('Andrian Simanjuntak', 'Andrian', '1211012510040004', 'Dairi', '2004-10-04', 'Laki-laki',
     '081331864076', 'andriansimanjuntak763@gmail.com', 'Mintauli Hutasoit', '081337453762', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '1274', 'Gayungan', '12724', 'Ketintang',
     'Jln. Ketintang Baru VII no 20', None),

    ('Aditya Saputra', 'Adit', '3578132404040003', 'Kota Surabaya', '2004-04-24', 'Laki-laki',
     '089505078712', 'aditya24sp@gmail.com', 'Imron', '0881027964779', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '816', 'Bubutan', '7438', 'Alun-Alun Contong',
     'Jalan Johar Belakang 28', None),

    ('Nando Septian Prisandy', 'Nando', '3578100709040003', 'Kota Surabaya', '2004-09-07', 'Laki-laki',
     '081233911558', 'nandodeng75@gmail.com', 'Desy Arisandy', '082143306965', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '1275', 'Tambaksari', '14842', 'Rangkah',
     'Jalan Rangkah 7 No. 106B, Rangkah, Tambaksari, Surabaya, Jawa Timur, 60135', None),

    ('Muhammad Rarendra Satiya', 'Rendra', '3578182509050001', 'Kota Surabaya', '2005-09-25', 'Laki-laki',
     '082211908989', 'mhd.rarendra@gmail.com', 'Siti Reksawati', '081232303303', 'Orang Tua',
     None, '6', 'Jawa Timur', '67', 'Kota Surabaya', '1001', 'Lakarsantri', '13115', 'Lidah Kulon',
     'PURI LIDAH KULON INDAH BLOK P-22, KECAMATAN LAKARSANTRI, SURABAYA', None),
]


def seed_from_sql():
    """Seed initial data dari daftar user dan members_master."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        # ── Seed users ────────────────────────────────────────────────────────
        users = [
            ('hilmyfahrizal5@gmail.com',          'admin'),
            ('aullianur794@gmail.com',             'admin'),
            ('oncom.86ali@gmail.com',              'member'),
            ('herawativicka5@gmail.com',           'member'),
            ('mhmmdhzakyyy@gmail.com',             'member'),
            ('jaiszan4@gmail.com',                 'member'),
            ('verafebriyanti245@gmail.com',        'member'),
            ('jbihisyti@gmail.com',                'member'),
            ('fadhilbarunawati@gmail.com',         'member'),
            ('andriansimanjuntak763@gmail.com',    'member'),
            ('aditya24sp@gmail.com',               'member'),
            ('nandodeng75@gmail.com',              'member'),
            ('mhd.rarendra@gmail.com',             'member'),
        ]
        for u in users:
            cur.execute(
                "INSERT INTO users (email, role) VALUES (%s,%s) ON CONFLICT (email) DO NOTHING",
                u)
        conn.commit()

        # ── Seed members_master ───────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM members_master")
        if cur.fetchone()[0] == 0:
            for row in SEED_MEMBERS_MASTER:
                cur.execute("""
                    INSERT INTO members_master (
                        nama_lengkap, nama_panggilan, nik, tempat_lahir, tanggal_lahir, jenis_kelamin,
                        no_hp, email, kontak_darurat_nama, kontak_darurat_hp, kontak_darurat_hubungan,
                        riwayat_penyakit, provinsi_id, provinsi_nama, kota_id, kota_nama,
                        kecamatan_id, kecamatan_nama, kelurahan_id, kelurahan_nama,
                        alamat_lengkap, catatan
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,
                        %s,%s
                    ) ON CONFLICT DO NOTHING
                """, row)
            conn.commit()

    except Exception as e:
        print("seed_from_sql error:", e)
        conn.rollback()
    finally:
        conn.close()