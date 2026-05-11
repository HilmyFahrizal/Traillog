"""
logic.py — Business logic, queries, kalkulasi
TrailLog v4

Perubahan:
- Login system (email-only, no password)
- members_master CRUD
- Kalkulasi: tagihan dikurangi menanggung → net_tagihan
- Durasi sewa: inklusif (+1 hari)
- Exercise CRUD
- Berat: konversi satuan (gram, kg, liter, ml, oz, lb)
"""
from database import get_connection, release_connection, ADMIN_EMAIL, ADMIN_EMAILS
import psycopg2.extras
from datetime import date, timedelta


# ─── DB HELPERS ───────────────────────────────────────────────────────────────
def q(sql, params=None, fetch=True):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if not fetch and sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
            cur.execute(sql, params or ())
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else None
        cur.execute(sql, params or ())
        if fetch:
            return [dict(r) for r in cur.fetchall()]
        conn.commit()
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def q1(sql, params=None):
    rows = q(sql, params)
    return rows[0] if rows else None


def qv(sql, params=None, default=0):
    row = q1(sql, params)
    if row is None:
        return default
    v = list(row.values())[0]
    return v if v is not None else default


def run(sql, params=None):
    return q(sql, params, fetch=False)


# ─── FORMAT ───────────────────────────────────────────────────────────────────
def fmt_rp(v) -> str:
    if v is None:
        return "Rp 0"
    return "Rp {:,.0f}".format(float(v)).replace(",", ".")


def fmt_berat(gram, unit="auto") -> str:
    if not gram:
        return "—"
    g = float(gram)
    if unit == "kg" or (unit == "auto" and g >= 1000):
        return "{:.2f} kg".format(g / 1000)
    return "{:.0f} g".format(g)


def hitung_usia(tgl) -> str:
    if not tgl:
        return ""
    return "{} tahun".format((date.today() - tgl).days // 365)


# ─── KONVERSI BERAT ───────────────────────────────────────────────────────────
BERAT_SATUAN_OPTS = ["gram", "kg", "liter (air≈1kg/L)", "ml", "oz", "lb"]

def to_gram(nilai, satuan):
    """Konversi berbagai satuan ke gram."""
    s = satuan.lower()
    v = float(nilai or 0)
    if s == "gram":          return v
    if s == "kg":            return v * 1000
    if "liter" in s:         return v * 1000   # air: 1L ≈ 1kg = 1000g
    if s == "ml":            return v           # 1ml ≈ 1g untuk air
    if s == "oz":            return v * 28.35
    if s == "lb":            return v * 453.59
    return v  # default gram


# ─── AUTH / LOGIN ─────────────────────────────────────────────────────────────
def get_user_by_email(email):
    return q1("SELECT * FROM users WHERE email=%s", (email.strip().lower(),))


def create_user_if_not_exist(email):
    email = email.strip().lower()
    existing = get_user_by_email(email)
    if existing:
        return existing
    run("INSERT INTO users (email, role) VALUES (%s, 'member') ON CONFLICT DO NOTHING", (email,))
    return get_user_by_email(email)


def is_admin(email):
    if not email:
        return False
    em = email.strip().lower()
    return any(em == a.lower() for a in ADMIN_EMAILS)


# ─── MEMBERS MASTER ───────────────────────────────────────────────────────────
def get_members_master(search=""):
    sql = "SELECT * FROM members_master WHERE 1=1"
    p = []
    if search:
        sql += " AND (nama_lengkap LIKE %s OR email LIKE %s OR no_hp LIKE %s)"
        p.extend(["%{}%".format(search)] * 3)
    sql += " ORDER BY nama_lengkap"
    rows = q(sql, p)
    result = []
    for row in rows:
        if row.get("provinsi_id") and not row.get("provinsi_nama"):
            row, changed = resolve_wilayah_names(row)
            if changed:
                run("UPDATE members_master SET provinsi_nama=%s,kota_nama=%s,kecamatan_nama=%s,kelurahan_nama=%s WHERE id=%s",
                    (row.get("provinsi_nama"),row.get("kota_nama"),row.get("kecamatan_nama"),row.get("kelurahan_nama"),row["id"]))
        result.append(row)
    return result


def get_member_master(mid):
    row = q1("SELECT * FROM members_master WHERE id=%s", (mid,))
    if row and row.get("provinsi_id") and not row.get("provinsi_nama"):
        row, changed = resolve_wilayah_names(row)
        if changed:
            run("UPDATE members_master SET provinsi_nama=%s,kota_nama=%s,kecamatan_nama=%s,kelurahan_nama=%s WHERE id=%s",
                (row.get("provinsi_nama"),row.get("kota_nama"),row.get("kecamatan_nama"),row.get("kelurahan_nama"),row["id"]))
    return row


def get_member_master_by_email(email):
    return q1("SELECT * FROM members_master WHERE email=%s", (email.strip().lower(),))


def _mm_params(d):
    return (
        d["nama_lengkap"], d.get("nama_panggilan"), d.get("nik"),
        d.get("tempat_lahir"), d.get("tanggal_lahir"), d.get("jenis_kelamin", "Laki-laki"),
        d.get("no_hp"), d.get("email"),
        d.get("kontak_darurat_nama"), d.get("kontak_darurat_hp"),
        d.get("kontak_darurat_hubungan", "Orang Tua"),
        d.get("riwayat_penyakit"),
        d.get("provinsi_id"), d.get("provinsi_nama"),
        d.get("kota_id"), d.get("kota_nama"),
        d.get("kecamatan_id"), d.get("kecamatan_nama"),
        d.get("kelurahan_id"), d.get("kelurahan_nama"),
        d.get("alamat_lengkap"), d.get("catatan"),
    )


def create_member_master(d):
    return run("""
        INSERT INTO members_master
            (nama_lengkap,nama_panggilan,nik,tempat_lahir,tanggal_lahir,jenis_kelamin,
             no_hp,email,kontak_darurat_nama,kontak_darurat_hp,kontak_darurat_hubungan,
             riwayat_penyakit,
             provinsi_id,provinsi_nama,kota_id,kota_nama,
             kecamatan_id,kecamatan_nama,kelurahan_id,kelurahan_nama,
             alamat_lengkap,catatan)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, _mm_params(d))


def update_member_master(mid, d):
    run("""
        UPDATE members_master SET
            nama_lengkap=%s,nama_panggilan=%s,nik=%s,tempat_lahir=%s,tanggal_lahir=%s,
            jenis_kelamin=%s,no_hp=%s,email=%s,
            kontak_darurat_nama=%s,kontak_darurat_hp=%s,kontak_darurat_hubungan=%s,
            riwayat_penyakit=%s,
            provinsi_id=%s,provinsi_nama=%s,kota_id=%s,kota_nama=%s,
            kecamatan_id=%s,kecamatan_nama=%s,kelurahan_id=%s,kelurahan_nama=%s,
            alamat_lengkap=%s,catatan=%s
        WHERE id=%s
    """, _mm_params(d) + (mid,))


def delete_member_master(mid):
    run("DELETE FROM members_master WHERE id=%s", (mid,))


def sync_trip_member_to_master(trip_member_id):
    """
    Saat anggota trip baru ditambahkan, sync ke members_master jika belum ada
    berdasarkan NIK atau email.
    """
    tm = q1("SELECT * FROM trip_members WHERE id=%s", (trip_member_id,))
    if not tm:
        return None
    # Cek berdasarkan email dulu, lalu NIK
    existing = None
    if tm.get("email"):
        existing = q1("SELECT id FROM members_master WHERE email=%s", (tm["email"],))
    if not existing and tm.get("nik"):
        existing = q1("SELECT id FROM members_master WHERE nik=%s", (tm["nik"],))

    if existing:
        # Update member_master_id di trip_member
        run("UPDATE trip_members SET member_master_id=%s WHERE id=%s", (existing["id"], trip_member_id))
        return existing["id"]
    else:
        # Buat baru di master
        mid = create_member_master({
            "nama_lengkap": tm["nama_lengkap"],
            "nama_panggilan": tm.get("nama_panggilan"),
            "nik": tm.get("nik"),
            "tempat_lahir": tm.get("tempat_lahir"),
            "tanggal_lahir": tm.get("tanggal_lahir"),
            "jenis_kelamin": tm.get("jenis_kelamin", "Laki-laki"),
            "no_hp": tm.get("no_hp"),
            "email": tm.get("email"),
            "kontak_darurat_nama": tm.get("kontak_darurat_nama"),
            "kontak_darurat_hp": tm.get("kontak_darurat_hp"),
            "kontak_darurat_hubungan": tm.get("kontak_darurat_hubungan", "Orang Tua"),
            "riwayat_penyakit": tm.get("riwayat_penyakit"),
            "provinsi_id": tm.get("provinsi_id"),
            "provinsi_nama": tm.get("provinsi_nama"),
            "kota_id": tm.get("kota_id"),
            "kota_nama": tm.get("kota_nama"),
            "kecamatan_id": tm.get("kecamatan_id"),
            "kecamatan_nama": tm.get("kecamatan_nama"),
            "kelurahan_id": tm.get("kelurahan_id"),
            "kelurahan_nama": tm.get("kelurahan_nama"),
            "alamat_lengkap": tm.get("alamat_lengkap"),
            "catatan": tm.get("catatan"),
        })
        run("UPDATE trip_members SET member_master_id=%s WHERE id=%s", (mid, trip_member_id))
        return mid


# ─── TRIPS ────────────────────────────────────────────────────────────────────
def get_trips(email=None):
    """Jika email (non-admin), hanya tampilkan trip yang terkait email tersebut."""
    # total_biaya:
    # - Kelompok: jumlah * harga_satuan (total untuk semua)
    # - Personal: jumlah * harga_satuan * jumlah_anggota_yang_kena
    total_biaya_subq = """
        (SELECT COALESCE(SUM(
            CASE ti.tipe_scope
              WHEN 'Kelompok' THEN ti.jumlah * ti.harga_satuan
              WHEN 'Personal' THEN ti.jumlah * ti.harga_satuan * GREATEST(1,
                CASE WHEN ti.personal_semua THEN
                  (SELECT COUNT(*) FROM trip_members tm2 WHERE tm2.trip_id=t.id)
                ELSE
                  (SELECT COUNT(*) FROM trip_item_members tim WHERE tim.trip_item_id=ti.id)
                END)
              ELSE ti.jumlah * ti.harga_satuan
            END
        ),0)
        FROM trip_items ti WHERE ti.trip_id=t.id)
    """
    if email and not is_admin(email):
        return q("""
            SELECT t.*,
                (SELECT COUNT(*) FROM trip_members WHERE trip_id=t.id) AS jml_anggota,
                (SELECT COUNT(*) FROM trip_items   WHERE trip_id=t.id) AS jml_item,
                {} AS total_biaya
            FROM trips t
            WHERE t.id IN (
                SELECT trip_id FROM trip_members WHERE email=%s
            )
            ORDER BY tanggal_berangkat DESC
        """.format(total_biaya_subq), (email,))
    return q("""
        SELECT t.*,
            (SELECT COUNT(*) FROM trip_members WHERE trip_id=t.id) AS jml_anggota,
            (SELECT COUNT(*) FROM trip_items   WHERE trip_id=t.id) AS jml_item,
            {} AS total_biaya
        FROM trips t ORDER BY tanggal_berangkat DESC
    """.format(total_biaya_subq))



def get_trip(tid):
    return q1("SELECT * FROM trips WHERE id=%s", (tid,))


def delete_trip(tid):
    run("DELETE FROM trips WHERE id=%s", (tid,))


def create_trip(d):
    return run("""
        INSERT INTO trips
            (nama_trip,gunung_tujuan,jalur_pendakian,tipe_pendakian,status,
             tanggal_berangkat,tanggal_kembali,jumlah_orang,catatan)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (d["nama_trip"], d["gunung_tujuan"], d.get("jalur_pendakian"),
          d["tipe_pendakian"], d["status"], d["tanggal_berangkat"],
          d.get("tanggal_kembali"), d["jumlah_orang"], d.get("catatan")))


def update_trip(tid, d):
    run("""
        UPDATE trips SET
            nama_trip=%s, gunung_tujuan=%s, jalur_pendakian=%s, tipe_pendakian=%s,
            status=%s, tanggal_berangkat=%s, tanggal_kembali=%s,
            jumlah_orang=%s, catatan=%s
        WHERE id=%s
    """, (d["nama_trip"], d["gunung_tujuan"], d.get("jalur_pendakian"),
          d["tipe_pendakian"], d["status"], d["tanggal_berangkat"],
          d.get("tanggal_kembali"), d["jumlah_orang"], d.get("catatan"), tid))


# ─── MEMBERS (per trip) ───────────────────────────────────────────────────────
def get_members(trip_id):
    rows = q("SELECT * FROM trip_members WHERE trip_id=%s ORDER BY nama_lengkap", (trip_id,))
    result = []
    for row in rows:
        if row.get("provinsi_id") and not row.get("provinsi_nama"):
            row, changed = resolve_wilayah_names(row)
            if changed:
                # patch DB so next load is instant
                run("UPDATE trip_members SET provinsi_nama=%s,kota_nama=%s,kecamatan_nama=%s,kelurahan_nama=%s WHERE id=%s",
                    (row.get("provinsi_nama"),row.get("kota_nama"),row.get("kecamatan_nama"),row.get("kelurahan_nama"),row["id"]))
        result.append(row)
    return result


def get_member(mid):
    row = q1("SELECT * FROM trip_members WHERE id=%s", (mid,))
    if row and row.get("provinsi_id") and not row.get("provinsi_nama"):
        row, changed = resolve_wilayah_names(row)
        if changed:
            run("UPDATE trip_members SET provinsi_nama=%s,kota_nama=%s,kecamatan_nama=%s,kelurahan_nama=%s WHERE id=%s",
                (row.get("provinsi_nama"),row.get("kota_nama"),row.get("kecamatan_nama"),row.get("kelurahan_nama"),row["id"]))
    return row


def delete_member(mid):
    run("DELETE FROM trip_members WHERE id=%s", (mid,))


def _mp(d):
    return (
        d.get("member_master_id"),
        d["nama_lengkap"], d.get("nama_panggilan"), d["nik"],
        d["tempat_lahir"], d["tanggal_lahir"], d["jenis_kelamin"],
        d["no_hp"], d["email"],
        d["kontak_darurat_nama"], d["kontak_darurat_hp"], d["kontak_darurat_hubungan"],
        d.get("riwayat_penyakit"),
        d.get("provinsi_id"), d.get("provinsi_nama"),
        d.get("kota_id"), d.get("kota_nama"),
        d.get("kecamatan_id"), d.get("kecamatan_nama"),
        d.get("kelurahan_id"), d.get("kelurahan_nama"),
        d["alamat_lengkap"], d.get("catatan"),
    )


def create_member(trip_id, d):
    tm_id = run("""
        INSERT INTO trip_members
            (trip_id,member_master_id,nama_lengkap,nama_panggilan,nik,tempat_lahir,tanggal_lahir,jenis_kelamin,
             no_hp,email,kontak_darurat_nama,kontak_darurat_hp,kontak_darurat_hubungan,
             riwayat_penyakit,
             provinsi_id,provinsi_nama,kota_id,kota_nama,
             kecamatan_id,kecamatan_nama,kelurahan_id,kelurahan_nama,
             alamat_lengkap,catatan)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (trip_id,) + _mp(d))
    # Sync ke master & daftarkan email ke users
    if tm_id:
        sync_trip_member_to_master(tm_id)
        if d.get("email"):
            create_user_if_not_exist(d["email"])
    return tm_id


def update_member(mid, d):
    run("""
        UPDATE trip_members SET
            member_master_id=%s,
            nama_lengkap=%s,nama_panggilan=%s,nik=%s,tempat_lahir=%s,tanggal_lahir=%s,
            jenis_kelamin=%s,no_hp=%s,email=%s,
            kontak_darurat_nama=%s,kontak_darurat_hp=%s,kontak_darurat_hubungan=%s,
            riwayat_penyakit=%s,
            provinsi_id=%s,provinsi_nama=%s,kota_id=%s,kota_nama=%s,
            kecamatan_id=%s,kecamatan_nama=%s,kelurahan_id=%s,kelurahan_nama=%s,
            alamat_lengkap=%s,catatan=%s
        WHERE id=%s
    """, _mp(d) + (mid,))


def create_member_from_master(trip_id, master_id):
    """Tambah anggota trip dari data members_master (tidak perlu isi ulang)."""
    mm = get_member_master(master_id)
    if not mm:
        return None
    return create_member(trip_id, {
        "member_master_id": master_id,
        "nama_lengkap": mm["nama_lengkap"],
        "nama_panggilan": mm.get("nama_panggilan") or "",
        "nik": mm.get("nik") or "-",
        "tempat_lahir": mm.get("tempat_lahir") or "-",
        "tanggal_lahir": mm.get("tanggal_lahir") or date(1995, 1, 1),
        "jenis_kelamin": mm.get("jenis_kelamin") or "Laki-laki",
        "no_hp": mm.get("no_hp") or "-",
        "email": mm.get("email") or "",
        "kontak_darurat_nama": mm.get("kontak_darurat_nama") or "-",
        "kontak_darurat_hp": mm.get("kontak_darurat_hp") or "-",
        "kontak_darurat_hubungan": mm.get("kontak_darurat_hubungan") or "Orang Tua",
        "riwayat_penyakit": mm.get("riwayat_penyakit"),
        "provinsi_id": mm.get("provinsi_id"),
        "provinsi_nama": mm.get("provinsi_nama"),
        "kota_id": mm.get("kota_id"),
        "kota_nama": mm.get("kota_nama"),
        "kecamatan_id": mm.get("kecamatan_id"),
        "kecamatan_nama": mm.get("kecamatan_nama"),
        "kelurahan_id": mm.get("kelurahan_id"),
        "kelurahan_nama": mm.get("kelurahan_nama"),
        "alamat_lengkap": mm.get("alamat_lengkap") or "-",
        "catatan": mm.get("catatan"),
    })


# ─── CATEGORIES ───────────────────────────────────────────────────────────────
def get_categories(jenis=None):
    if jenis:
        return q("SELECT * FROM categories WHERE jenis=%s ORDER BY urutan,nama_kategori", (jenis,))
    return q("SELECT * FROM categories ORDER BY urutan,nama_kategori")


def get_category(cid):
    return q1("SELECT * FROM categories WHERE id=%s", (cid,))


def create_category(d):
    return run(
        "INSERT INTO categories (nama_kategori,jenis,icon,deskripsi,urutan) VALUES(%s,%s,%s,%s,%s)",
        (d["nama_kategori"], d["jenis"], d.get("icon", "📦"), d.get("deskripsi"), d.get("urutan", 0)))


def update_category(cid, d):
    run("UPDATE categories SET nama_kategori=%s,jenis=%s,icon=%s,deskripsi=%s,urutan=%s WHERE id=%s",
        (d["nama_kategori"], d["jenis"], d.get("icon", "📦"), d.get("deskripsi"), d.get("urutan", 0), cid))


def delete_category(cid):
    cnt = qv("SELECT COUNT(*) FROM items WHERE category_id=%s", (cid,))
    if cnt:
        raise ValueError("Masih ada {} item master di kategori ini.".format(cnt))
    run("DELETE FROM categories WHERE id=%s", (cid,))


# ─── ITEM MASTER ──────────────────────────────────────────────────────────────
def get_items_master(cat_id=None, search="", tujuan=None):
    sql = """
        SELECT i.*, c.nama_kategori, c.jenis, c.icon
        FROM items i JOIN categories c ON i.category_id=c.id
        WHERE 1=1
    """
    p = []
    if cat_id:
        sql += " AND i.category_id=%s"; p.append(cat_id)
    if search:
        sql += " AND i.nama_item LIKE %s"; p.append("%{}%".format(search))
    if tujuan:
        sql += " AND i.tujuan=%s"; p.append(tujuan)
    sql += " ORDER BY c.urutan, i.tujuan, i.label, i.nama_item"
    return q(sql, p)


def get_item_master(iid):
    return q1("""
        SELECT i.*, c.nama_kategori, c.jenis, c.icon
        FROM items i JOIN categories c ON i.category_id=c.id
        WHERE i.id=%s
    """, (iid,))


def create_item_master(d):
    return run(
        "INSERT INTO items (nama_item,category_id,satuan,berat_gram,tujuan,label,deskripsi) VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (d["nama_item"], d["category_id"], d.get("satuan", "pcs"), d.get("berat_gram", 0),
         d.get("tujuan", "Personal"), d.get("label", "Wajib"), d.get("deskripsi")))


def update_item_master(iid, d):
    run("UPDATE items SET nama_item=%s,category_id=%s,satuan=%s,berat_gram=%s,tujuan=%s,label=%s,deskripsi=%s WHERE id=%s",
        (d["nama_item"], d["category_id"], d.get("satuan", "pcs"), d.get("berat_gram", 0),
         d.get("tujuan", "Personal"), d.get("label", "Wajib"), d.get("deskripsi"), iid))


def delete_item_master(iid):
    run("DELETE FROM items WHERE id=%s", (iid,))


# ─── TRIP ITEMS ───────────────────────────────────────────────────────────────
def _enrich(rows, trip_id, jumlah_orang):
    if not rows:
        return rows
    members_all = get_members(trip_id)
    # Batch: 1 query untuk semua assigned members
    item_ids = [row["id"] for row in rows]
    placeholders = ",".join(["%s"] * len(item_ids))
    all_assignments = q("""
        SELECT tim.trip_item_id, tm.id, tm.nama_lengkap, tm.nama_panggilan
        FROM trip_item_members tim
        JOIN trip_members tm ON tim.member_id=tm.id
        WHERE tim.trip_item_id IN ({})
    """.format(placeholders), item_ids)
    assign_map = {}
    for a in all_assignments:
        assign_map.setdefault(a["trip_item_id"], []).append({
            "id": a["id"], "nama_lengkap": a["nama_lengkap"],
            "nama_panggilan": a["nama_panggilan"],
        })
    for row in rows:
        sub = float(row.get("jumlah", 1)) * float(row.get("harga_satuan", 0))
        row["subtotal"] = sub
        if row["tipe_scope"] == "Personal":
            if row.get("personal_semua"):
                row["assigned_members"] = members_all
            else:
                row["assigned_members"] = assign_map.get(row["id"], [])
        else:
            row["assigned_members"] = members_all
        n = len(row["assigned_members"]) if row["assigned_members"] else 1
        row["n_bayar"] = n
        row["per_orang_rp"] = sub if row["tipe_scope"] == "Personal" else (sub / n if n else 0)
        berat_gram_val = float(row.get("berat_gram") or 0)
        berat_satuan_val = row.get("berat_satuan") or "gram"
        row["berat_gram_converted"] = to_gram(berat_gram_val, berat_satuan_val)
    return rows


def get_trip_items(trip_id, jumlah_orang=1):
    rows = q("""
        SELECT ti.*, c.nama_kategori, c.jenis, c.icon,
               tm.nama_lengkap AS penanggung_nama,
               tm.nama_panggilan AS penanggung_panggilan
        FROM trip_items ti
        LEFT JOIN categories c  ON ti.category_id=c.id
        LEFT JOIN trip_members tm ON ti.ditanggung_member_id=tm.id
        WHERE ti.trip_id=%s
        ORDER BY c.urutan, c.nama_kategori, ti.nama_item
    """, (trip_id,))
    return _enrich(rows, trip_id, jumlah_orang)


def get_trip_item(iid):
    """Get single trip item — enriched with subtotal, per_orang_rp, assigned_members."""
    row = q1("""
        SELECT ti.*, c.nama_kategori, c.jenis, c.icon,
               tm.nama_lengkap AS penanggung_nama,
               tm.nama_panggilan AS penanggung_panggilan
        FROM trip_items ti
        LEFT JOIN categories c ON ti.category_id=c.id
        LEFT JOIN trip_members tm ON ti.ditanggung_member_id=tm.id
        WHERE ti.id=%s
    """, (iid,))
    if not row:
        return None
    row["assigned_member_ids"] = [
        r["member_id"] for r in
        q("SELECT member_id FROM trip_item_members WHERE trip_item_id=%s", (iid,))
    ]
    # Enrich manually
    sub = float(row.get("harga_satuan") or 0) * float(row.get("jumlah") or 1)
    row["subtotal"] = sub
    # assigned_members list
    assigned_members = []
    if row["assigned_member_ids"]:
        for mid in row["assigned_member_ids"]:
            m = q1("SELECT id,nama_lengkap,nama_panggilan FROM trip_members WHERE id=%s", (mid,))
            if m: assigned_members.append(m)
    row["assigned_members"] = assigned_members
    n = len(assigned_members) if assigned_members else 1
    row["n_bayar"] = n
    if row["tipe_scope"] == "Personal":
        row["per_orang_rp"] = sub
    else:
        row["per_orang_rp"] = sub / n if n else 0
    return row


def _calc_tgl_selesai(d):
    """
    Hitung tanggal selesai sewa secara inklusif.
    Mulai 12, durasi 5 → selesai 16 (12+5-1=16, artinya hari ke-12,13,14,15,16 = 5 hari)
    """
    if d.get("jenis_pengadaan") == "Sewa" and d.get("tanggal_sewa_mulai") and d.get("durasi_sewa_hari"):
        return d["tanggal_sewa_mulai"] + timedelta(days=int(d["durasi_sewa_hari"]) - 1)
    return None


def create_trip_item(trip_id, d, assigned_ids):
    tgl_selesai = _calc_tgl_selesai(d)
    item_id = run("""
        INSERT INTO trip_items
            (trip_id, nama_item, category_id, jenis_pengadaan,
             tanggal_sewa_mulai, durasi_sewa_hari, tanggal_sewa_selesai,
             jumlah, satuan, berat_gram, berat_satuan, harga_satuan,
             tipe_scope, personal_semua, ditanggung_member_id, catatan)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        trip_id, d["nama_item"], d.get("category_id"), d.get("jenis_pengadaan", "Beli"),
        d.get("tanggal_sewa_mulai"), d.get("durasi_sewa_hari", 1), tgl_selesai,
        d.get("jumlah", 1), d.get("satuan", "pcs"),
        d.get("berat_gram", 0), d.get("berat_satuan", "gram"),
        d.get("harga_satuan", 0),
        d["tipe_scope"], bool(d.get("personal_semua", False)),
        d.get("ditanggung_member_id"), d.get("catatan"),
    ))

    if d["tipe_scope"] == "Personal" and not d.get("personal_semua") and assigned_ids:
        for mid in assigned_ids:
            run("INSERT INTO trip_item_members (trip_item_id,member_id) VALUES(%s,%s)",
                (item_id, mid))

    _sync_biaya_to_checklist(trip_id, item_id, d, assigned_ids)
    return item_id


def update_trip_item(iid, trip_id, d, assigned_ids):
    tgl_selesai = _calc_tgl_selesai(d)
    run("""
        UPDATE trip_items SET
            nama_item=%s, category_id=%s, jenis_pengadaan=%s,
            tanggal_sewa_mulai=%s, durasi_sewa_hari=%s, tanggal_sewa_selesai=%s,
            jumlah=%s, satuan=%s, berat_gram=%s, berat_satuan=%s, harga_satuan=%s,
            tipe_scope=%s, personal_semua=%s, ditanggung_member_id=%s, catatan=%s
        WHERE id=%s
    """, (
        d["nama_item"], d.get("category_id"), d.get("jenis_pengadaan", "Beli"),
        d.get("tanggal_sewa_mulai"), d.get("durasi_sewa_hari", 1), tgl_selesai,
        d.get("jumlah", 1), d.get("satuan", "pcs"),
        d.get("berat_gram", 0), d.get("berat_satuan", "gram"),
        d.get("harga_satuan", 0),
        d["tipe_scope"], bool(d.get("personal_semua", False)),
        d.get("ditanggung_member_id"), d.get("catatan"), iid,
    ))

    run("DELETE FROM trip_item_members WHERE trip_item_id=%s", (iid,))
    if d["tipe_scope"] == "Personal" and not d.get("personal_semua") and assigned_ids:
        for mid in assigned_ids:
            run("INSERT INTO trip_item_members (trip_item_id,member_id) VALUES(%s,%s)",
                (iid, mid))

    run("UPDATE trip_checklist_group    SET nama_item=%s WHERE trip_item_id=%s", (d["nama_item"], iid))
    run("UPDATE trip_checklist_personal SET nama_item=%s WHERE trip_item_id=%s", (d["nama_item"], iid))


def delete_trip_item(iid):
    run("DELETE FROM trip_checklist_group    WHERE trip_item_id=%s", (iid,))
    run("DELETE FROM trip_checklist_personal WHERE trip_item_id=%s", (iid,))
    run("DELETE FROM trip_items WHERE id=%s", (iid,))


def _sync_biaya_to_checklist(trip_id, trip_item_id, d, assigned_ids):
    nama   = d.get("nama_item", "")
    cat_id = d.get("category_id")

    if d["tipe_scope"] == "Kelompok":
        exists = qv("SELECT COUNT(*) FROM trip_checklist_group WHERE trip_item_id=%s", (trip_item_id,))
        if not exists:
            run("""INSERT INTO trip_checklist_group
                    (trip_id,trip_item_id,nama_item,category_id,label,sumber,sudah_siap)
                    VALUES(%s,%s,%s,%s,'Wajib','Biaya',FALSE)""",
                (trip_id, trip_item_id, nama, cat_id))
    else:
        members_all = get_members(trip_id)
        targets = [m["id"] for m in members_all] if d.get("personal_semua") else assigned_ids
        for mid in targets:
            exists = qv(
                "SELECT COUNT(*) FROM trip_checklist_personal WHERE trip_item_id=%s AND member_id=%s",
                (trip_item_id, mid))
            if not exists:
                run("""INSERT INTO trip_checklist_personal
                        (trip_id,member_id,trip_item_id,nama_item,category_id,label,sumber,sudah_siap)
                        VALUES(%s,%s,%s,%s,%s,'Wajib','Biaya',FALSE)""",
                    (trip_id, mid, trip_item_id, nama, cat_id))


# ─── BULK: ITEM MASTER → CHECKLIST ────────────────────────────────────────────
def sync_master_to_checklist(trip_id, item_ids):
    return sync_master_to_checklist_with_qty(trip_id, {iid: 1 for iid in item_ids})


def sync_master_to_checklist_with_qty(trip_id, qty_map):
    members = get_members(trip_id)
    added = 0
    for iid, qty in qty_map.items():
        item = get_item_master(iid)
        if not item:
            continue
        qty = max(1, int(qty))
        for n in range(1, qty + 1):
            nama = "{} #{}".format(item["nama_item"], n) if qty > 1 else item["nama_item"]
            if item["tujuan"] == "Kelompok":
                exists = qv("SELECT COUNT(*) FROM trip_checklist_group WHERE trip_id=%s AND item_id=%s AND nama_item=%s",
                            (trip_id, iid, nama))
                if not exists:
                    run("""INSERT INTO trip_checklist_group
                            (trip_id,item_id,nama_item,category_id,label,sumber,sudah_siap)
                            VALUES(%s,%s,%s,%s,%s,'Master',FALSE)""",
                        (trip_id, iid, nama, item["category_id"], item["label"]))
                    added += 1
            else:
                for m in members:
                    exists = qv("SELECT COUNT(*) FROM trip_checklist_personal WHERE trip_id=%s AND member_id=%s AND item_id=%s AND nama_item=%s",
                                (trip_id, m["id"], iid, nama))
                    if not exists:
                        run("""INSERT INTO trip_checklist_personal
                                (trip_id,member_id,item_id,nama_item,category_id,label,sumber,sudah_siap)
                                VALUES(%s,%s,%s,%s,%s,%s,'Master',FALSE)""",
                            (trip_id, m["id"], iid, nama, item["category_id"], item["label"]))
                        added += 1
    return added


def sync_master_to_personal_checklist(trip_id, member_id, qty_map):
    """Assign item master ke checklist personal satu anggota tertentu."""
    added = 0
    for iid, qty in qty_map.items():
        item = get_item_master(iid)
        if not item: continue
        qty = max(1, int(qty))
        for n in range(1, qty + 1):
            nama = "{} #{}".format(item["nama_item"], n) if qty > 1 else item["nama_item"]
            exists = qv("SELECT COUNT(*) FROM trip_checklist_personal WHERE trip_id=%s AND member_id=%s AND item_id=%s AND nama_item=%s",
                        (trip_id, member_id, iid, nama))
            if not exists:
                run("""INSERT INTO trip_checklist_personal
                        (trip_id,member_id,item_id,nama_item,category_id,label,sumber,sudah_siap)
                        VALUES(%s,%s,%s,%s,%s,%s,'Master',FALSE)""",
                    (trip_id, member_id, iid, nama, item["category_id"], item["label"]))
                added += 1
    return added


# ─── CHECKLIST GROUP ──────────────────────────────────────────────────────────
def get_checklist_group(trip_id, sort_by="urutan", f_label=None, f_sumber=None, search=""):
    sql = """
        SELECT cg.*, c.nama_kategori, c.icon,
               tm.nama_lengkap AS dibawa_nama, tm.nama_panggilan AS dibawa_panggilan
        FROM trip_checklist_group cg
        LEFT JOIN categories  c  ON cg.category_id=c.id
        LEFT JOIN trip_members tm ON cg.dibawa_oleh=tm.id
        WHERE cg.trip_id=%s
    """
    p = [trip_id]
    if f_label:  sql += " AND cg.label=%s";       p.append(f_label)
    if f_sumber: sql += " AND cg.sumber=%s";      p.append(f_sumber)
    if search:   sql += " AND cg.nama_item LIKE %s"; p.append("%{}%".format(search))
    order_map = {"nama": "cg.sumber, cg.nama_item", "sumber": "cg.sumber, cg.nama_item", "label": "cg.label, cg.nama_item"}
    sql += " ORDER BY " + order_map.get(sort_by, "cg.sumber, cg.label, cg.urutan, cg.nama_item")
    return q(sql, p)


def add_checklist_group_manual(trip_id, d):
    return run("""INSERT INTO trip_checklist_group
                    (trip_id,nama_item,category_id,label,catatan,sumber,sudah_siap)
                    VALUES(%s,%s,%s,%s,%s,'Manual',FALSE)""",
               (trip_id, d["nama_item"], d.get("category_id"), d.get("label", "Wajib"), d.get("catatan")))


def update_checklist_group(clid, d):
    run("""UPDATE trip_checklist_group SET
            nama_item=%s, category_id=%s, label=%s, catatan=%s, sudah_siap=%s, dibawa_oleh=%s
           WHERE id=%s""",
        (d["nama_item"], d.get("category_id"), d.get("label", "Wajib"),
         d.get("catatan"), bool(d.get("sudah_siap", False)), d.get("dibawa_oleh"), clid))


def toggle_checklist_group(clid, val):
    run("UPDATE trip_checklist_group SET sudah_siap=%s WHERE id=%s", (bool(val), clid))


def delete_checklist_group(clid):
    run("DELETE FROM trip_checklist_group WHERE id=%s", (clid,))


def set_dibawa_oleh(clid, member_id):
    run("UPDATE trip_checklist_group SET dibawa_oleh=%s WHERE id=%s", (member_id, clid))


# ─── CHECKLIST PERSONAL ───────────────────────────────────────────────────────
def get_checklist_personal(trip_id, member_id, sort_by="urutan", f_label=None, f_sumber=None, search=""):
    sql = """
        SELECT cp.*, c.nama_kategori, c.icon
        FROM trip_checklist_personal cp
        LEFT JOIN categories c ON cp.category_id=c.id
        WHERE cp.trip_id=%s AND cp.member_id=%s
    """
    p = [trip_id, member_id]
    if f_label:  sql += " AND cp.label=%s";       p.append(f_label)
    if f_sumber: sql += " AND cp.sumber=%s";      p.append(f_sumber)
    if search:   sql += " AND cp.nama_item LIKE %s"; p.append("%{}%".format(search))
    order_map = {"nama": "cp.sumber, cp.nama_item", "sumber": "cp.sumber, cp.nama_item", "label": "cp.label, cp.nama_item"}
    sql += " ORDER BY " + order_map.get(sort_by, "cp.sumber, cp.label, cp.urutan, cp.nama_item")
    return q(sql, p)


def add_checklist_personal_manual(trip_id, member_id, d):
    return run("""INSERT INTO trip_checklist_personal
                    (trip_id,member_id,nama_item,category_id,label,catatan,sumber,sudah_siap)
                    VALUES(%s,%s,%s,%s,%s,%s,'Manual',FALSE)""",
               (trip_id, member_id, d["nama_item"], d.get("category_id"),
                d.get("label", "Wajib"), d.get("catatan")))


def update_checklist_personal(clid, d):
    run("""UPDATE trip_checklist_personal SET
            nama_item=%s, category_id=%s, label=%s, catatan=%s, sudah_siap=%s
           WHERE id=%s""",
        (d["nama_item"], d.get("category_id"), d.get("label", "Wajib"),
         d.get("catatan"), bool(d.get("sudah_siap", False)), clid))


def toggle_checklist_personal(clid, val):
    run("UPDATE trip_checklist_personal SET sudah_siap=%s WHERE id=%s", (bool(val), clid))


def delete_checklist_personal(clid):
    run("DELETE FROM trip_checklist_personal WHERE id=%s", (clid,))


# ─── KALKULASI BIAYA ──────────────────────────────────────────────────────────
def calc_trip_summary(trip_id, jumlah_orang):
    """
    Kalkulasi biaya per anggota — logika benar:

    tagihan[mid]     = total biaya yg seharusnya dibayar mid (kelompok+personal)
    menanggung[mid]  = total yang SUDAH mid keluarkan dari kantong sendiri
                       (item dengan ditanggung_member_id = mid)
    net_tagihan[mid] = tagihan[mid] - menanggung[mid]
      → positif : mid masih kurang bayar ke kas (sisa_bayar = net - paid_to_kas)
      → negatif : mid sudah lebih bayar, uangnya belum dikembalikan (piutang)

    PENTING: menanggung MENGURANGI tagihan, bukan menambah.
    Contoh: tagihan 500k, menanggung 200k → net 300k (masih harus bayar 300k ke kas)
    """
    items   = get_trip_items(trip_id, jumlah_orang)
    members = get_members(trip_id)
    mids    = [m["id"] for m in members]

    tagihan    = {mid: 0.0 for mid in mids}
    menanggung = {mid: 0.0 for mid in mids}
    total_kelompok = 0.0
    total_personal = 0.0

    for item in items:
        sub      = float(item["subtotal"])
        assigned = [m["id"] for m in item["assigned_members"]] if item["assigned_members"] else mids
        n_asgn   = max(len(assigned), 1)

        if item["tipe_scope"] == "Kelompok":
            total_kelompok += sub
            # Setiap member kelompok menanggung porsi rata
            per_o = sub / max(jumlah_orang, 1)
            for mid in mids:
                tagihan[mid] += per_o
        else:
            total_personal += sub
            # Personal: SETIAP anggota yg dipilih menanggung PENUH subtotal
            # Tidak dibagi — masing-masing bayar sendiri sebesar sub
            for mid in assigned:
                if mid in tagihan:
                    tagihan[mid] += sub  # full subtotal, bukan sub/n_asgn

        # Jika item ini "ditanggung" oleh seseorang:
        # artinya dia sudah keluarkan uang dari kantong sendiri.
        # Untuk kelompok: dia bayar sub (total untuk semua)
        # Untuk personal: dia bayar sub × n_asgn (karena tiap orang kena sub penuh)
        pid = item.get("ditanggung_member_id")
        if pid and pid in menanggung:
            if item["tipe_scope"] == "Personal":
                # Penanggung membayar sub untuk setiap orang yang ditugaskan
                menanggung[pid] += sub * n_asgn
            else:
                menanggung[pid] += sub

    # net = tagihan - menanggung
    # positif → masih harus bayar net ke kas
    # negatif → kelebihan (piutang dari kas/grup)
    net_tagihan = {mid: round(tagihan[mid] - menanggung[mid], 2) for mid in mids}

    return {
        "total_kelompok":     total_kelompok,
        "total_personal":     total_personal,
        "grand_total":        total_kelompok + total_personal,
        "per_orang_kelompok": total_kelompok / max(jumlah_orang, 1),
        "tagihan":            tagihan,
        "menanggung":         menanggung,
        "net_tagihan":        net_tagihan,
        "items":              items,
        "members":            members,
    }


# ─── KALKULASI BERAT ──────────────────────────────────────────────────────────
def calc_berat(trip_id, jumlah_orang):
    """
    Kalkulasi estimasi berat per anggota.
    Sumber berat:
    1. Trip items (input biaya) yang punya berat
    2. Item master dari checklist (trip_checklist_group & trip_checklist_personal)
       yang item master-nya punya berat_gram

    Untuk item Kelompok di Sumber 1:
    - Jika checklist-nya sudah ada dibawa_oleh → berat full ke pembawa itu saja
    - Jika belum ditentukan → dibagi rata ke semua anggota
    """
    trip_items_raw = get_trip_items(trip_id, jumlah_orang)
    members = get_members(trip_id)
    mids    = [m["id"] for m in members]
    n_member = max(len(mids), 1)

    berat_per_orang = {mid: 0.0 for mid in mids}
    berat_kelompok  = 0.0
    berat_total     = 0.0
    all_items_display = []  # for display

    # Pre-load peta trip_item_id → dibawa_oleh dari checklist_group
    # Dipakai di Sumber 1 agar item kelompok yg sudah ditentukan pembawanya
    # tidak dibagi rata, melainkan full ke pembawa tersebut.
    cl_group_all = get_checklist_group(trip_id)
    dibawa_oleh_map = {}  # trip_item_id → member_id pembawa
    for cl in cl_group_all:
        if cl.get("trip_item_id") and cl.get("dibawa_oleh"):
            dibawa_oleh_map[cl["trip_item_id"]] = cl["dibawa_oleh"]

    # ── Sumber 1: Trip items (input biaya) ──────────────────────────────────
    for item in trip_items_raw:
        bg_per_unit = float(item.get("berat_gram_converted") or
                            to_gram(item.get("berat_gram") or 0,
                                    item.get("berat_satuan") or "gram"))
        bg = bg_per_unit * float(item.get("jumlah", 1))
        if bg == 0:
            continue

        if item["tipe_scope"] == "Kelompok":
            berat_kelompok += bg
            berat_total    += bg
            pembawa = dibawa_oleh_map.get(item["id"])
            if pembawa and pembawa in mids:
                # Sudah ditentukan pembawanya → berat full ke dia saja
                berat_per_orang[pembawa] += bg
                assigned   = [pembawa]
                per_o      = bg
                asgn_members = [m for m in members if m["id"] == pembawa]
            else:
                # Belum ditentukan → dibagi rata
                assigned     = mids
                n            = max(len(assigned), 1)
                per_o        = bg / n
                asgn_members = members
                for mid in assigned:
                    if mid in berat_per_orang:
                        berat_per_orang[mid] += per_o
        else:
            berat_total += bg
            assigned = [m["id"] for m in item["assigned_members"]] if item["assigned_members"] else mids
            n        = max(len(assigned), 1)
            per_o    = bg / n
            asgn_members = item.get("assigned_members", members)
            for mid in assigned:
                if mid in berat_per_orang:
                    berat_per_orang[mid] += per_o

        all_items_display.append({
            **item,
            "sumber_berat": "Biaya",
            "berat_total_item": bg,
            "berat_per_orang_item": per_o,
            "assigned_ids": assigned,
            "assigned_members": asgn_members,
        })

    # ── Sumber 2: Checklist kelompok (dari item master) ─────────────────────
    # Gunakan cl_group_all yg sudah di-load, skip item yg berasal dari trip_items
    # (trip_item_id != NULL) karena sudah dihitung di Sumber 1.
    for cl in cl_group_all:
        if cl.get("trip_item_id"):
            continue  # sudah diproses di Sumber 1, skip agar tidak double-count
        if not cl.get("item_id"):
            continue
        master = get_item_master(cl["item_id"])
        if not master or not master.get("berat_gram"):
            continue
        bg = float(master["berat_gram"])
        if bg == 0:
            continue
        # Jika ada "dibawa_oleh", hanya anggota itu yang nanggung
        if cl.get("dibawa_oleh") and cl["dibawa_oleh"] in mids:
            pembawa = cl["dibawa_oleh"]
            berat_kelompok += bg
            berat_total    += bg
            berat_per_orang[pembawa] += bg
            all_items_display.append({
                "nama_item": cl["nama_item"],
                "tipe_scope": "Kelompok",
                "jumlah": 1, "satuan": "unit",
                "nama_kategori": cl.get("nama_kategori","?"),
                "icon": cl.get("icon","📦"),
                "sumber_berat": "Master (Checklist)",
                "berat_total_item": bg,
                "berat_per_orang_item": bg,
                "assigned_ids": [pembawa],
                "assigned_members": [m for m in members if m["id"]==pembawa],
            })
        else:
            # Dibagi rata
            per_o = bg / n_member
            berat_kelompok += bg
            berat_total    += bg
            for mid in mids:
                berat_per_orang[mid] += per_o
            all_items_display.append({
                "nama_item": cl["nama_item"],
                "tipe_scope": "Kelompok",
                "jumlah": 1, "satuan": "unit",
                "nama_kategori": cl.get("nama_kategori","?"),
                "icon": cl.get("icon","📦"),
                "sumber_berat": "Master (Checklist)",
                "berat_total_item": bg,
                "berat_per_orang_item": per_o,
                "assigned_ids": mids,
                "assigned_members": members,
            })

    # ── Sumber 3: Checklist personal (dari item master) ─────────────────────
    for m in members:
        cl_personal = get_checklist_personal(trip_id, m["id"])
        for cl in cl_personal:
            if not cl.get("item_id"):
                continue
            master = get_item_master(cl["item_id"])
            if not master or not master.get("berat_gram"):
                continue
            bg = float(master["berat_gram"])
            if bg == 0:
                continue
            berat_total += bg
            berat_per_orang[m["id"]] = berat_per_orang.get(m["id"], 0) + bg
            all_items_display.append({
                "nama_item": cl["nama_item"],
                "tipe_scope": "Personal",
                "jumlah": 1, "satuan": "unit",
                "nama_kategori": cl.get("nama_kategori","?"),
                "icon": cl.get("icon","📦"),
                "sumber_berat": "Master (Checklist)",
                "berat_total_item": bg,
                "berat_per_orang_item": bg,
                "assigned_ids": [m["id"]],
                "assigned_members": [m],
            })

    return {
        "berat_per_orang": berat_per_orang,
        "berat_kelompok":  berat_kelompok,
        "berat_total":     berat_total,
        "members":         members,
        "items":           all_items_display,
    }

def assign_pembawa(checklist_group_id, member_id):
    set_dibawa_oleh(checklist_group_id, member_id)


# ─── PAYMENTS ─────────────────────────────────────────────────────────────────
def get_payments(trip_id):
    return q("""
        SELECT tp.*, tm.nama_lengkap, tm.nama_panggilan
        FROM trip_payments tp
        JOIN trip_members tm ON tp.member_id=tm.id
        WHERE tp.trip_id=%s ORDER BY tp.created_at DESC
    """, (trip_id,))


def add_payment(trip_id, d):
    return run("""
        INSERT INTO trip_payments
            (trip_id,member_id,jumlah_dibayar,tanggal_bayar,metode_bayar,keterangan)
        VALUES(%s,%s,%s,%s,%s,%s)
    """, (trip_id, d["member_id"], d["jumlah_dibayar"],
          d.get("tanggal_bayar"), d.get("metode_bayar", "Tunai"), d.get("keterangan")))


def delete_payment(pid):
    run("DELETE FROM trip_payments WHERE id=%s", (pid,))


def get_paid(trip_id, member_id):
    return float(qv(
        "SELECT COALESCE(SUM(jumlah_dibayar),0) FROM trip_payments WHERE trip_id=%s AND member_id=%s",
        (trip_id, member_id)))


def get_paid_all(trip_id):
    """1 query untuk semua member."""
    rows = q(
        "SELECT member_id, COALESCE(SUM(jumlah_dibayar),0) AS total "
        "FROM trip_payments WHERE trip_id=%s GROUP BY member_id", (trip_id,))
    return {r["member_id"]: float(r["total"]) for r in rows}


# ─── NOTES ────────────────────────────────────────────────────────────────────
def get_notes(trip_id):
    return q("SELECT * FROM trip_notes WHERE trip_id=%s ORDER BY created_at DESC", (trip_id,))


def add_note(trip_id, d):
    return run("INSERT INTO trip_notes (trip_id,judul,isi,tipe) VALUES(%s,%s,%s,%s)",
               (trip_id, d.get("judul"), d["isi"], d.get("tipe", "Umum")))


def update_note(nid, d):
    run("UPDATE trip_notes SET judul=%s,isi=%s,tipe=%s WHERE id=%s",
        (d.get("judul"), d["isi"], d.get("tipe", "Umum"), nid))


def delete_note(nid):
    run("DELETE FROM trip_notes WHERE id=%s", (nid,))


# ─── EXERCISES ────────────────────────────────────────────────────────────────
def get_exercise_categories():
    return q("SELECT * FROM exercise_categories ORDER BY urutan, nama")


def get_exercises(cat_id=None, level=None, search=""):
    sql = """
        SELECT e.*, ec.nama AS nama_kategori, ec.icon AS cat_icon
        FROM exercises e
        JOIN exercise_categories ec ON e.category_id=ec.id
        WHERE 1=1
    """
    p = []
    if cat_id:
        sql += " AND e.category_id=%s"; p.append(cat_id)
    if level:
        sql += " AND e.level=%s"; p.append(level)
    if search:
        sql += " AND (e.nama_latihan LIKE %s OR e.fokus LIKE %s OR e.otot_utama LIKE %s)"
        p.extend(["%{}%".format(search)] * 3)
    sql += " ORDER BY ec.urutan, e.level, e.nama_latihan"
    return q(sql, p)


def get_exercise(eid):
    return q1("""
        SELECT e.*, ec.nama AS nama_kategori, ec.icon AS cat_icon
        FROM exercises e JOIN exercise_categories ec ON e.category_id=ec.id
        WHERE e.id=%s
    """, (eid,))


def create_exercise(d):
    return run("""
        INSERT INTO exercises
            (nama_latihan,category_id,fokus,level,durasi_menit,kalori_estimasi,
             otot_utama,peralatan,instruksi,tips,gambar_url)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (d["nama_latihan"], d["category_id"], d.get("fokus"), d.get("level","Pemula"),
          d.get("durasi_menit",30), d.get("kalori_estimasi",0),
          d.get("otot_utama"), d.get("peralatan","Tanpa Alat"),
          d.get("instruksi"), d.get("tips"), d.get("gambar_url")))


def update_exercise(eid, d):
    run("""
        UPDATE exercises SET
            nama_latihan=%s, category_id=%s, fokus=%s, level=%s,
            durasi_menit=%s, kalori_estimasi=%s, otot_utama=%s,
            peralatan=%s, instruksi=%s, tips=%s, gambar_url=%s
        WHERE id=%s
    """, (d["nama_latihan"], d["category_id"], d.get("fokus"), d.get("level","Pemula"),
          d.get("durasi_menit",30), d.get("kalori_estimasi",0),
          d.get("otot_utama"), d.get("peralatan","Tanpa Alat"),
          d.get("instruksi"), d.get("tips"), d.get("gambar_url"), eid))


def delete_exercise(eid):
    run("DELETE FROM exercises WHERE id=%s", (eid,))


# ─── WILAYAH API ──────────────────────────────────────────────────────────────
_API = "https://api-regional-indonesia.vercel.app/api"


def _get(url):
    try:
        import requests
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            body = r.json()
            if isinstance(body, dict):
                data = body.get("data")
                if isinstance(data, list):
                    return data
                return []
            if isinstance(body, list):
                return body
    except Exception:
        pass
    return []


def resolve_wilayah_names(d):
    """
    Jika nama wilayah kosong tapi ID ada, coba resolve dari API.
    d is dict with provinsi_id, kota_id, kecamatan_id, kelurahan_id.
    Returns updated dict with filled *_nama fields.
    """
    changed = False
    try:
        if d.get("provinsi_id") and not d.get("provinsi_nama"):
            provs = api_provinces()
            for p in provs:
                if str(p["id"]) == str(d["provinsi_id"]):
                    d["provinsi_nama"] = p["name"]; changed = True; break

        if d.get("kota_id") and not d.get("kota_nama") and d.get("provinsi_id"):
            cities = api_cities(d["provinsi_id"])
            for c in cities:
                if str(c["id"]) == str(d["kota_id"]):
                    d["kota_nama"] = c["name"]; changed = True; break

        if d.get("kecamatan_id") and not d.get("kecamatan_nama") and d.get("kota_id"):
            dists = api_districts(d["kota_id"])
            for c in dists:
                if str(c["id"]) == str(d["kecamatan_id"]):
                    d["kecamatan_nama"] = c["name"]; changed = True; break

        if d.get("kelurahan_id") and not d.get("kelurahan_nama") and d.get("kecamatan_id"):
            vils = api_villages(d["kecamatan_id"])
            for c in vils:
                if str(c["id"]) == str(d["kelurahan_id"]):
                    d["kelurahan_nama"] = c["name"]; changed = True; break
    except Exception:
        pass
    return d, changed


def api_provinces():
    return _get("{}/provinces?sort=name".format(_API))


def api_cities(province_id):
    return _get("{}/cities/{}?sort=name".format(_API, province_id))


def api_districts(city_id):
    return _get("{}/districts/{}?sort=name".format(_API, city_id))


def api_villages(district_id):
    return _get("{}/villages/{}?sort=name".format(_API, district_id))


# ─── TIMELINE ─────────────────────────────────────────────────────────────────
TIMELINE_ICONS = {
    "Perjalanan": "🚌", "Pendakian": "🥾", "Istirahat": "⛺",
    "Makan": "🍽️", "Dokumentasi": "📷", "Darurat": "🚨", "Lainnya": "📍",
}
TIMELINE_COLORS = {
    "Perjalanan": "#3b82f6", "Pendakian": "#22c55e", "Istirahat": "#f59e0b",
    "Makan": "#ec4899", "Dokumentasi": "#a855f7", "Darurat": "#ef4444", "Lainnya": "#6b7280",
}

def get_timeline(trip_id):
    return q("""
        SELECT * FROM trip_timeline
        WHERE trip_id=%s
        ORDER BY hari_ke, urutan, jam_mulai
    """, (trip_id,))


def get_timeline_by_day(trip_id):
    rows = get_timeline(trip_id)
    days = {}
    for r in rows:
        d = r["hari_ke"]
        days.setdefault(d, []).append(r)
    return days


def add_timeline(trip_id, d):
    return run("""
        INSERT INTO trip_timeline
            (trip_id, hari_ke, tanggal, jam_mulai, jam_mulai_kira,
             jam_selesai, jam_selesai_kira,
             judul, deskripsi, lokasi, kategori, icon, urutan, scenario_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        trip_id,
        d.get("hari_ke", 1),
        d.get("tanggal"),
        d.get("jam_mulai"),
        d.get("jam_mulai_kira"),
        d.get("jam_selesai"),
        d.get("jam_selesai_kira"),
        d["judul"],
        d.get("deskripsi"),
        d.get("lokasi"),
        d.get("kategori", "Pendakian"),
        TIMELINE_ICONS.get(d.get("kategori","Lainnya"), "📍"),
        d.get("urutan", 0),
        d.get("scenario_id"),
    ))


def update_timeline(tid, d):
    run("""
        UPDATE trip_timeline SET
            hari_ke=%s, tanggal=%s,
            jam_mulai=%s, jam_mulai_kira=%s,
            jam_selesai=%s, jam_selesai_kira=%s,
            judul=%s, deskripsi=%s, lokasi=%s,
            kategori=%s, icon=%s, urutan=%s,
            scenario_id=%s
        WHERE id=%s
    """, (
        d.get("hari_ke", 1),
        d.get("tanggal"),
        d.get("jam_mulai"),
        d.get("jam_mulai_kira"),
        d.get("jam_selesai"),
        d.get("jam_selesai_kira"),
        d["judul"],
        d.get("deskripsi"),
        d.get("lokasi"),
        d.get("kategori", "Pendakian"),
        TIMELINE_ICONS.get(d.get("kategori","Lainnya"), "📍"),
        d.get("urutan", 0),
        d.get("scenario_id"),
        tid,
    ))


def delete_timeline(tid):
    run("DELETE FROM trip_timeline WHERE id=%s", (tid,))


# ─── BANK INFO ────────────────────────────────────────────────────────────────
def get_bank_info():
    return q("SELECT * FROM bank_info ORDER BY urutan, nama_bank")

def add_bank_info(d):
    return run("""
        INSERT INTO bank_info (nama_bank, no_rekening, atas_nama, catatan, icon, urutan)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (d["nama_bank"], d["no_rekening"], d["atas_nama"],
          d.get("catatan"), d.get("icon","🏦"), d.get("urutan",0)))

def update_bank_info(bid, d):
    run("""UPDATE bank_info SET nama_bank=%s,no_rekening=%s,atas_nama=%s,
           catatan=%s,icon=%s,urutan=%s WHERE id=%s""",
        (d["nama_bank"], d["no_rekening"], d["atas_nama"],
         d.get("catatan"), d.get("icon","🏦"), d.get("urutan",0), bid))

def delete_bank_info(bid):
    run("DELETE FROM bank_info WHERE id=%s", (bid,))

# ─── LOGISTIK MAKANAN ─────────────────────────────────────────────────────────
def get_logistik(trip_id):
    return q("SELECT * FROM trip_logistik WHERE trip_id=%s ORDER BY hari_ke,kategori,id", (trip_id,))

def create_logistik(trip_id, d):
    return run("INSERT INTO trip_logistik (trip_id,nama_item,kategori,jumlah,satuan,hari_ke,estimasi_harga,catatan) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (trip_id, d["nama_item"], d.get("kategori","Lainnya"), d.get("jumlah",1), d.get("satuan","porsi"),
         d.get("hari_ke",1), d.get("estimasi_harga",0), d.get("catatan")))

def update_logistik(lid, d):
    return run("UPDATE trip_logistik SET nama_item=%s,kategori=%s,jumlah=%s,satuan=%s,hari_ke=%s,estimasi_harga=%s,catatan=%s WHERE id=%s",
        (d["nama_item"], d.get("kategori","Lainnya"), d.get("jumlah",1), d.get("satuan","porsi"),
         d.get("hari_ke",1), d.get("estimasi_harga",0), d.get("catatan"), lid))

def delete_logistik(lid):
    run("DELETE FROM trip_logistik WHERE id=%s", (lid,))

def get_logistik_summary(trip_id):
    rows = q("""SELECT kategori, COUNT(*) as jml, SUM(estimasi_harga*jumlah) as total
                FROM trip_logistik WHERE trip_id=%s GROUP BY kategori ORDER BY kategori""", (trip_id,))
    return rows


# ─── P3K & MEDIS ─────────────────────────────────────────────────────────────
def get_p3k(trip_id, f_kategori=None):
    if f_kategori:
        return q("SELECT * FROM trip_p3k WHERE trip_id=%s AND kategori=%s ORDER BY label,kategori,id",
                 (trip_id, f_kategori))
    return q("SELECT * FROM trip_p3k WHERE trip_id=%s ORDER BY label,kategori,id", (trip_id,))

def create_p3k(trip_id, d):
    return run("INSERT INTO trip_p3k (trip_id,nama_item,kategori,jumlah,satuan,label,sudah_disiapkan,catatan) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (trip_id, d["nama_item"], d.get("kategori","Obat Umum"), d.get("jumlah",1), d.get("satuan","pcs"),
         d.get("label","Wajib"), 0, d.get("catatan")))

def update_p3k(pid, d):
    return run("UPDATE trip_p3k SET nama_item=%s,kategori=%s,jumlah=%s,satuan=%s,label=%s,catatan=%s WHERE id=%s",
        (d["nama_item"], d.get("kategori","Obat Umum"), d.get("jumlah",1), d.get("satuan","pcs"),
         d.get("label","Wajib"), d.get("catatan"), pid))

def toggle_p3k(pid, val):
    run("UPDATE trip_p3k SET sudah_disiapkan=%s WHERE id=%s", (bool(val), pid))

def delete_p3k(pid):
    run("DELETE FROM trip_p3k WHERE id=%s", (pid,))

def seed_p3k_from_template(trip_id):
    """Isi P3K dari template standar jika belum ada item."""
    existing = get_p3k(trip_id)
    if existing:
        return 0
    from database import SEED_P3K
    count = 0
    for nama, kat, jml, sat, label, catatan in SEED_P3K:
        create_p3k(trip_id, dict(nama_item=nama, kategori=kat, jumlah=jml,
                                  satuan=sat, label=label, catatan=catatan))
        count += 1
    return count


# ─── BAWA APA: status checklist per item ─────────────────────────────────────
def get_bawa_apa_with_checklist(trip_id, member_id=None):
    """
    Ambil semua item Master yang ada di trip, gabungkan dengan status checklist.
    Returns list item dengan field: sudah_siap (group or personal), dibawa_nama, etc.
    """
    # Kelompok items: dari checklist_group
    group_items = q("""
        SELECT cg.*, c.icon as cat_icon, c.nama_kategori,
               tm.nama_lengkap as dibawa_nama, tm.nama_panggilan as dibawa_panggilan
        FROM trip_checklist_group cg
        LEFT JOIN categories c ON cg.category_id = c.id
        LEFT JOIN trip_members tm ON cg.dibawa_oleh = tm.id
        WHERE cg.trip_id=%s
        ORDER BY c.nama_kategori, cg.nama_item
    """, (trip_id,))

    # Personal items: dari checklist_personal untuk member tertentu
    personal_items = []
    if member_id:
        personal_items = q("""
            SELECT cp.*, c.icon as cat_icon, c.nama_kategori
            FROM trip_checklist_personal cp
            LEFT JOIN categories c ON cp.category_id = c.id
            WHERE cp.trip_id=%s AND cp.member_id=%s
            ORDER BY c.nama_kategori, cp.nama_item
        """, (trip_id, member_id))

    return group_items, personal_items

# ─── TIMELINE SKENARIO ────────────────────────────────────────────────────────
def get_timeline_scenarios(trip_id):
    return q("SELECT * FROM trip_timeline_scenarios WHERE trip_id=%s ORDER BY urutan, id", (trip_id,))

def create_scenario(trip_id, nama, deskripsi=None):
    return run("INSERT INTO trip_timeline_scenarios (trip_id, nama, deskripsi, urutan) VALUES (%s,%s,%s,(SELECT COALESCE(MAX(urutan),0)+1 FROM trip_timeline_scenarios ts2 WHERE ts2.trip_id=%s))",
               (trip_id, nama, deskripsi, trip_id))

def update_scenario(sid, nama, deskripsi=None):
    run("UPDATE trip_timeline_scenarios SET nama=%s, deskripsi=%s WHERE id=%s", (nama, deskripsi, sid))

def delete_scenario(sid):
    run("DELETE FROM trip_timeline WHERE scenario_id=%s", (sid,))
    run("DELETE FROM trip_timeline_scenarios WHERE id=%s", (sid,))

def get_timeline_by_scenario(trip_id, scenario_id):
    rows = q("""
        SELECT * FROM trip_timeline
        WHERE trip_id=%s AND scenario_id=%s
        ORDER BY hari_ke, urutan, jam_mulai
    """, (trip_id, scenario_id))
    days = {}
    for r in rows:
        days.setdefault(r["hari_ke"], []).append(r)
    return days