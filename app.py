"""
app.py — TrailLog v5
REDESIGN TOTAL: layout, sidebar, semua halaman
Logic & fitur identik dengan versi sebelumnya.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta, time as dtime

from database import init_database, ADMIN_EMAIL, init_timeline_table, init_bank_table, seed_from_sql
import logic as L

st.set_page_config(page_title="TrailLog", page_icon="⛰️", layout="wide",
                   initial_sidebar_state="expanded")

# ─── SESSION RESTORE ──────────────────────────────────────────────────────────
def _check_localstorage_restore():
    try:
        params = st.query_params
        if "u" in params and not st.session_state.get("logged_in_email"):
            import base64
            decoded = base64.b64decode(params["u"]).decode("utf-8")
            if ":" in decoded:
                em, rl = decoded.split(":", 1)
                user = L.get_user_by_email(em.strip())
                if user:
                    st.session_state["logged_in_email"] = user["email"]
                    st.session_state["logged_in_role"]  = user["role"]
    except Exception:
        pass

def _save_session_to_url():
    email = st.session_state.get("logged_in_email","")
    role  = st.session_state.get("logged_in_role","")
    if email:
        import base64
        encoded = base64.b64encode("{}:{}".format(email,role).encode()).decode()
        try: st.query_params["u"] = encoded
        except Exception: pass

# ─── DESIGN TOKENS & CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root{
  --bg:#0b0f14; --surface:#111720; --card:#161e2a;
  --raised:#1c2638; --border:#243044; --border2:#2e3f58;
  --txt:#e2eaf5; --txt2:#8aa0c0; --txt3:#4a6080;
  --accent:#3b82f6; --accent2:#60a5fa;
  --green:#22c55e; --orange:#f59e0b; --red:#ef4444;
  --teal:#06b6d4; --purple:#a855f7; --pink:#ec4899; --yellow:#eab308;
  --r:10px; --rl:16px;
}

*,*::before,*::after{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important;}

/* ─ App ─ */
.stApp{background:var(--bg)!important;color:var(--txt)!important;}
.main .block-container{padding:0!important;max-width:100%!important;}

/* ─ Sidebar ─ */
section[data-testid="stSidebar"]{
  background:var(--surface)!important;
  border-right:1px solid var(--border)!important;
  min-width:260px!important;max-width:260px!important;
}
section[data-testid="stSidebar"]>div{padding:0!important;overflow-y:auto!important;overflow-x:hidden!important;}
section[data-testid="stSidebar"] .stButton>button{
  width:100%!important;text-align:left!important;background:transparent!important;
  color:var(--txt3)!important;border:none!important;border-radius:8px!important;
  padding:8px 14px!important;font-size:13px!important;font-weight:500!important;
  font-family:'Plus Jakarta Sans',sans-serif!important;
  transition:all 0.12s!important;line-height:1.4!important;min-height:unset!important;margin:1px 0!important;
}
section[data-testid="stSidebar"] .stButton>button:hover{
  background:var(--raised)!important;color:var(--txt)!important;padding-left:18px!important;
}

/* ─ Metrics ─ */
div[data-testid="metric-container"]{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:var(--rl)!important;padding:18px 20px!important;
  transition:border-color .2s,box-shadow .2s!important;
}
div[data-testid="metric-container"]:hover{border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(59,130,246,.1)!important;}
div[data-testid="metric-container"] label{font-family:'IBM Plex Mono',monospace!important;font-size:10px!important;font-weight:500!important;letter-spacing:1.5px!important;text-transform:uppercase!important;color:var(--txt3)!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{font-family:'IBM Plex Mono',monospace!important;font-size:24px!important;font-weight:600!important;color:var(--accent2)!important;}
div[data-testid="metric-container"] [data-testid="stMetricDelta"]{color:var(--green)!important;}

/* ─ Buttons ─ */
.stButton>button{
  background:var(--accent)!important;color:#fff!important;border:none!important;
  border-radius:var(--r)!important;font-size:13px!important;font-weight:600!important;
  padding:10px 18px!important;font-family:'Plus Jakarta Sans',sans-serif!important;transition:all .15s!important;
}
.stButton>button:hover{background:var(--accent2)!important;transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(59,130,246,.4)!important;}
.stButton>button:active{transform:translateY(0)!important;}
.btn-ok>button{background:var(--green)!important;color:#052e16!important;}
.btn-ok>button:hover{background:#4ade80!important;box-shadow:0 6px 20px rgba(34,197,94,.4)!important;}
.btn-warn>button{background:var(--orange)!important;color:#1c1003!important;}
.btn-warn>button:hover{background:#fbbf24!important;box-shadow:0 6px 20px rgba(245,158,11,.4)!important;}
.btn-danger>button{background:var(--red)!important;color:#fff!important;font-size:12px!important;padding:7px 14px!important;}
.btn-danger>button:hover{background:#f87171!important;box-shadow:0 6px 20px rgba(239,68,68,.4)!important;}
.btn-gray>button{background:var(--raised)!important;color:var(--txt2)!important;border:1px solid var(--border)!important;}
.btn-gray>button:hover{color:var(--txt)!important;border-color:var(--border2)!important;}
.btn-teal>button{background:var(--teal)!important;color:#04212a!important;}
.btn-purple>button{background:var(--purple)!important;color:#fff!important;}

/* ─ Inputs ─ */
.stTextInput>div>div>input,.stNumberInput>div>div>input,
.stTextArea>div>div>textarea,.stDateInput>div>div>input,.stTimeInput>div>div>input{
  background:var(--raised)!important;border:1px solid var(--border)!important;
  color:var(--txt)!important;border-radius:var(--r)!important;font-size:13.5px!important;
  font-family:'Plus Jakarta Sans',sans-serif!important;transition:border-color .15s,box-shadow .15s!important;
}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(59,130,246,.15)!important;outline:none!important;
}
div[data-baseweb="select"]>div{background:var(--raised)!important;border-color:var(--border)!important;color:var(--txt)!important;border-radius:var(--r)!important;font-size:13.5px!important;}
div[data-baseweb="popover"] div{background:var(--card)!important;color:var(--txt)!important;border-color:var(--border)!important;}
label{color:var(--txt2)!important;font-size:12.5px!important;font-weight:600!important;}

/* ─ Expander ─ */
.streamlit-expanderHeader{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important;color:var(--txt)!important;font-weight:600!important;font-size:13px!important;padding:12px 16px!important;}
.streamlit-expanderHeader:hover{border-color:var(--accent)!important;}
.streamlit-expanderContent{background:var(--raised)!important;border:1px solid var(--border)!important;border-top:none!important;border-radius:0 0 var(--r) var(--r)!important;padding:14px 16px!important;}

/* ─ Tabs ─ */
.stTabs [data-baseweb="tab-list"]{background:transparent;border-bottom:2px solid var(--border);padding:0;gap:0;border-radius:0;}
.stTabs [data-baseweb="tab"]{background:transparent;color:var(--txt3);border-radius:0;font-size:13px;font-weight:600;padding:10px 20px;border:none!important;border-bottom:2px solid transparent!important;transition:all .14s;font-family:'Plus Jakarta Sans',sans-serif!important;margin-bottom:-2px!important;}
.stTabs [data-baseweb="tab"]:hover{color:var(--txt2);background:rgba(59,130,246,.05);}
.stTabs [aria-selected="true"]{background:transparent!important;color:var(--accent2)!important;font-weight:700!important;border-bottom:2px solid var(--accent)!important;}

/* ─ Misc ─ */
.stDataFrame{border:1px solid var(--border)!important;border-radius:var(--r)!important;overflow:hidden!important;}
.stMultiSelect [data-baseweb="tag"]{background:rgba(59,130,246,.2)!important;color:var(--accent2)!important;border-radius:5px!important;}
hr{border-color:var(--border)!important;margin:16px 0!important;}
.stCheckbox label,.stRadio label{color:var(--txt)!important;font-size:13.5px!important;}
.stCheckbox label p,.stRadio label p{color:var(--txt)!important;}
p,div{font-family:'Plus Jakarta Sans',sans-serif!important;}

/* ─ Page wrapper ─ */
.pw{padding:28px 36px 64px;max-width:1380px;margin:0 auto;}

/* ─ Page header ─ */
.page-hdr{display:flex;align-items:center;gap:16px;margin-bottom:28px;padding-bottom:20px;border-bottom:2px solid var(--border);}
.page-icon{width:52px;height:52px;border-radius:14px;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.25);display:flex;align-items:center;justify-content:center;font-size:26px;flex-shrink:0;}
.page-title{font-size:22px;font-weight:800;color:var(--txt);letter-spacing:-.03em;line-height:1.1;}
.page-sub{font-size:13px;color:var(--txt3);margin-top:5px;font-weight:400;}

/* ─ Cards ─ */
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--rl);padding:18px 20px;margin-bottom:10px;transition:border-color .18s,box-shadow .18s;animation:fadeUp .18s ease both;}
.card:hover{border-color:var(--border2);box-shadow:0 4px 24px rgba(0,0,0,.25);}
.card-blue{border-left:3px solid var(--accent);}
.card-green{border-left:3px solid var(--green);}
.card-orange{border-left:3px solid var(--orange);}
.card-red{border-left:3px solid var(--red);}
.card-purple{border-left:3px solid var(--purple);}
.card-teal{border-left:3px solid var(--teal);}

/* ─ Stat box ─ */
.stat-box{background:var(--card);border:1px solid var(--border);border-radius:var(--rl);padding:20px;text-align:center;}
.stat-lbl{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:500;letter-spacing:2px;text-transform:uppercase;color:var(--txt3);}
.stat-val{font-family:'IBM Plex Mono',monospace;font-size:28px;font-weight:600;color:var(--accent2);margin-top:8px;}
.stat-sub{font-size:12px;color:var(--txt2);margin-top:6px;}

/* ─ Section label ─ */
.sec-lbl{font-size:10px;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:1.5px;margin:20px 0 10px;display:flex;align-items:center;gap:8px;}
.sec-lbl::after{content:'';flex:1;height:1px;background:var(--border);}

/* ─ Progress ─ */
.prog{height:5px;background:var(--raised);border-radius:4px;overflow:hidden;margin-top:8px;}
.prog-fill{height:100%;border-radius:4px;background:var(--accent);transition:width .5s;}
.prog-g{background:var(--green);} .prog-o{background:var(--orange);} .prog-r{background:var(--red);} .prog-t{background:var(--teal);}

/* ─ Alerts ─ */
.al{padding:12px 16px;border-radius:var(--r);font-size:13px;line-height:1.6;margin:10px 0;font-weight:500;}
.al-i{background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.25);border-left:3px solid var(--accent);color:#93c5fd;}
.al-w{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25);border-left:3px solid var(--orange);color:#fcd34d;}
.al-s{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-left:3px solid var(--green);color:#86efac;}
.al-d{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-left:3px solid var(--red);color:#fca5a5;}

/* ─ Badges ─ */
.badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700;font-family:'IBM Plex Mono',monospace;white-space:nowrap;}
.b-blue{background:rgba(59,130,246,.15);color:#93c5fd;border:1px solid rgba(59,130,246,.3);}
.b-green{background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.3);}
.b-orange{background:rgba(245,158,11,.15);color:#fcd34d;border:1px solid rgba(245,158,11,.3);}
.b-red{background:rgba(239,68,68,.15);color:#fca5a5;border:1px solid rgba(239,68,68,.3);}
.b-purple{background:rgba(168,85,247,.15);color:#d8b4fe;border:1px solid rgba(168,85,247,.3);}
.b-teal{background:rgba(6,182,212,.15);color:#67e8f9;border:1px solid rgba(6,182,212,.3);}
.b-gray{background:rgba(138,160,192,.1);color:var(--txt2);border:1px solid rgba(138,160,192,.2);}
.b-yellow{background:rgba(234,179,8,.15);color:#fde68a;border:1px solid rgba(234,179,8,.3);}
.b-pink{background:rgba(236,72,153,.15);color:#f9a8d4;border:1px solid rgba(236,72,153,.3);}

/* ─ Bank card ─ */
.bank-card{background:var(--card);border:1px solid var(--border);border-radius:var(--rl);padding:20px 24px;display:flex;align-items:center;gap:20px;margin-bottom:12px;transition:border-color .2s,box-shadow .2s;}
.bank-card:hover{border-color:var(--accent);box-shadow:0 4px 20px rgba(59,130,246,.12);}
.bank-logo{font-size:36px;flex-shrink:0;}
.bank-name{font-size:14px;font-weight:700;color:var(--txt);}
.bank-acc{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;color:var(--accent2);letter-spacing:.1em;margin-top:5px;}
.bank-holder{font-size:12px;color:var(--txt2);margin-top:3px;}

/* ─ Rekap table ─ */
.rekap-tbl{width:100%;border-collapse:collapse;font-size:13px;}
.rekap-tbl td{padding:9px 12px;border-bottom:1px solid var(--border);color:var(--txt2);}
.rekap-tbl tr:last-child td{border-bottom:none;}
.rekap-tbl .col-r{text-align:right;font-family:'IBM Plex Mono',monospace;}
.rekap-tbl .row-total td{border-top:2px solid var(--border2);font-weight:700;color:var(--txt);}
.rekap-tbl .row-net td{color:var(--orange);font-weight:700;font-family:'IBM Plex Mono',monospace;}
.rekap-tbl .row-neg td{color:var(--green);font-weight:700;font-family:'IBM Plex Mono',monospace;}

/* ─ Item / checklist row ─ */
.irow{background:var(--raised);border:1px solid var(--border);border-radius:var(--r);padding:10px 14px;margin-bottom:6px;transition:border-color .14s;}
.irow:hover{border-color:var(--border2);}
.cl-done{background:rgba(34,197,94,.06);border-color:rgba(34,197,94,.3)!important;}

/* ─ Scrollbar ─ */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--border2);}

/* ─ Animation ─ */
@keyframes fadeUp{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:translateY(0);}}

/* ─ Mobile ─ */
@media(max-width:768px){.pw{padding:14px 12px 40px;}.page-title{font-size:18px!important;}.stTabs [data-baseweb="tab"]{font-size:11px!important;padding:8px 10px!important;}}
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
CATS       = ["Pendakian","Camp","Makan","Transportasi","Istirahat","Darurat","Lainnya"]
CAT_COLORS = {"Pendakian":"#3b82f6","Camp":"#22c55e","Makan":"#f59e0b",
              "Transportasi":"#06b6d4","Istirahat":"#a855f7","Darurat":"#ef4444","Lainnya":"#64748b"}
CAT_ICONS  = {"Pendakian":"⛰️","Camp":"⛺","Makan":"🍱",
              "Transportasi":"🚌","Istirahat":"😴","Darurat":"🚨","Lainnya":"📍"}
NOTE_ICON  = {"Umum":"📝","Penting":"📌","Darurat":"🚨","Info":"ℹ️"}
_MISS      = object()

# ─── UI HELPERS ───────────────────────────────────────────────────────────────
def _pw():
    st.markdown("<div class='pw'>", unsafe_allow_html=True)

def _pw_end():
    st.markdown("</div>", unsafe_allow_html=True)

def ph(icon, title, sub=""):
    sub_h = "<div class='page-sub'>{}</div>".format(sub) if sub else ""
    st.markdown(
        "<div class='page-hdr'>"
        "<div class='page-icon'>{}</div>"
        "<div><div class='page-title'>{}</div>{}</div>"
        "</div>".format(icon, title, sub_h),
        unsafe_allow_html=True)

def sec(label):
    st.markdown("<div class='sec-lbl'>{}</div>".format(label), unsafe_allow_html=True)

def badge(txt, color="gray"):
    cls = {"blue":"b-blue","green":"b-green","orange":"b-orange","red":"b-red",
           "purple":"b-purple","teal":"b-teal","gray":"b-gray","yellow":"b-yellow","pink":"b-pink"}.get(color,"b-gray")
    return "<span class='badge {}'>{}</span>".format(cls, txt)

def alert(txt, kind="info"):
    cls = {"info":"al-i","warning":"al-w","success":"al-s","danger":"al-d"}.get(kind,"al-i")
    st.markdown("<div class='al {}'>{}</div>".format(cls, txt), unsafe_allow_html=True)

def pb(pct, color="blue"):
    ex = " prog-g" if color=="green" else " prog-o" if color=="orange" else " prog-r" if color=="red" else " prog-t" if color=="teal" else ""
    st.markdown("<div class='prog'><div class='prog-fill{}' style='width:{}%'></div></div>".format(ex,min(100,max(0,pct))), unsafe_allow_html=True)

def msep():
    st.markdown("<hr style='border-color:var(--border);margin:14px 0 18px;'>", unsafe_allow_html=True)

def confirm_del(key, on_confirm, label="🗑️", msg="Yakin hapus?"):
    ck = "_cd_{}".format(key)
    if st.session_state.get(ck):
        c1,c2,c3 = st.columns([5,1,1])
        c1.markdown("<div style='padding:7px 0;font-size:12px;color:#fca5a5;'>⚠️ {}</div>".format(msg), unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("Ya", key="_cdy_{}".format(key), use_container_width=True):
                on_confirm(); st.session_state.pop(ck,None); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="btn-gray">', unsafe_allow_html=True)
            if st.button("Batal", key="_cdn_{}".format(key), use_container_width=True):
                st.session_state.pop(ck,None); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button(label, key="_cdt_{}".format(key)):
            st.session_state[ck] = True; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def get_email():   return st.session_state.get("logged_in_email","")
def is_admin_user(): return get_email().strip().lower() == ADMIN_EMAIL.strip().lower()

def trip_selector(label="Pilih Trip"):
    email = get_email()
    trips = L.get_trips(None if is_admin_user() else email)
    if not trips: alert("Belum ada trip tersedia.","warning"); return None
    opts = {"{} — {}".format(t["nama_trip"],t["gunung_tujuan"]):t for t in trips}
    return opts[st.selectbox(label, list(opts.keys()), key="ts_{}".format(label[:8]))]

# ─── WILAYAH ──────────────────────────────────────────────────────────────────
def _wg(k):      return st.session_state.get("_wil_{}".format(k),_MISS)
def _ws(k,v):    st.session_state["_wil_{}".format(k)] = v
def _wil_clear():
    for k in [x for x in st.session_state if x.startswith("_wil_")]: del st.session_state[k]

def _provinces():
    c=_wg("prov");
    if c is not _MISS: return c
    d=L.api_provinces()
    if d: _ws("prov",d)
    return d

def _cities(pid):
    c=_wg("city_{}".format(pid))
    if c is not _MISS: return c
    d=L.api_cities(pid)
    if d: _ws("city_{}".format(pid),d)
    return d

def _districts(cid):
    c=_wg("dist_{}".format(cid))
    if c is not _MISS: return c
    d=L.api_districts(cid)
    if d: _ws("dist_{}".format(cid),d)
    return d

def _villages(did):
    c=_wg("vil_{}".format(did))
    if c is not _MISS: return c
    d=L.api_villages(did)
    if d: _ws("vil_{}".format(did),d)
    return d

def _all_cities():
    cached = st.session_state.get("_wil_all_cities")
    if cached: return cached
    provinces = _provinces()
    if not provinces: return []
    import concurrent.futures
    def fetch(p):
        cs=L.api_cities(p["id"])
        for c in cs: c["province_name"]=p["name"]
        return cs
    all_cities=[]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            for f in concurrent.futures.as_completed({ex.submit(fetch,p):p for p in provinces},timeout=20):
                try: all_cities.extend(f.result())
                except: pass
    except: pass
    all_cities=sorted(all_cities,key=lambda x:x.get("name","").lower())
    if all_cities: st.session_state["_wil_all_cities"]=all_cities
    return all_cities

def _tempat_lahir_selectbox(prefix, default=""):
    ld_k="{}_ttl_loaded".format(prefix)
    if not st.session_state.get(ld_k):
        with st.spinner("⏳ Memuat kota..."):
            cities=_all_cities()
        st.session_state[ld_k]=True
    else: cities=_all_cities()
    if not cities:
        return st.text_input("Tempat Lahir *", value=default, key="{}_ttl_manual".format(prefix))
    disp=["— Pilih Kota —"]+["{} ({})".format(c["name"],c.get("province_name","")) for c in cities]
    names=[None]+[c["name"] for c in cities]
    def_i=0
    if default:
        for i,c in enumerate(cities):
            if c["name"].lower()==default.lower(): def_i=i+1; break
    sel=st.selectbox("Tempat Lahir *",disp,index=def_i,key="{}_ttl_sel".format(prefix))
    return names[disp.index(sel)] or ""

def _api_status_indicator():
    prov=_provinces()
    if prov:
        st.markdown("<div style='display:flex;align-items:center;gap:8px;padding:8px 14px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-radius:8px;margin-bottom:10px;font-size:13px;color:#86efac;'>🟢 API Wilayah terhubung — {} provinsi</div>".format(len(prov)), unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding:10px 14px;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-radius:8px;margin-bottom:10px;'><span style='color:#fca5a5;font-size:13px;'>🔴 API Wilayah tidak terhubung — input manual</span></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh API",key="_api_ref"): _wil_clear(); st.rerun()
    return bool(prov)

def wilayah_form(prefix, d=None):
    d=d or {}; ss=st.session_state
    ik="{}_wil_inited".format(prefix)
    if not ss.get(ik) and any(d.get(k) for k in ["provinsi_id","kota_id","kecamatan_id","kelurahan_id"]):
        for k,sk in [("provinsi_id","prov"),("kota_id","kota"),("kecamatan_id","kec"),("kelurahan_id","kel")]:
            ss["{}_wil_{}_id".format(prefix,sk)]=d.get(k)
        ss[ik]=True
    def sk(p): return "{}_wil_{}_id".format(prefix,p)
    prov_list=_provinces() or []
    if prov_list:
        pnames=["— Pilih Provinsi —"]+[p["name"] for p in prov_list]
        pids=[None]+[p["id"] for p in prov_list]
        cur_pid=ss.get(sk("prov")); def_i=pids.index(cur_pid) if cur_pid in pids else 0
        def _on_prov():
            new=pids[pnames.index(ss["{}_wil_prov_sel".format(prefix)])]
            if new!=ss.get(sk("prov")):
                ss[sk("prov")]=new; ss[sk("kota")]=None; ss[sk("kec")]=None; ss[sk("kel")]=None
                if new: _cities(new)
        st.selectbox("Provinsi *",pnames,index=def_i,key="{}_wil_prov_sel".format(prefix),on_change=_on_prov)
        sel_pi=ss.get(sk("prov"))
    else:
        st.text_input("Provinsi *",value=d.get("provinsi_nama",""),key="{}_wil_prov_txt".format(prefix))
        sel_pi=None
    kota_list=_cities(sel_pi) if sel_pi else []
    if kota_list:
        knames=["— Kab/Kota —"]+[k["name"] for k in kota_list]
        kids=[None]+[k["id"] for k in kota_list]
        cur_kid=ss.get(sk("kota")); def_i=kids.index(cur_kid) if cur_kid in kids else 0
        def _on_kota():
            new=kids[knames.index(ss["{}_wil_kota_sel".format(prefix)])]
            if new!=ss.get(sk("kota")):
                ss[sk("kota")]=new; ss[sk("kec")]=None; ss[sk("kel")]=None
                if new: _districts(new)
        st.selectbox("Kab/Kota *",knames,index=def_i,key="{}_wil_kota_sel".format(prefix),on_change=_on_kota)
        sel_ki=ss.get(sk("kota"))
    elif sel_pi: st.info("⏳ Memuat kota..."); sel_ki=None
    else: st.selectbox("Kab/Kota *",["— Pilih Provinsi Dulu —"],disabled=True,key="{}_wil_kota_dis".format(prefix)); sel_ki=None
    kec_list=_districts(sel_ki) if sel_ki else []
    if kec_list:
        kcnames=["— Kecamatan —"]+[k["name"] for k in kec_list]
        kcids=[None]+[k["id"] for k in kec_list]
        cur_kcid=ss.get(sk("kec")); def_i=kcids.index(cur_kcid) if cur_kcid in kcids else 0
        def _on_kec():
            new=kcids[kcnames.index(ss["{}_wil_kec_sel".format(prefix)])]
            if new!=ss.get(sk("kec")):
                ss[sk("kec")]=new; ss[sk("kel")]=None
                if new: _villages(new)
        st.selectbox("Kecamatan *",kcnames,index=def_i,key="{}_wil_kec_sel".format(prefix),on_change=_on_kec)
        sel_kci=ss.get(sk("kec"))
    elif sel_ki: st.info("⏳ Memuat kecamatan..."); sel_kci=None
    else: st.selectbox("Kecamatan *",["— Pilih Kab/Kota Dulu —"],disabled=True,key="{}_wil_kec_dis".format(prefix)); sel_kci=None
    kel_list=_villages(sel_kci) if sel_kci else []
    if kel_list:
        klnames=["— Kelurahan —"]+[v["name"] for v in kel_list]
        klids=[None]+[v["id"] for v in kel_list]
        cur_klid=ss.get(sk("kel")); def_i=klids.index(cur_klid) if cur_klid in klids else 0
        def _on_kel(): ss[sk("kel")]=klids[klnames.index(ss["{}_wil_kel_sel".format(prefix)])]
        st.selectbox("Kelurahan/Desa *",klnames,index=def_i,key="{}_wil_kel_sel".format(prefix),on_change=_on_kel)
        sel_kli=ss.get(sk("kel"))
    elif sel_kci: st.info("⏳ Memuat kelurahan..."); sel_kli=None
    else: st.selectbox("Kelurahan/Desa *",["— Pilih Kecamatan Dulu —"],disabled=True,key="{}_wil_kel_dis".format(prefix)); sel_kli=None
    def _nm(lst,id_v):
        if not id_v: return None
        for it in lst:
            if it["id"]==id_v: return it["name"]
        return None
    return dict(provinsi_id=sel_pi,provinsi_nama=_nm(prov_list,sel_pi),
                kota_id=sel_ki,kota_nama=_nm(kota_list,sel_ki),
                kecamatan_id=sel_kci,kecamatan_nama=_nm(kec_list,sel_kci),
                kelurahan_id=sel_kli,kelurahan_nama=_nm(kel_list,sel_kli))

# ─── LOGIN ────────────────────────────────────────────────────────────────────
def page_login():
    st.markdown("""<style>
section[data-testid="stSidebar"]{display:none!important;}
.main .block-container{max-width:420px!important;padding:80px 20px 40px!important;}
</style>""", unsafe_allow_html=True)
    st.markdown("""
<div style="text-align:center;margin-bottom:32px;">
  <div style="width:80px;height:80px;margin:0 auto 20px;
    background:linear-gradient(135deg,#1d4ed8,#3b82f6);border-radius:22px;
    display:flex;align-items:center;justify-content:center;font-size:40px;
    box-shadow:0 12px 40px rgba(59,130,246,.5);">⛰️</div>
  <div style="font-size:32px;font-weight:800;color:#e2eaf5;letter-spacing:-.04em;
    font-family:'Plus Jakarta Sans',sans-serif;">TrailLog</div>
  <div style="font-size:14px;color:#4a6080;margin-top:8px;">Platform manajemen pendakian</div>
</div>
<div style="background:#111720;border:1px solid #243044;border-radius:18px;
  padding:32px 28px;box-shadow:0 16px 60px rgba(0,0,0,.6);">
""", unsafe_allow_html=True)
    st.markdown("<div style='font-size:15px;font-weight:700;color:#e2eaf5;margin-bottom:4px;'>Masuk dengan Email</div>", unsafe_allow_html=True)
    st.caption("Tidak perlu password — cukup email terdaftar")
    email_in = st.text_input("Email", placeholder="namakamu@email.com",
        label_visibility="collapsed", key="login_email_input")
    st.markdown('<div class="btn-ok">', unsafe_allow_html=True)
    if st.button("Masuk ke TrailLog →", use_container_width=True, key="login_btn"):
        email = email_in.strip().lower()
        if not email or "@" not in email:
            st.error("Masukkan email yang valid.")
        else:
            user = L.get_user_by_email(email)
            if not user:
                from database import get_connection
                con2=get_connection(); cur2=con2.cursor()
                cur2.execute("SELECT COUNT(*) FROM trip_members WHERE email=%s",(email,))
                cnt=cur2.fetchone()[0]; con2.close()
                if cnt>0:
                    L.create_user_if_not_exist(email)
                    user=L.get_user_by_email(email)
                else:
                    st.error("❌ Email tidak dikenali. Hubungi admin trip kamu.")
                    st.markdown('</div>',unsafe_allow_html=True)
                    st.markdown("</div>",unsafe_allow_html=True)
                    return
            st.session_state["logged_in_email"]=email
            st.session_state["logged_in_role"]=user["role"]
            st.session_state["page"]="dashboard"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        email=st.session_state.get("logged_in_email","")
        role=st.session_state.get("logged_in_role","member")
        trips=L.get_trips(None if role=="admin" else email)
        aktif=sum(1 for t in trips if t.get("status") in ("Perencanaan","Aktif"))
        cur=st.session_state.get("page","dashboard")

        # Logo
        st.markdown("""
<div style="padding:18px 16px 12px;border-bottom:1px solid #243044;
  display:flex;align-items:center;gap:12px;">
  <div style="width:42px;height:42px;background:linear-gradient(135deg,#1d4ed8,#3b82f6);
    border-radius:12px;display:flex;align-items:center;justify-content:center;
    font-size:22px;box-shadow:0 4px 16px rgba(59,130,246,.45);flex-shrink:0;">⛰️</div>
  <div>
    <div style="font-size:16px;font-weight:800;color:#e2eaf5;letter-spacing:-.03em;
      font-family:'Plus Jakarta Sans',sans-serif;">TrailLog</div>
    <div style="font-size:9px;color:#3b82f6;letter-spacing:2px;
      font-family:'IBM Plex Mono',monospace;text-transform:uppercase;margin-top:1px;">Pendakian Manager</div>
  </div>
</div>""", unsafe_allow_html=True)

        # User info
        rc="#f59e0b" if role=="admin" else "#22c55e"
        ic="🔑" if role=="admin" else "👤"
        rl="Administrator" if role=="admin" else "Member"
        st.markdown("""
<div style="margin:10px 10px 6px;padding:10px 12px;background:#1c2638;
  border:1px solid #243044;border-radius:11px;display:flex;align-items:center;gap:10px;">
  <div style="width:34px;height:34px;background:{rc}20;border:1px solid {rc}50;border-radius:50%;
    display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">{ic}</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:12px;font-weight:700;color:#e2eaf5;overflow:hidden;text-overflow:ellipsis;
      white-space:nowrap;">{em}</div>
    <div style="font-size:9.5px;font-weight:700;color:{rc};margin-top:1px;">{rl}</div>
  </div>
</div>""".format(rc=rc,ic=ic,em=email.split("@")[0] if email else "?",rl=rl), unsafe_allow_html=True)

        # Stats mini
        st.markdown("""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:0 10px 8px;">
  <div style="background:#161e2a;border:1px solid #243044;border-radius:9px;padding:8px 10px;text-align:center;">
    <div style="font-size:18px;font-weight:800;color:#e2eaf5;font-family:'IBM Plex Mono',monospace;">{nt}</div>
    <div style="font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;margin-top:1px;">Trip</div>
  </div>
  <div style="background:#161e2a;border:1px solid #243044;border-radius:9px;padding:8px 10px;text-align:center;">
    <div style="font-size:18px;font-weight:800;color:#22c55e;font-family:'IBM Plex Mono',monospace;">{na}</div>
    <div style="font-size:9px;color:#22c55e;text-transform:uppercase;letter-spacing:1px;margin-top:1px;opacity:.8;">Aktif</div>
  </div>
</div>""".format(nt=len(trips),na=aktif), unsafe_allow_html=True)

        def nav_sep(label):
            st.markdown("<div style='padding:8px 14px 3px;font-size:9px;font-weight:700;color:#4a6080;text-transform:uppercase;letter-spacing:1.5px;font-family:IBM Plex Mono,monospace;'>{}</div>".format(label), unsafe_allow_html=True)

        def nav(icon, label, page_key):
            is_cur=(cur==page_key)
            if is_cur:
                st.markdown("""
<div style="margin:1px 8px;padding:9px 14px;background:rgba(59,130,246,.12);
  border-radius:9px;border-left:3px solid #3b82f6;
  display:flex;align-items:center;gap:10px;">
  <span style="font-size:15px;line-height:1;">{}</span>
  <span style="font-size:13px;font-weight:700;color:#60a5fa;
    font-family:'Plus Jakarta Sans',sans-serif;">{}</span>
</div>""".format(icon,label), unsafe_allow_html=True)
            else:
                if st.button("{} {}".format(icon,label), key="nb_{}".format(page_key)):
                    st.session_state["page"]=page_key; st.rerun()

        nav_sep("Utama")
        nav("🏠","Dashboard","dashboard")

        nav_sep("Trip")
        nav("🗺️","Manajemen Trip","trips")
        nav("📅","Timeline","timeline")
        nav("👥","Anggota Trip","members")
        if role=="admin": nav("👤","Master Anggota","members_master")

        nav_sep("Keuangan")
        if role=="admin": nav("💰","Input Biaya","biaya")
        nav("📊","Rekap & Kalkulasi","rekap")
        nav("💳","Pelacak Pembayaran","payments")

        nav_sep("Persiapan")
        nav("✅","Packing Kelompok","cl_group")
        nav("🎒","Packing Personal","cl_personal")
        nav("🍱","Logistik Makanan","logistik")
        nav("💊","P3K & Medis","medis")
        nav("📦","Bawa Apa?","bawa_apa")
        nav("⚖️","Analisis Berat","berat")
        nav("📝","Catatan Trip","notes")

        nav_sep("Fitness")
        nav("💪","Latihan Fisik","exercises")

        if role=="admin":
            nav_sep("Sistem")
            nav("⚙️","Pengaturan","settings")

        # Footer
        st.markdown("<div style='height:1px;background:#243044;margin:10px 10px 8px;'></div>", unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            dark=st.session_state.get("dark_mode",True)
            if st.button("☀️ Light" if dark else "🌙 Dark", key="sb_dm", use_container_width=True):
                st.session_state["dark_mode"]=not dark; st.rerun()
        with c2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("Keluar",key="sb_logout",use_container_width=True):
                for k in ["logged_in_email","logged_in_role","page"]: st.session_state.pop(k,None)
                try: st.query_params.clear()
                except Exception: pass
                st.rerun()
            st.markdown("</div>",unsafe_allow_html=True)

    return cur

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    _pw()
    email=get_email(); admin=is_admin_user()
    ph("🏠","Dashboard","Ringkasan semua aktivitas pendakian")
    trips=L.get_trips(None if admin else email)
    cats=L.get_categories(); items=L.get_items_master(); anggota=L.get_members_master()
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("📋 Total Trip",len(trips))
    c2.metric("🟢 Aktif",sum(1 for t in trips if t["status"]=="Aktif"))
    c3.metric("📅 Perencanaan",sum(1 for t in trips if t["status"]=="Perencanaan"))
    c4.metric("🏷️ Kategori",len(cats))
    c5.metric("👤 Anggota DB",len(anggota))
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    col_main,col_side=st.columns([3,1])
    with col_main:
        sec("📋 Trip Terkini")
        if not trips: alert("Belum ada trip. Buat di menu Manajemen Trip.","info")
        else:
            for t in trips[:6]:
                stc={"Perencanaan":"#3b82f6","Aktif":"#22c55e","Selesai":"#06b6d4","Dibatalkan":"#ef4444"}.get(t["status"],"#64748b")
                dur=(t["tanggal_kembali"]-t["tanggal_berangkat"]).days+1 if t.get("tanggal_kembali") else "?"
                tbf=t["tanggal_berangkat"].strftime("%d %b %Y") if t.get("tanggal_berangkat") else "—"
                sisa=""
                if t.get("tanggal_kembali") and t["status"]=="Aktif":
                    s=(t["tanggal_kembali"]-date.today()).days
                    if s>=0: sisa="<span style='background:rgba(34,197,94,.15);color:#86efac;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;'>⏳ {}h lagi</span>".format(s)
                html_card = (
                    "<div class='card card-blue' style='display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;'>"
                    "<div>"
                    "<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;'>"
                    "<span style='font-size:15px;font-weight:700;color:#e2eaf5;'>{nm}</span>"
                    "<span style='background:{stc};opacity:.85;color:{stc};border:1px solid {stc};padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700;"
                    "background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.4);color:{stc};'>{sts}</span>"
                    "{sisa}"
                    "</div>"
                    "<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
                    "<span style='font-size:12px;color:#8aa0c0;'>📍 {gu}</span>"
                    "<span style='font-size:12px;color:#8aa0c0;'>📅 {tb}</span>"
                    "<span style='font-size:12px;color:#8aa0c0;'>⏱️ {dur}h</span>"
                    "<span style='font-size:12px;color:#8aa0c0;'>👥 {jml}</span>"
                    "<span style='font-size:12px;color:#60a5fa;font-family:IBM Plex Mono,monospace;font-weight:600;'>💰 {biaya}</span>"
                    "</div></div>"
                    "<div style='text-align:right;'>"
                    "<span style='font-size:11px;color:#4a6080;background:#1c2638;padding:3px 8px;border-radius:6px;'>{tp}</span>"
                    "</div></div>"
                ).format(nm=t["nama_trip"], stc=stc, sts=t["status"], sisa=sisa,
                         gu=t["gunung_tujuan"], tb=tbf, dur=dur,
                         jml="{}org".format(t["jumlah_orang"]),
                         biaya=L.fmt_rp(t["total_biaya"]), tp=t["tipe_pendakian"])
                # Fix status badge color per-status
                status_bg = {"Perencanaan":"rgba(59,130,246,.15)","Aktif":"rgba(34,197,94,.15)","Selesai":"rgba(6,182,212,.15)","Dibatalkan":"rgba(239,68,68,.15)"}.get(t["status"],"rgba(100,116,139,.15)")
                status_bd = {"Perencanaan":"rgba(59,130,246,.4)","Aktif":"rgba(34,197,94,.4)","Selesai":"rgba(6,182,212,.4)","Dibatalkan":"rgba(239,68,68,.4)"}.get(t["status"],"rgba(100,116,139,.4)")
                st.markdown(
                    "<div class='card card-blue' style='display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;'>"
                    "<div><div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;'>"
                    "<span style='font-size:15px;font-weight:700;color:#e2eaf5;'>{nm}</span>"
                    "<span style='background:{sbg};color:{stc};border:1px solid {sbd};padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700;'>{sts}</span>"
                    "{sisa}</div>"
                    "<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
                    "<span style='font-size:12px;color:#8aa0c0;'>📍 {gu}</span>"
                    "<span style='font-size:12px;color:#8aa0c0;'>📅 {tb}</span>"
                    "<span style='font-size:12px;color:#8aa0c0;'>⏱️ {dur}h</span>"
                    "<span style='font-size:12px;color:#8aa0c0;'>👥 {jml}</span>"
                    "<span style='font-size:12px;color:#60a5fa;font-family:IBM Plex Mono,monospace;font-weight:600;'>💰 {biaya}</span>"
                    "</div></div>"
                    "<div style='text-align:right;'><span style='font-size:11px;color:#4a6080;background:#1c2638;padding:3px 8px;border-radius:6px;'>{tp}</span></div>"
                    "</div>".format(
                        nm=t["nama_trip"], sbg=status_bg, stc=stc, sbd=status_bd,
                        sts=t["status"], sisa=sisa, gu=t["gunung_tujuan"], tb=tbf,
                        dur=dur, jml="{}org".format(t["jumlah_orang"]),
                        biaya=L.fmt_rp(t["total_biaya"]), tp=t["tipe_pendakian"]),
                    unsafe_allow_html=True)
            if len(trips)>6: st.caption("… dan {} trip lainnya".format(len(trips)-6))
    with col_side:
        sec("📊 Status")
        for sts,color in [("Aktif","#22c55e"),("Perencanaan","#3b82f6"),("Selesai","#06b6d4"),("Dibatalkan","#ef4444")]:
            n=sum(1 for t in trips if t["status"]==sts)
            if n==0: continue
            st.markdown("""
<div style='display:flex;justify-content:space-between;align-items:center;
  padding:10px 14px;background:#161e2a;border:1px solid #243044;
  border-left:3px solid {c};border-radius:10px;margin-bottom:6px;'>
  <span style='font-size:13px;font-weight:600;color:#e2eaf5;'>{s}</span>
  <span style='font-size:18px;font-weight:700;color:{c};font-family:IBM Plex Mono,monospace;'>{n}</span>
</div>""".format(c=color,s=sts,n=n),unsafe_allow_html=True)
        if items:
            st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
            sec("📦 Item Master")
            st.metric("Total",len(items))
    _pw_end()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: TRIPS
# ═══════════════════════════════════════════════════════════════════════════════
def page_trips():
    _pw()
    admin=is_admin_user(); email=get_email()
    ph("🗺️","Manajemen Trip","Kelola semua rencana pendakian")
    tabs=st.tabs(["➕ Buat Trip","📋 Daftar Trip","✏️ Edit Trip"] if admin else ["📋 Daftar Trip"])

    if admin:
        with tabs[0]:
            with st.form("trip_new",clear_on_submit=True):
                c1,c2=st.columns(2)
                with c1:
                    nm=st.text_input("Nama Trip *",placeholder="Pendakian Rinjani 2025")
                    gu=st.text_input("Gunung Tujuan *",placeholder="Gunung Rinjani")
                    jl=st.text_input("Jalur Pendakian",placeholder="Sembalun")
                with c2:
                    tp=st.selectbox("Tipe",["Camping","Tektok"])
                    st2=st.selectbox("Status",["Perencanaan","Aktif","Selesai","Dibatalkan"])
                    jo=st.number_input("Jumlah Orang",min_value=1,max_value=500,value=10)
                dc1,dc2=st.columns(2)
                tb_=dc1.date_input("Tanggal Berangkat",value=date.today())
                tk_=dc2.date_input("Tanggal Kembali",value=date.today())
                ct=st.text_area("Catatan",height=68)
                if st.form_submit_button("✅ Buat Trip",use_container_width=True):
                    if not nm or not gu: st.error("Nama Trip & Gunung wajib!")
                    elif tk_<tb_: st.error("Tanggal kembali tidak boleh sebelum berangkat!")
                    else:
                        L.create_trip(dict(nama_trip=nm,gunung_tujuan=gu,jalur_pendakian=jl,
                            tipe_pendakian=tp,status=st2,tanggal_berangkat=tb_,
                            tanggal_kembali=tk_,jumlah_orang=jo,catatan=ct))
                        st.success("✅ Trip {} dibuat!".format(nm)); st.rerun()

    li=1 if admin else 0
    with tabs[li]:
        trips=L.get_trips(None if admin else email)
        if not trips: alert("Belum ada trip.","info")
        else:
            fc1,fc2,fc3=st.columns(3)
            fs=fc1.selectbox("Status",["Semua","Perencanaan","Aktif","Selesai","Dibatalkan"],key="tl_fs")
            ft=fc2.selectbox("Tipe",["Semua","Camping","Tektok"],key="tl_ft")
            fq=fc3.text_input("🔍 Cari","",key="tl_fq",placeholder="Nama atau gunung...")
            filt=[t for t in trips
                if (fs=="Semua" or t["status"]==fs) and (ft=="Semua" or t["tipe_pendakian"]==ft)
                and (not fq or fq.lower() in t["nama_trip"].lower() or fq.lower() in t["gunung_tujuan"].lower())]
            st.markdown("<div style='font-size:12px;color:#4a6080;margin-bottom:12px;'>Menampilkan <b style='color:#e2eaf5;'>{}</b> dari {} trip</div>".format(len(filt),len(trips)),unsafe_allow_html=True)
            for t in filt:
                stc={"Perencanaan":"#3b82f6","Aktif":"#22c55e","Selesai":"#06b6d4","Dibatalkan":"#ef4444"}.get(t["status"],"#64748b")
                sbg={"Perencanaan":"rgba(59,130,246,.12)","Aktif":"rgba(34,197,94,.12)","Selesai":"rgba(6,182,212,.12)","Dibatalkan":"rgba(239,68,68,.12)"}.get(t["status"],"rgba(100,116,139,.12)")
                dur=(t["tanggal_kembali"]-t["tanggal_berangkat"]).days+1 if t.get("tanggal_kembali") else "?"
                tbf=t["tanggal_berangkat"].strftime("%d %b %Y") if t.get("tanggal_berangkat") else "—"
                tp_ic="⛺" if t["tipe_pendakian"]=="Camping" else "🏃"
                col_card,col_btn=st.columns([9,1])
                with col_card:
                    st.markdown(
                        "<div style='background:#161e2a;border:1px solid #243044;border-left:4px solid {stc};border-radius:12px;padding:16px 20px;'>"
                        "<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;'>"
                        "<span style='font-size:16px;font-weight:800;color:#e2eaf5;'>{tp_ic} {nm}</span>"
                        "<span style='background:{sbg};color:{stc};border:1px solid {stc}40;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;'>{sts}</span>"
                        "<span style='background:#1c2638;color:#8aa0c0;padding:2px 8px;border-radius:6px;font-size:11px;'>{tp}</span>"
                        "</div>"
                        "<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px;'>"
                        "<div style='background:#1c2638;border-radius:8px;padding:10px 12px;'><div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>📍 Gunung</div><div style='font-size:12px;font-weight:700;color:#e2eaf5;'>{gu}</div></div>"
                        "<div style='background:#1c2638;border-radius:8px;padding:10px 12px;'><div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>📅 Berangkat</div><div style='font-size:12px;font-weight:700;color:#e2eaf5;'>{tb}</div></div>"
                        "<div style='background:#1c2638;border-radius:8px;padding:10px 12px;'><div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>⏱️ Durasi / 👥</div><div style='font-size:12px;font-weight:700;color:#e2eaf5;'>{dur}h · {jml_a}/{jml}org</div></div>"
                        "<div style='background:#1c2638;border-radius:8px;padding:10px 12px;'><div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>💰 Total Biaya</div><div style='font-size:12px;font-weight:700;color:#60a5fa;font-family:IBM Plex Mono,monospace;'>{biaya}</div></div>"
                        "</div>{cat}</div>".format(
                            stc=stc,sbg=sbg,tp_ic=tp_ic,nm=t["nama_trip"],sts=t["status"],tp=t["tipe_pendakian"],
                            gu=t["gunung_tujuan"]+((" / "+t["jalur_pendakian"]) if t.get("jalur_pendakian") else ""),
                            tb=tbf,dur=dur,jml_a=t["jml_anggota"],jml=t["jumlah_orang"],biaya=L.fmt_rp(t["total_biaya"]),
                            cat="<div style='margin-top:10px;font-size:12px;color:#4a6080;'>📝 {}</div>".format(t["catatan"]) if t.get("catatan") else ""),
                        unsafe_allow_html=True)
                with col_btn:
                    st.markdown("<div style='padding-top:14px;display:flex;flex-direction:column;gap:6px;'>",unsafe_allow_html=True)
                    if admin:
                        st.markdown('<div class="btn-warn">',unsafe_allow_html=True)
                        if st.button("✏️",key="et_{}".format(t["id"]),help="Edit trip",use_container_width=True):
                            st.session_state["edit_trip_id"]=t["id"]; st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)
                        confirm_del("trip_{}".format(t["id"]),lambda tid=t["id"]:L.delete_trip(tid),"🗑️","Hapus {}?".format(t["nama_trip"]))
                    st.markdown("</div>",unsafe_allow_html=True)
                st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)

    if admin:
        with tabs[2]:
            trips_all=L.get_trips()
            if not trips_all: alert("Belum ada trip.","info")
            else:
                opts={"{} — {}".format(t["nama_trip"],t["gunung_tujuan"]):t["id"] for t in trips_all}
                def_i=0
                if "edit_trip_id" in st.session_state:
                    ids=list(opts.values())
                    if st.session_state["edit_trip_id"] in ids: def_i=ids.index(st.session_state["edit_trip_id"])
                def _on_tr_sel():
                    pass  # fields auto-reload from selected trip data
                sel=st.selectbox("🔍 Pilih Trip yang akan Diedit",list(opts.keys()),index=def_i,key="edit_trip_sel")
                trip=L.get_trip(opts[sel])
                if trip:
                    stc={"Perencanaan":"#3b82f6","Aktif":"#22c55e","Selesai":"#06b6d4","Dibatalkan":"#ef4444"}.get(trip["status"],"#64748b")
                    st.markdown(
                        "<div style='background:#1c2638;border:1px solid #243044;border-left:4px solid {c};border-radius:12px;padding:14px 18px;margin-bottom:16px;'>"
                        "<div style='font-size:11px;color:#4a6080;margin-bottom:4px;'>Data saat ini:</div>"
                        "<div style='font-size:15px;font-weight:800;color:#e2eaf5;'>⛺ {nm}</div>"
                        "<div style='font-size:12px;color:#8aa0c0;margin-top:4px;'>📍 {gu} · {sts} · {jml} orang</div>"
                        "</div>".format(c=stc,nm=trip["nama_trip"],gu=trip["gunung_tujuan"],sts=trip["status"],jml=trip["jumlah_orang"]),
                        unsafe_allow_html=True)
                    with st.form("trip_edit_{}".format(trip["id"])):
                        sec("📋 Info Dasar")
                        c1,c2,c3=st.columns(3)
                        en=c1.text_input("Nama Trip *",value=trip["nama_trip"])
                        eg=c2.text_input("Gunung Tujuan *",value=trip["gunung_tujuan"])
                        ej=c3.text_input("Jalur Pendakian",value=trip["jalur_pendakian"] or "")
                        sec("⚙️ Status & Konfigurasi")
                        c4,c5,c6=st.columns(3)
                        et=c4.selectbox("Tipe",["Camping","Tektok"],index=["Camping","Tektok"].index(trip["tipe_pendakian"]))
                        es=c5.selectbox("Status",["Perencanaan","Aktif","Selesai","Dibatalkan"],
                            index=["Perencanaan","Aktif","Selesai","Dibatalkan"].index(trip["status"]))
                        eo=c6.number_input("Jumlah Orang",min_value=1,max_value=500,value=trip["jumlah_orang"])
                        sec("📅 Jadwal")
                        c7,c8=st.columns(2)
                        etb=c7.date_input("Tanggal Berangkat",value=trip["tanggal_berangkat"])
                        etk=c8.date_input("Tanggal Kembali",value=trip["tanggal_kembali"] or trip["tanggal_berangkat"])
                        ec=st.text_area("📝 Catatan",value=trip["catatan"] or "",height=68)
                        st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                        if st.form_submit_button("💾 Simpan Perubahan",use_container_width=True):
                            L.update_trip(trip["id"],dict(nama_trip=en,gunung_tujuan=eg,jalur_pendakian=ej,
                                tipe_pendakian=et,status=es,tanggal_berangkat=etb,
                                tanggal_kembali=etk,jumlah_orang=eo,catatan=ec))
                            st.success("✅ Trip **{}** diperbarui!".format(en)); st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)
    _pw_end()

# ═══════════════════════════════════════════════════════════════════════════════
# MEMBER HELPERS (fields inside form)
# ═══════════════════════════════════════════════════════════════════════════════
def _member_fields_inside_form(prefix, d=None):
    d = d or {}
    sec("👤 Identitas Diri")
    c1, c2, c3 = st.columns(3)
    with c1:
        nm  = st.text_input("Nama Lengkap *", value=d.get("nama_lengkap",""), key="{}_nm".format(prefix))
        pg  = st.text_input("Nama Panggilan", value=d.get("nama_panggilan","") or "", key="{}_pg".format(prefix))
        nik = st.text_input("NIK *", value=d.get("nik",""), key="{}_nik".format(prefix), max_chars=16)
    with c2:
        ttl_disp = d.get("tempat_lahir","") or "—"
        st.markdown("<div style='font-size:12px;color:var(--txt2);margin-bottom:2px;'>Tempat Lahir</div>"
                    "<div style='font-size:13px;color:var(--txt);background:var(--raised);"
                    "border:1px solid var(--border);border-radius:9px;padding:8px 12px;margin-bottom:8px;'>"
                    "📍 {}</div>".format(ttl_disp), unsafe_allow_html=True)
        tgl = st.date_input("Tanggal Lahir *", value=d.get("tanggal_lahir", date(1995,1,1)),
                             min_value=date(1900,1,1), key="{}_tgl".format(prefix))
        jk  = st.selectbox("JK *", ["Laki-laki","Perempuan"],
                            index=["Laki-laki","Perempuan"].index(d.get("jenis_kelamin","Laki-laki")),
                            key="{}_jk".format(prefix))
    with c3:
        hp  = st.text_input("No. HP *", value=d.get("no_hp",""), key="{}_hp".format(prefix))
        em  = st.text_input("Email *",  value=d.get("email",""), key="{}_em".format(prefix))
        rp  = st.text_area("Riwayat Penyakit (opsional)", value=d.get("riwayat_penyakit","") or "",
                            height=68, key="{}_rp".format(prefix), placeholder="Asma, alergi, dll.")
    sec("🆘 Kontak Darurat")
    k1, k2, k3 = st.columns(3)
    kdn = k1.text_input("Nama Kontak *", value=d.get("kontak_darurat_nama",""), key="{}_kdn".format(prefix))
    kdh = k2.text_input("HP Kontak *",   value=d.get("kontak_darurat_hp",""),  key="{}_kdh".format(prefix))
    HUB = ["Orang Tua","Saudara","Pasangan","Lainnya"]
    kdr = k3.selectbox("Hubungan *", HUB,
                        index=HUB.index(d.get("kontak_darurat_hubungan","Orang Tua")),
                        key="{}_kdr".format(prefix))
    return dict(nama_lengkap=nm, nama_panggilan=pg or None, nik=nik,
                tanggal_lahir=tgl, jenis_kelamin=jk,
                no_hp=hp, email=em, riwayat_penyakit=rp or None,
                kontak_darurat_nama=kdn, kontak_darurat_hp=kdh, kontak_darurat_hubungan=kdr)

def _val_member(d):
    errs=[]
    for f,l in [("nama_lengkap","Nama Lengkap"),("nik","NIK"),("no_hp","No. HP"),
                ("email","Email"),("kontak_darurat_nama","Kontak Darurat"),
                ("kontak_darurat_hp","HP Kontak"),("alamat_lengkap","Alamat")]:
        if not d.get(f): errs.append("{} wajib diisi".format(l))
    return errs


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ANGGOTA TRIP
# ═══════════════════════════════════════════════════════════════════════════════
def page_members():
    _pw()
    ph("👥","Anggota & Profil","Data lengkap setiap peserta pendakian")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; members=L.get_members(trip_id); n=len(members)
    admin=is_admin_user(); email=get_email()
    full=(n>=trip["jumlah_orang"])
    alert("{}/{} terdaftar {}".format(n,trip["jumlah_orang"],"✅ Kuota penuh!" if full else ""),
          "success" if full else "info")

    # Member hanya melihat Daftar dan Edit (data dirinya saja)
    if admin:
        tabs=st.tabs(["➕ Tambah Manual","📥 Import Master","📋 Daftar","✏️ Edit"])
    else:
        tabs=st.tabs(["📋 Daftar","✏️ Edit Data Saya"])

    tab_offset = 0 if admin else -2  # tab index offset for non-admin

    if admin:
        with tabs[0]:
            _api_status_indicator()
            sec("📍 Tempat Lahir")
            ttl_new=_tempat_lahir_selectbox("mnew","")
            sec("🏠 Domisili")
            wil_new=wilayah_form("mnew")
            al_new=st.text_area("Alamat Lengkap *",height=68,key="mnew_al",placeholder="Jl. ...")
            ct_new=st.text_area("Catatan (opsional)",height=56,key="mnew_ct")
            msep()
            with st.form("mnew",clear_on_submit=True):
                inside=_member_fields_inside_form("mnew")
                if st.form_submit_button("✅ Daftarkan Anggota",use_container_width=True):
                    data=dict(**inside,**wil_new,tempat_lahir=ttl_new or inside.get("tempat_lahir","—"),
                              alamat_lengkap=al_new,catatan=ct_new or None)
                    errs=_val_member(data)
                    if errs:
                        for e in errs: st.error(e)
                    else:
                        L.create_member(trip_id,data)
                        st.success("✅ {} berhasil didaftarkan!".format(data["nama_lengkap"]))
                        for k in [k2 for k2 in st.session_state if k2.startswith("mnew_wil_") or k2.startswith("mnew_ttl")]:
                            del st.session_state[k]
                        st.rerun()

        with tabs[1]:
            all_master=L.get_members_master()
            if not all_master: alert("Master kosong. Tambahkan di Master Anggota.","info")
            else:
                current_ids={m.get("master_anggota_id") for m in L.get_members(trip_id) if m.get("master_anggota_id")}
                available=[ma for ma in all_master if ma["id"] not in current_ids]
                if not available: alert("Semua anggota master sudah terdaftar.","success")
                else:
                    sel_import=st.multiselect("Pilih anggota",[ma["id"] for ma in available],
                        format_func=lambda mid:next("{} ({})".format(ma["nama_lengkap"],ma.get("no_hp","")) for ma in available if ma["id"]==mid),
                        key="import_master_sel")
                    if sel_import:
                        st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                        if st.button("📥 Import {} Anggota".format(len(sel_import))):
                            imported=0
                            for mid in sel_import:
                                ma=next((x for x in available if x["id"]==mid),None)
                                if ma:
                                    data={k:ma.get(k) for k in ["nama_lengkap","nama_panggilan","nik","jenis_kelamin",
                                        "tempat_lahir","tanggal_lahir","no_hp","email","kontak_darurat_nama",
                                        "kontak_darurat_hubungan","kontak_darurat_hp","riwayat_penyakit",
                                        "provinsi_id","kota_id","kecamatan_id","kelurahan_id","alamat_lengkap","catatan"]}
                                    data["master_anggota_id"]=ma["id"]
                                    L.create_member(trip_id,data); imported+=1
                            st.success("✅ {} anggota diimport!".format(imported)); st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)

    # Tab daftar — admin: tabs[2], member: tabs[0]
    daftar_tab = tabs[2] if admin else tabs[0]
    edit_tab   = tabs[3] if admin else tabs[1]

    with daftar_tab:
        if not members: alert("Belum ada anggota.","info")
        else:
            st.markdown("<div style='font-size:12px;color:#4a6080;margin-bottom:12px;'><b style='color:#e2eaf5;'>{}</b> anggota terdaftar dari {} kuota</div>".format(len(members),trip["jumlah_orang"]),unsafe_allow_html=True)
            for m in members:
                usia=L.hitung_usia(m["tanggal_lahir"])
                dom=", ".join(p for p in [m.get("kecamatan_nama"),m.get("kota_nama"),m.get("provinsi_nama")] if p) or "—"
                jk_ic="🧑" if m["jenis_kelamin"]=="Laki-laki" else "👩"
                own=(get_email().lower()==(m.get("email") or "").lower())
                can_edit=is_admin_user() or own

                col_info, col_act = st.columns([9,1])
                with col_info:
                    medis_bar=""
                    if m.get("riwayat_penyakit"):
                        medis_bar="<div style='background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:6px;padding:6px 12px;font-size:11px;color:#fca5a5;margin-top:8px;'>🏥 {}</div>".format(m["riwayat_penyakit"])
                    st.markdown(
                        "<div style='background:#161e2a;border:1px solid #243044;border-left:3px solid #3b82f6;border-radius:12px;padding:14px 18px;'>"
                        "<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>"
                        "<div style='width:38px;height:38px;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;'>{jk}</div>"
                        "<div style='flex:1;'><div style='font-size:15px;font-weight:700;color:#e2eaf5;'>{nm}</div>"
                        "<div style='font-size:11px;color:#4a6080;margin-top:2px;'>@{pan} · {usia}</div></div>"
                        "<div style='text-align:right;font-size:11px;color:#4a6080;'><div>📱 {hp}</div><div>📧 {em}</div></div>"
                        "</div>"
                        "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:11px;'>"
                        "<div style='background:#1c2638;border-radius:8px;padding:8px 10px;'><span style='color:#4a6080;font-size:9px;display:block;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;'>🪪 Identitas</span>"
                        "<span style='color:#8aa0c0;'>NIK: {nik}</span><br><span style='color:#8aa0c0;'>TTL: {ttl}</span></div>"
                        "<div style='background:#1c2638;border-radius:8px;padding:8px 10px;'><span style='color:#4a6080;font-size:9px;display:block;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;'>📞 Kontak Darurat</span>"
                        "<span style='color:#8aa0c0;'>{kdn} ({kdh})</span><br><span style='color:#8aa0c0;'>📱 {kdhp}</span></div>"
                        "<div style='background:#1c2638;border-radius:8px;padding:8px 10px;'><span style='color:#4a6080;font-size:9px;display:block;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;'>🏠 Domisili</span>"
                        "<span style='color:#8aa0c0;'>{dom}</span></div>"
                        "</div>{medis}</div>".format(
                            jk=jk_ic,nm=m["nama_lengkap"],
                            pan=m.get("nama_panggilan") or m["nama_lengkap"].split()[0],
                            usia="{} thn".format(usia) if usia else "—",
                            hp=m.get("no_hp") or "—",em=m.get("email") or "—",
                            nik=m.get("nik") or "—",
                            ttl="{}, {}".format(m.get("tempat_lahir") or "—",str(m["tanggal_lahir"]) if m.get("tanggal_lahir") else ""),
                            kdn=m.get("kontak_darurat_nama") or "—",kdh=m.get("kontak_darurat_hubungan") or "—",
                            kdhp=m.get("kontak_darurat_hp") or "—",dom=dom,medis=medis_bar),
                        unsafe_allow_html=True)
                with col_act:
                    st.markdown("<div style='padding-top:14px;display:flex;flex-direction:column;gap:6px;'>",unsafe_allow_html=True)
                    if can_edit:
                        st.markdown('<div class="btn-warn">',unsafe_allow_html=True)
                        if st.button("✏️",key="em_{}".format(m["id"]),help="Edit anggota ini",use_container_width=True):
                            st.session_state["edit_member_id"]=m["id"]; st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)
                    if is_admin_user():
                        confirm_del("mem_{}".format(m["id"]),lambda mid=m["id"]:L.delete_member(mid),"🗑️","Hapus {}?".format(m["nama_lengkap"]))
                    st.markdown("</div>",unsafe_allow_html=True)
                st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)

    with edit_tab:
        members2=L.get_members(trip_id)
        if not members2: alert("Belum ada anggota.","info")
        else:
            # Member hanya bisa edit data dirinya; admin bisa pilih siapa saja
            if admin:
                opts={m["nama_lengkap"]:m["id"] for m in members2}
                di=0
                if "edit_member_id" in st.session_state:
                    ids=list(opts.values())
                    if st.session_state["edit_member_id"] in ids: di=ids.index(st.session_state["edit_member_id"])
                def _on_mem_sel():
                    to_del=[k for k in st.session_state if
                        (k.startswith("medit_") and k!="medit_sel") or
                        k.startswith("_wil_medit")]
                    for k in to_del: del st.session_state[k]
                sel=st.selectbox("🔍 Pilih Anggota yang akan Diedit",list(opts.keys()),index=di,key="medit_sel",on_change=_on_mem_sel)
                selected_mid=opts[sel]
            else:
                # Member: cari data dirinya berdasarkan email
                my_member=next((m for m in members2 if (m.get("email") or "").lower()==email.lower()),None)
                if not my_member:
                    alert("Data Anda tidak ditemukan di trip ini. Pastikan email sesuai dengan yang didaftarkan admin.","warning")
                    _pw_end(); return
                selected_mid=my_member["id"]
            m=L.get_member(selected_mid)
            if m:
                mk=str(m["id"])  # member key for unique widget IDs
                jk_ic2="🧑" if m["jenis_kelamin"]=="Laki-laki" else "👩"
                usia2=L.hitung_usia(m["tanggal_lahir"])

                st.markdown(
                    "<div style='background:#1c2638;border:1px solid #243044;border-left:4px solid #3b82f6;"
                    "border-radius:12px;padding:14px 18px;margin-bottom:16px;'>"
                    "<div style='font-size:11px;color:#4a6080;margin-bottom:6px;'>✏️ Mengedit data anggota:</div>"
                    "<div style='display:flex;align-items:center;gap:12px;'>"
                    "<span style='font-size:28px;'>{jk}</span>"
                    "<div><div style='font-size:15px;font-weight:800;color:#e2eaf5;'>{nm}</div>"
                    "<div style='font-size:12px;color:#8aa0c0;margin-top:3px;'>NIK: {nik} · {usia} · 📱 {hp}</div>"
                    "</div></div></div>".format(
                        jk=jk_ic2,nm=m["nama_lengkap"],
                        nik=m.get("nik") or "—",usia=usia2 or "—",hp=m.get("no_hp") or "—"),
                    unsafe_allow_html=True)
                pfx="medit_{}".format(mk)
                sec("📍 Tempat Lahir")
                ttl_edit=_tempat_lahir_selectbox(pfx, m.get("tempat_lahir",""))
                sec("🏠 Domisili")
                wil_edit=wilayah_form(pfx, m)
                al_edit=st.text_area("Alamat Lengkap *",value=m.get("alamat_lengkap","") or "",height=68,key="{}_al".format(pfx))
                ct_edit=st.text_area("Catatan",value=m.get("catatan","") or "",height=56,key="{}_ct".format(pfx))
                msep()
                # Use member-ID-specific form key so widgets always show correct data
                with st.form("medit_form_{}".format(mk)):
                    sec("👤 Identitas Diri")
                    c1,c2,c3=st.columns(3)
                    nm_e=c1.text_input("Nama Lengkap *",value=m.get("nama_lengkap",""),key="ef_nm_{}".format(mk))
                    pg_e=c1.text_input("Nama Panggilan",value=m.get("nama_panggilan","") or "",key="ef_pg_{}".format(mk))
                    nik_e=c1.text_input("NIK *",value=m.get("nik","") or "",max_chars=16,key="ef_nik_{}".format(mk))
                    tgl_e=c2.date_input("Tanggal Lahir *",value=m.get("tanggal_lahir",date(1995,1,1)),min_value=date(1900,1,1),key="ef_tgl_{}".format(mk))
                    jk_e=c2.selectbox("Jenis Kelamin *",["Laki-laki","Perempuan"],
                        index=["Laki-laki","Perempuan"].index(m.get("jenis_kelamin","Laki-laki")),key="ef_jk_{}".format(mk))
                    hp_e=c3.text_input("No. HP *",value=m.get("no_hp","") or "",key="ef_hp_{}".format(mk))
                    em_e=c3.text_input("Email *",value=m.get("email","") or "",key="ef_em_{}".format(mk))
                    rp_e=c3.text_area("Riwayat Penyakit",value=m.get("riwayat_penyakit","") or "",height=68,key="ef_rp_{}".format(mk))
                    sec("🆘 Kontak Darurat")
                    k1,k2,k3=st.columns(3)
                    HUB=["Orang Tua","Saudara","Pasangan","Teman","Lainnya"]
                    kdn_e=k1.text_input("Nama Kontak *",value=m.get("kontak_darurat_nama","") or "",key="ef_kdn_{}".format(mk))
                    kdh_e=k2.text_input("HP Kontak *",value=m.get("kontak_darurat_hp","") or "",key="ef_kdh_{}".format(mk))
                    hub_cur=m.get("kontak_darurat_hubungan","Orang Tua")
                    kdr_e=k3.selectbox("Hubungan",HUB,index=HUB.index(hub_cur) if hub_cur in HUB else 0,key="ef_hub_{}".format(mk))
                    st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                    if st.form_submit_button("💾 Simpan Perubahan",use_container_width=True):
                        if not nm_e or not nik_e or not hp_e:
                            st.error("Nama, NIK, dan No. HP wajib diisi!")
                        else:
                            data=dict(nama_lengkap=nm_e,nama_panggilan=pg_e or None,nik=nik_e,
                                tanggal_lahir=tgl_e,jenis_kelamin=jk_e,no_hp=hp_e,email=em_e,
                                riwayat_penyakit=rp_e or None,kontak_darurat_nama=kdn_e,
                                kontak_darurat_hp=kdh_e,kontak_darurat_hubungan=kdr_e,
                                **wil_edit,
                                tempat_lahir=ttl_edit or m.get("tempat_lahir","—"),
                                alamat_lengkap=al_edit,catatan=ct_edit or None)
                            L.update_member(m["id"],data)
                            st.success("✅ **{}** berhasil diperbarui!".format(nm_e))
                            st.session_state.pop("edit_member_id",None)
                            st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: INPUT BIAYA
# ═══════════════════════════════════════════════════════════════════════════════
def page_biaya():
    _pw()
    if not is_admin_user(): alert("🔒 Hanya admin.","warning"); _pw_end(); return
    ph("💰","Input Biaya & Perlengkapan","Item berbayar — Beli atau Sewa")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; jml=trip["jumlah_orang"]
    members=L.get_members(trip_id); cats=L.get_categories()
    cat_opts={"{} {}".format(c["icon"],c["nama_kategori"]):c for c in cats}
    m_opts={m["nama_lengkap"]:m["id"] for m in members}
    admin=is_admin_user()

    tabs=st.tabs(["➕ Tambah Item","📋 Daftar Item","✏️ Edit Item"])

    with tabs[0]:
        all_masters=L.get_items_master()
        master_names=["— Input Manual —"]+["{} {}".format(im.get("icon","📦"),im["nama_item"]) for im in all_masters]
        def _on_master_change():
            sel = st.session_state.get("bi_master_sel","— Input Manual —")
            if sel != "— Input Manual —":
                idx = master_names.index(sel) - 1
                ref = all_masters[idx]
                st.session_state["bi_af_nama"]   = ref.get("nama_item","")
                st.session_state["bi_af_berat"]  = float(ref.get("berat_gram") or 0)
                st.session_state["bi_af_satuan"] = ref.get("satuan","pcs") or "pcs"
                st.session_state["bi_af_cat"]    = ref.get("nama_kategori","")
            else:
                for k in ["bi_af_nama","bi_af_berat","bi_af_satuan","bi_af_cat"]:
                    st.session_state.pop(k, None)

        sel_master=st.selectbox("📦 Pilih dari Item Master (opsional)",master_names,
            key="bi_master_sel", on_change=_on_master_change)
        master_ref=None
        if sel_master!="— Input Manual —":
            master_ref=all_masters[master_names.index(sel_master)-1]
        msep()

        af_nama   = st.session_state.get("bi_af_nama",   master_ref["nama_item"] if master_ref else "")
        af_berat  = st.session_state.get("bi_af_berat",  float(master_ref["berat_gram"]) if master_ref and master_ref.get("berat_gram") else 0.0)
        af_satuan = st.session_state.get("bi_af_satuan", master_ref.get("satuan","pcs") if master_ref else "pcs")
        af_cat    = st.session_state.get("bi_af_cat",    master_ref.get("nama_kategori","") if master_ref else "")

        cl,cr=st.columns([3,2])
        with cl:
            sec("📦 Detail Item")
            nama_i=st.text_input("Nama Item *",value=af_nama,
                placeholder="cth: Sewa Jaket, Simaksi...",key="bi_nama_i")
            cat_keys=list(cat_opts.keys())
            cat_idx=next((i for i,k in enumerate(cat_keys) if af_cat and af_cat.lower() in k.lower()),0)
            cat_k=st.selectbox("Kategori",cat_keys,index=cat_idx,key="bi_cat_k")
            jp=st.selectbox("Jenis Pengadaan",["Beli","Sewa","DP (Uang Muka)","Dimiliki"],key="bi_jp")
            tgl_mulai=None; dur_hari=1; nominal_dp=0.0
            if jp=="Sewa":
                sec("📅 Info Sewa")
                ss1,ss2=st.columns(2)
                tgl_mulai=ss1.date_input("Mulai Sewa",value=trip["tanggal_berangkat"],key="bi_tgls")
                dur_default=max(1,(trip["tanggal_kembali"]-trip["tanggal_berangkat"]).days+1) if trip.get("tanggal_kembali") else 1
                dur_hari=ss2.number_input("Durasi (hari)",min_value=1,value=dur_default,key="bi_dur")
                alert("📅 Selesai: <b>{}</b>".format((tgl_mulai+timedelta(days=int(dur_hari)-1)).strftime("%d %b %Y")),"info")
            elif jp=="DP (Uang Muka)":
                sec("💵 Info DP")
                nominal_dp=st.number_input("Nominal DP (Rp) *",min_value=0.0,value=0.0,step=10000.0,key="bi_dp")
            sec("📊 Harga & Jumlah")
            hc1,hc2,hc3=st.columns(3)
            harga_lbl="Harga Satuan (Rp)" if jp!="Dimiliki" else "Harga (0 jika dimiliki)"
            harga=hc1.number_input(harga_lbl,min_value=0.0,value=0.0,step=500.0,key="bi_harga")
            jumlah=hc2.number_input("Jumlah",min_value=0.01,value=1.0,step=0.5,key="bi_jml")
            satuan=hc3.text_input("Satuan",value=af_satuan,key="bi_satuan")
            sec("⚖️ Berat")
            bw1,bw2=st.columns(2)
            berat_val=bw1.number_input("Berat per unit",min_value=0.0,value=af_berat,step=0.1,key="bi_berat_val")
            berat_sat=bw2.selectbox("Satuan berat",["gram","kg","liter","ml","oz","lb"],key="bi_berat_sat")
            berat_gram_conv=L.to_gram(berat_val,berat_sat)
            if berat_val>0: st.caption("≈ {:.0f} gram/unit".format(berat_gram_conv))
            catatan=st.text_input("Catatan (opsional)",key="bi_catatan")

        with cr:
            sec("👥 Scope & Tanggungan")
            scope=st.radio("Scope Biaya",["Kelompok","Personal"],key="bi_scope",
                help="Kelompok=dibagi rata semua. Personal=hanya anggota terpilih.")
            assigned_ids=[]; personal_semua=False
            if scope=="Personal":
                if members:
                    personal_semua=st.checkbox("Berlaku ke SEMUA anggota",key="bi_ps")
                    if not personal_semua:
                        sel_names=st.multiselect("Anggota yang kena biaya *",list(m_opts.keys()),key="bi_asgn")
                        assigned_ids=[m_opts[n] for n in sel_names]
                else: alert("Tambahkan anggota dulu.","warning")
            tang_opts={"— Tidak ada —":None}
            tang_opts.update({m["nama_lengkap"]:m["id"] for m in members})
            pt=st.selectbox("Dibayarkan duluan oleh",list(tang_opts.keys()),key="bi_tang")
            pid=tang_opts[pt]

            # Preview kalkulasi
            harga_eff=nominal_dp if jp=="DP (Uang Muka)" and nominal_dp>0 else harga
            subtotal=harga_eff*jumlah
            berat_total=berat_gram_conv*jumlah

            if scope=="Kelompok":
                n_eff=max(jml,1)
                per_o=subtotal/n_eff
                scope_note="÷ {} orang (kelompok) = <b>{}</b>/orang".format(n_eff, L.fmt_rp(per_o))
                preview_label="Per Orang (Kelompok)"
                preview_amount=L.fmt_rp(per_o)
            else:
                # PERSONAL: setiap anggota yg dipilih MENANGGUNG PENUH subtotal ini
                # subtotal TIDAK dibagi jumlah anggota kelompok/trip
                if personal_semua:
                    n_asgn=max(len(members),1)
                    asgn_label="Semua {} anggota".format(n_asgn)
                elif assigned_ids:
                    n_asgn=len(assigned_ids)
                    asgn_label="{} anggota dipilih".format(n_asgn)
                else:
                    n_asgn=0
                    asgn_label="Belum ada anggota dipilih"
                # Masing-masing orang MENANGGUNG penuh subtotal ini (bukan dibagi)
                per_o=subtotal  # tiap orang bayar subtotal penuh
                scope_note="Setiap orang dari <b>{}</b> menanggung <b>{}</b> masing-masing".format(asgn_label, L.fmt_rp(subtotal))
                preview_label="Per Orang (Personal)"
                preview_amount=L.fmt_rp(subtotal)
                n_eff=n_asgn

            per_g=berat_total/max(n_eff,1) if berat_total>0 and n_eff>0 else berat_total

            msep()
            dp_note=""
            if jp=="DP (Uang Muka)": dp_note="<div style='font-size:12px;color:#8aa0c0;margin-top:4px;'>DP dari harga penuh {}</div>".format(L.fmt_rp(harga*jumlah))
            berat_note=""
            if berat_total>0: berat_note="<div style='font-size:12px;color:#8aa0c0;margin-top:4px;'>🎒 {} total berat</div>".format(L.fmt_berat(berat_total))

            sc_bg="rgba(59,130,246,.06)" if scope=="Kelompok" else "rgba(168,85,247,.06)"
            sc_bd="rgba(59,130,246,.25)" if scope=="Kelompok" else "rgba(168,85,247,.25)"
            sc_col="#93c5fd" if scope=="Kelompok" else "#d8b4fe"
            sc_badge="<span style='background:{bg};color:{c};border:1px solid {bd};padding:2px 10px;border-radius:20px;font-size:10px;font-weight:700;margin-bottom:8px;display:inline-block;'>{sc}</span>".format(
                bg=sc_bg.replace("06","15"),bd=sc_bd,c=sc_col,sc=scope)
            lbl_txt="(DP)" if jp=="DP (Uang Muka)" else ""
            st.markdown(
                "<div style='background:{bg};border:1px solid {bd};border-radius:14px;padding:20px;text-align:center;'>"
                "{sc}<br>"
                "<div style='font-family:IBM Plex Mono,monospace;font-size:10px;font-weight:500;letter-spacing:2px;text-transform:uppercase;color:#4a6080;margin-top:6px;'>Subtotal {lbl}</div>"
                "<div style='font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:600;color:#60a5fa;margin-top:6px;'>{sub}</div>"
                "<div style='font-size:12px;color:#8aa0c0;margin-top:6px;'>{sn}</div>"
                "{dp}{brt}"
                "</div>".format(bg=sc_bg, bd=sc_bd, sc=sc_badge, lbl=lbl_txt,
                                sub=L.fmt_rp(subtotal), sn=scope_note, dp=dp_note, brt=berat_note),
                unsafe_allow_html=True)

            st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)
            st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
            if st.button("✅ Tambah ke Trip",use_container_width=True,key="bi_submit"):
                err=None
                if not nama_i: err="Nama item wajib!"
                elif jp!="Dimiliki" and harga<=0: err="Harga harus > 0!"
                elif jp=="DP (Uang Muka)" and nominal_dp<=0: err="Nominal DP harus > 0!"
                elif scope=="Personal" and not personal_semua and not assigned_ids: err="Pilih minimal 1 anggota!"
                if err: st.error(err)
                else:
                    harga_save=nominal_dp if jp=="DP (Uang Muka)" and nominal_dp>0 else harga
                    jp_save=jp.replace(" (Uang Muka)","")
                    L.create_trip_item(trip_id,dict(
                        nama_item=nama_i,category_id=cat_opts[cat_k]["id"],
                        jenis_pengadaan=jp_save,tanggal_sewa_mulai=tgl_mulai,durasi_sewa_hari=dur_hari,
                        jumlah=jumlah,satuan=satuan,harga_satuan=harga_save,
                        berat_gram=berat_gram_conv,berat_satuan="gram",
                        tipe_scope=scope,personal_semua=bool(personal_semua),
                        ditanggung_member_id=pid,catatan=catatan or None),assigned_ids)
                    if scope=="Personal":
                        n_info=len(assigned_ids) if not personal_semua else len(members)
                        st.success("✅ {} ditambahkan! Setiap dari {} orang menanggung {} masing-masing.".format(
                            nama_i, n_info, L.fmt_rp(subtotal)))
                    else:
                        st.success("✅ {} ditambahkan! Subtotal: {} ({}/org dari {} orang)".format(
                            nama_i, L.fmt_rp(subtotal), L.fmt_rp(subtotal/max(jml,1)), jml))
                    st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

    with tabs[1]:
        items=L.get_trip_items(trip_id,jml)
        if not items: alert("Belum ada item.","info")
        else:
            tk=sum(float(i["subtotal"]) for i in items if i["tipe_scope"]=="Kelompok")
            tp=sum(float(i["subtotal"]) for i in items if i["tipe_scope"]=="Personal")
            mc1,mc2,mc3=st.columns(3)
            mc1.metric("🏕️ Kelompok",L.fmt_rp(tk))
            mc2.metric("👤 Personal",L.fmt_rp(tp))
            mc3.metric("💰 Total",L.fmt_rp(tk+tp))
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            fc1,fc2,fc3=st.columns(3)
            fs=fc1.selectbox("Scope",["Semua","Kelompok","Personal"],key="bi_fs")
            fj=fc2.selectbox("Jenis",["Semua","Beli","Sewa","DP","Dimiliki"],key="bi_fj")
            fq=fc3.text_input("🔍 Cari","",key="bi_fq",placeholder="Nama item...")
            filtered=items
            if fs!="Semua": filtered=[i for i in filtered if i["tipe_scope"]==fs]
            if fj!="Semua": filtered=[i for i in filtered if i["jenis_pengadaan"]==fj]
            if fq: filtered=[i for i in filtered if fq.lower() in i["nama_item"].lower()]
            by_cat={}
            for item in filtered:
                k=(item.get("icon","📦"),item.get("nama_kategori","?"))
                by_cat.setdefault(k,[]).append(item)
            for (icon,cat_name),citems in sorted(by_cat.items()):
                ct=sum(float(i["subtotal"]) for i in citems)
                with st.expander("{} {}  ·  {} item  ·  {}".format(icon,cat_name,len(citems),L.fmt_rp(ct))):
                    for item in citems:
                        assigned=item.get("assigned_members",[])
                        names=[m.get("nama_panggilan") or m["nama_lengkap"].split()[0] for m in assigned]
                        assig_str=", ".join(names) if names else ("Semua ({} org)".format(jml) if item["tipe_scope"]=="Kelompok" else "?")
                        scope_c="blue" if item["tipe_scope"]=="Kelompok" else "purple"
                        jenis_c={"Beli":"green","Sewa":"orange","DP":"yellow","Dimiliki":"gray"}.get(item["jenis_pengadaan"],"gray")
                        tang_str=" · 💼 {}".format(item["penanggung_nama"]) if item.get("penanggung_nama") else ""
                        per_lbl="Per org" if item["tipe_scope"]=="Kelompok" else "Per orang (full)"
                        col_a,col_b,col_c=st.columns([5,3,1])
                        with col_a:
                            st.markdown(
                                "<div style='background:#1c2638;border:1px solid #243044;border-left:3px solid #3b82f6;"
                                "border-radius:10px;padding:10px 14px;'>"
                                "<div style='font-size:13px;font-weight:700;color:#e2eaf5;margin-bottom:6px;'>{nm}</div>"
                                "<div style='display:flex;gap:6px;align-items:center;flex-wrap:wrap;'>"
                                "{sc} {jn}"
                                "<span style='font-size:11px;color:#8aa0c0;'>👥 {ag}{tang}</span>"
                                "</div>"
                                "{ct}"
                                "</div>".format(
                                    nm=item["nama_item"],
                                    sc=badge(item["tipe_scope"],scope_c),
                                    jn=badge(item["jenis_pengadaan"],jenis_c),
                                    ag=assig_str, tang=tang_str,
                                    ct="<div style='font-size:11px;color:#4a6080;margin-top:5px;'>📝 {}</div>".format(item["catatan"]) if item.get("catatan") else ""),
                                unsafe_allow_html=True)
                        with col_b:
                            st.markdown(
                                "<div style='background:#1c2638;border:1px solid #243044;border-radius:10px;"
                                "padding:10px 14px;text-align:right;height:100%;'>"
                                "<div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;'>Qty × Harga</div>"
                                "<div style='font-size:12px;color:#8aa0c0;margin-top:2px;font-family:IBM Plex Mono,monospace;'>{qty} {sat} × {hrg}</div>"
                                "<div style='height:6px;background:#243044;border-radius:2px;margin:8px 0;'></div>"
                                "<div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;'>Subtotal · {pl}</div>"
                                "<div style='font-size:17px;font-weight:700;color:#60a5fa;font-family:IBM Plex Mono,monospace;margin-top:2px;'>{sub}</div>"
                                "<div style='font-size:11px;color:#4a6080;font-family:IBM Plex Mono,monospace;'>{po}</div>"
                                "</div>".format(
                                    qty=float(item["jumlah"]),sat=item["satuan"],
                                    hrg=L.fmt_rp(item["harga_satuan"]),pl=per_lbl,
                                    sub=L.fmt_rp(item["subtotal"]),po=L.fmt_rp(item["per_orang_rp"])),
                                unsafe_allow_html=True)
                        with col_c:
                            st.markdown("<div style='padding-top:8px;'>",unsafe_allow_html=True)
                            if admin:
                                confirm_del("ti_{}".format(item["id"]),lambda iid=item["id"]:L.delete_trip_item(iid),"🗑️","Hapus {}?".format(item["nama_item"]))
                            st.markdown("</div>",unsafe_allow_html=True)
                        st.markdown("<div style='height:4px'></div>",unsafe_allow_html=True)

    with tabs[2]:
        items2=L.get_trip_items(trip_id,jml)
        if not items2: alert("Belum ada item.","info")
        else:
            def _sub(i): return float(i.get("subtotal") or 0) or float(i.get("harga_satuan",0) or 0)*float(i.get("jumlah",1) or 1)
            i_opts={"{} — {} — {}".format(i["nama_item"],i.get("nama_kategori","?"),L.fmt_rp(_sub(i))):i["id"] for i in items2}
            def _on_ti_change():
                for k in [k2 for k2 in st.session_state if k2.startswith("tie_")]: del st.session_state[k]
            sel_e=st.selectbox("🔍 Pilih Item yang akan Diedit",list(i_opts.keys()),key="ti_edit_sel",on_change=_on_ti_change)
            ti=L.get_trip_item(i_opts[sel_e])
            if ti:
                if "subtotal" not in ti or ti["subtotal"] is None:
                    ti["subtotal"]=float(ti.get("harga_satuan",0) or 0)*float(ti.get("jumlah",1) or 1)
                # Preview data saat ini
                sc_now_c="#3b82f6" if ti["tipe_scope"]=="Kelompok" else "#a855f7"
                jenis_ic={"Beli":"🛒","Sewa":"📅","DP":"💵","Dimiliki":"✅"}.get(ti["jenis_pengadaan"],"📦")
                st.markdown(
                    "<div style='background:#1c2638;border:1px solid #243044;border-left:4px solid {c};"
                    "border-radius:12px;padding:14px 18px;margin-bottom:16px;'>"
                    "<div style='font-size:11px;color:#4a6080;margin-bottom:6px;'>Item saat ini:</div>"
                    "<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;'>"
                    "<span style='font-size:24px;'>{ic}</span>"
                    "<div><div style='font-size:15px;font-weight:800;color:#e2eaf5;'>{nm}</div>"
                    "<div style='font-size:12px;color:#8aa0c0;margin-top:3px;'>{sc} · {jn} · {sub} · {qty} {sat}</div>"
                    "</div></div></div>".format(
                        c=sc_now_c, ic=jenis_ic,
                        nm=ti["nama_item"], sc=ti["tipe_scope"], jn=ti["jenis_pengadaan"],
                        sub=L.fmt_rp(ti["subtotal"]),
                        qty=float(ti["jumlah"]), sat=ti["satuan"]),
                    unsafe_allow_html=True)

                with st.form("ti_edit_{}".format(ti["id"])):
                    sec("📦 Detail Item")
                    c1,c2,c3=st.columns(3)
                    en=c1.text_input("Nama Item",value=ti["nama_item"])
                    cat_list=list(cat_opts.keys()); cat_ids=[cat_opts[k]["id"] for k in cat_list]
                    ci=cat_ids.index(ti["category_id"]) if ti.get("category_id") in cat_ids else 0
                    ec=c2.selectbox("Kategori",cat_list,index=ci)
                    jp_opts=["Beli","Sewa","DP","Dimiliki"]
                    ejp=c3.selectbox("Jenis",jp_opts,index=jp_opts.index(ti["jenis_pengadaan"]) if ti["jenis_pengadaan"] in jp_opts else 0)
                    etm,ed=None,1
                    if ejp=="Sewa":
                        sec("📅 Info Sewa")
                        es1,es2=st.columns(2)
                        etm=es1.date_input("Mulai Sewa",value=ti.get("tanggal_sewa_mulai") or date.today())
                        ed=es2.number_input("Durasi (hari)",min_value=1,value=ti.get("durasi_sewa_hari") or 1)
                    sec("💰 Harga & Jumlah")
                    h1,h2,h3,h4=st.columns(4)
                    eh=h1.number_input("Harga Satuan (Rp)",value=float(ti["harga_satuan"]),step=500.0)
                    ej2=h2.number_input("Jumlah",value=float(ti["jumlah"]),step=0.5)
                    es_=h3.text_input("Satuan",value=ti["satuan"] or "pcs")
                    eb=h4.number_input("Berat/unit (gram)",value=float(ti.get("berat_gram") or 0))
                    sec("👥 Scope & Penanggungan")
                    esc=st.radio("Scope Biaya",["Kelompok","Personal"],
                        index=["Kelompok","Personal"].index(ti["tipe_scope"]),horizontal=True)
                    e_ps,e_aid=False,[]
                    if esc=="Personal" and members:
                        e_ps=st.checkbox("Berlaku ke semua anggota",value=bool(ti.get("personal_semua")))
                        if not e_ps:
                            cur_ids=ti.get("assigned_member_ids",[])
                            cur_nm=[n for n,mid in m_opts.items() if mid in cur_ids]
                            sel_nm=st.multiselect("Anggota yang kena biaya",list(m_opts.keys()),default=cur_nm)
                            e_aid=[m_opts[n] for n in sel_nm]
                    tang2={"— Tidak ada —":None}
                    tang2.update({m["nama_lengkap"]:m["id"] for m in members})
                    curpt=next((k for k,v in tang2.items() if v==ti.get("ditanggung_member_id")),"— Tidak ada —")
                    ept=st.selectbox("Ditanggung / dibayarkan oleh",list(tang2.keys()),
                        index=list(tang2.keys()).index(curpt) if curpt in tang2 else 0)
                    ect=st.text_input("Catatan (opsional)",value=ti.get("catatan") or "")
                    st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                    if st.form_submit_button("💾 Simpan Perubahan",use_container_width=True):
                        L.update_trip_item(ti["id"],trip_id,dict(
                            nama_item=en,category_id=cat_opts[ec]["id"],
                            jenis_pengadaan=ejp,tanggal_sewa_mulai=etm,durasi_sewa_hari=ed,
                            jumlah=ej2,satuan=es_,harga_satuan=eh,berat_gram=eb,
                            tipe_scope=esc,personal_semua=bool(e_ps),
                            ditanggung_member_id=tang2[ept],catatan=ect),e_aid)
                        st.success("✅ **{}** berhasil diperbarui!".format(en)); st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)
    _pw_end()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: REKAP
# ═══════════════════════════════════════════════════════════════════════════════
def page_rekap():
    _pw()
    ph("📊","Rekap & Kalkulasi Biaya","Tagihan, tanggungan, saldo per anggota")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; jml=trip["jumlah_orang"]
    summary=L.calc_trip_summary(trip_id,jml)
    items=summary["items"]; members=summary["members"]
    admin=is_admin_user(); email=get_email()
    if not items: alert("Belum ada data biaya. Tambahkan di Input Biaya.","info"); _pw_end(); return

    paid_all_rekap=L.get_paid_all(trip_id)
    tagihan=summary["tagihan"]; menanggung=summary["menanggung"]
    net_tagihan=summary.get("net_tagihan",{m["id"]:tagihan.get(m["id"],0)-menanggung.get(m["id"],0) for m in members})

    # Identifikasi member saat ini
    my_member=next((m for m in members if (m.get("email") or "").lower()==email.lower()),None)
    my_mid=my_member["id"] if my_member else None

    if admin:
        # Admin: Kelompok = total, Personal = total semua × assigned, Per Orang = kelompok/jml, Grand = tagihan semua orang
        total_personal_admin=sum(
            float(i.get("subtotal") or 0)*len(i.get("assigned_members",[]))
            for i in items if i["tipe_scope"]=="Personal"
        )
        grand_admin=summary["total_kelompok"]+total_personal_admin
        c1,c2,c3,c4=st.columns(4)
        c1.metric("🏕️ Kelompok (total)",L.fmt_rp(summary["total_kelompok"]))
        c2.metric("👤 Personal (total semua)",L.fmt_rp(total_personal_admin))
        c3.metric("➗ Per Orang (kelompok)",L.fmt_rp(summary["per_orang_kelompok"]))
        c4.metric("💰 Grand Total",L.fmt_rp(grand_admin))
    else:
        # Member: Grand Total = tagihan dirinya (kelompok/jml + personal sendiri)
        if my_mid:
            my_tag=tagihan.get(my_mid,0)
            my_mng=menanggung.get(my_mid,0)
            my_net=net_tagihan.get(my_mid,my_tag-my_mng)
            my_paid=paid_all_rekap.get(my_mid,0)
            my_personal=sum(float(i.get("per_orang_rp") or 0) for i in items
                           if i["tipe_scope"]=="Personal" and any(a["id"]==my_mid for a in i.get("assigned_members",[])))
            c1,c2,c3,c4=st.columns(4)
            c1.metric("🏕️ Porsi Kelompok",L.fmt_rp(summary["per_orang_kelompok"]))
            c2.metric("👤 Personal Saya",L.fmt_rp(my_personal))
            c3.metric("💰 Total Tagihan Saya",L.fmt_rp(my_tag))
            c4.metric("✅ Sudah Bayar",L.fmt_rp(my_paid+my_mng),
                     delta="Sisa: {}".format(L.fmt_rp(max(0,my_net-my_paid))),
                     delta_color="inverse" if my_net>my_paid else "normal")
        else:
            alert("Data anggota Anda tidak ditemukan. Pastikan email sesuai dengan yang didaftarkan.","warning")
    msep()

    tabs=st.tabs(["👥 Per Anggota","📂 Per Kategori","📊 Ringkasan","📥 Export"])

    with tabs[0]:
        if not members:
            est=summary["grand_total"]/jml if jml else 0
            st.markdown("<div class='stat-box'><div class='stat-lbl'>Est. per Orang</div><div class='stat-val'>{}</div></div>".format(L.fmt_rp(est)),unsafe_allow_html=True)
            _pw_end(); return
        alert("💡 <b>Net = Tagihan − Menanggung</b>. Net positif → bayar ke kas. Net negatif → piutang dari kas.","info")
        co1,co2=st.columns(2)
        show_cat=co1.checkbox("📂 Breakdown per kategori",value=True,key="rk_sc")
        show_kel=co2.checkbox("🏕️ Tampilkan item kelompok",value=True,key="rk_sk")

        # Member hanya melihat datanya sendiri; admin lihat semua
        members_to_show=members if admin else ([my_member] if my_member else [])

        for idx_m,m in enumerate(members_to_show):
            mid=m["id"]; tag=tagihan.get(mid,0); mng=menanggung.get(mid,0)
            net=net_tagihan.get(mid,tag-mng); paid=paid_all_rekap.get(mid,0)
            p_items=[i for i in items if i["tipe_scope"]=="Personal" and any(a["id"]==mid for a in i.get("assigned_members",[]))]
            k_items=[i for i in items if i["tipe_scope"]=="Kelompok"]

            p_total=sum(float(i["per_orang_rp"]) for i in p_items)
            k_share=summary["per_orang_kelompok"]
            if net>0:
                sisa_net=net-paid; pct=min(100,int(paid/net*100)) if net>0 else 100
                if sisa_net<=0: ac="#22c55e"; st_ic="✅"; st_txt="LUNAS"; sv=L.fmt_rp(0); sv_lbl="Sisa hutang"
                elif paid>0:    ac="#f59e0b"; st_ic="⏳"; st_txt="KURANG BAYAR"; sv=L.fmt_rp(max(0,sisa_net)); sv_lbl="Sisa ke kas"
                else:           ac="#ef4444"; st_ic="❗"; st_txt="BELUM BAYAR"; sv=L.fmt_rp(max(0,sisa_net)); sv_lbl="Harus setor ke kas"
            else:
                pct=100; ac="#06b6d4"; st_ic="💚"; st_txt="PIUTANG"; sv=L.fmt_rp(abs(net)); sv_lbl="Kas/grup berhutang kepadanya"

            pan=m.get("nama_panggilan") or m["nama_lengkap"].split()[0]
            jk_ic3="🧑" if m.get("jenis_kelamin")=="Laki-laki" else "👩"

            # Build detail rows for the breakdown table
            rows_html=""
            if k_share>0:
                rows_html+=(
                    "<div style='display:flex;justify-content:space-between;align-items:center;"
                    "padding:8px 0;border-bottom:1px solid #243044;'>"
                    "<span style='font-size:12px;color:#8aa0c0;'>🏕️ Kelompok (porsi)</span>"
                    "<span style='font-family:IBM Plex Mono,monospace;font-size:12px;color:#8aa0c0;'>{}</span>"
                    "</div>".format(L.fmt_rp(k_share)))
            if p_total>0:
                rows_html+=(
                    "<div style='display:flex;justify-content:space-between;align-items:center;"
                    "padding:8px 0;border-bottom:1px solid #243044;'>"
                    "<span style='font-size:12px;color:#8aa0c0;'>👤 Personal</span>"
                    "<span style='font-family:IBM Plex Mono,monospace;font-size:12px;color:#8aa0c0;'>{}</span>"
                    "</div>".format(L.fmt_rp(p_total)))
            rows_html+=(
                "<div style='display:flex;justify-content:space-between;align-items:center;"
                "padding:9px 0;border-bottom:1px solid #2e3f58;'>"
                "<span style='font-size:13px;font-weight:700;color:#e2eaf5;'>Total Tagihan</span>"
                "<span style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:700;color:#e2eaf5;'>{}</span>"
                "</div>".format(L.fmt_rp(tag)))
            if mng>0:
                net_col="#22c55e" if net<=0 else "#ef4444"
                rows_html+=(
                    "<div style='display:flex;justify-content:space-between;align-items:center;"
                    "padding:8px 0;border-bottom:1px solid #243044;'>"
                    "<span style='font-size:12px;color:#f59e0b;'>💼 Menanggung (sudah keluar)</span>"
                    "<span style='font-family:IBM Plex Mono,monospace;font-size:12px;color:#f59e0b;font-weight:700;'>− {}</span>"
                    "</div>"
                    "<div style='display:flex;justify-content:space-between;align-items:center;"
                    "padding:9px 0;border-bottom:1px solid #2e3f58;'>"
                    "<span style='font-size:13px;font-weight:700;color:#e2eaf5;'>Net Tagihan</span>"
                    "<span style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:700;color:{nc};'>{nv}</span>"
                    "</div>".format(L.fmt_rp(mng), nc=net_col, nv=L.fmt_rp(abs(net))))
            rows_html+=(
                "<div style='display:flex;justify-content:space-between;align-items:center;padding:8px 0;'>"
                "<span style='font-size:12px;color:#60a5fa;'>✅ Sudah disetor ke kas</span>"
                "<span style='font-family:IBM Plex Mono,monospace;font-size:12px;color:#60a5fa;'>{}</span>"
                "</div>".format(L.fmt_rp(paid)))

            # Status badge
            status_bg={"✅":"rgba(34,197,94,.12)","⏳":"rgba(245,158,11,.12)","❗":"rgba(239,68,68,.12)","💚":"rgba(6,182,212,.12)"}.get(st_ic,"rgba(100,116,139,.12)")

            st.markdown(
                "<div style='background:#161e2a;border:1px solid #243044;border-left:4px solid {ac};"
                "border-radius:14px;padding:0;margin-bottom:12px;overflow:hidden;'>"
                # Header
                "<div style='display:flex;align-items:center;gap:14px;padding:16px 20px;"
                "border-bottom:1px solid #243044;background:#1c2638;'>"
                "<div style='width:42px;height:42px;background:{ac}20;border:1px solid {ac}50;"
                "border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;'>{jk}</div>"
                "<div style='flex:1;'>"
                "<div style='font-size:15px;font-weight:800;color:#e2eaf5;'>{nm}</div>"
                "<div style='font-size:11px;color:#4a6080;margin-top:2px;'>@{pan}</div>"
                "</div>"
                "<div style='text-align:right;'>"
                "<div style='display:inline-block;background:{sbg};color:{ac};border:1px solid {ac}50;"
                "padding:4px 12px;border-radius:20px;font-size:10px;font-weight:700;"
                "font-family:IBM Plex Mono,monospace;letter-spacing:.5px;margin-bottom:4px;'>{st_ic} {stxt}</div><br>"
                "<div style='font-size:9px;color:#4a6080;text-transform:uppercase;letter-spacing:1px;'>{sv_lbl}</div>"
                "<div style='font-size:20px;font-weight:700;color:{ac};font-family:IBM Plex Mono,monospace;'>{sv}</div>"
                "</div></div>"
                # Body
                "<div style='padding:14px 20px;'>"
                "{rows}"
                # Progress
                "<div style='height:4px;background:#243044;border-radius:4px;overflow:hidden;margin-top:14px;'>"
                "<div style='height:100%;border-radius:4px;width:{pct}%;background:{ac};transition:width .6s;'></div></div>"
                "<div style='font-size:10px;color:#4a6080;margin-top:5px;text-align:right;'>{pct}% terbayar</div>"
                "</div></div>".format(
                    ac=ac,jk=jk_ic3,nm=m["nama_lengkap"],pan=pan,sbg=status_bg,
                    st_ic=st_ic,stxt=st_txt,sv_lbl=sv_lbl,sv=sv,rows=rows_html,pct=pct),
                unsafe_allow_html=True)

            # Detail items expander
            total_det=(len(p_items)+(len(k_items) if show_kel else 0))
            if total_det>0:
                with st.expander("📋 Lihat detail {} item".format(total_det)):
                    def _rend_item(pi, is_personal=False):
                        jp=pi.get("jenis_pengadaan","Beli")
                        jpc={"Beli":"green","Sewa":"orange","DP":"yellow","Dimiliki":"gray"}.get(jp,"gray")
                        lbl="Tanggung penuh" if is_personal else "porsi"
                        st.markdown(
                            "<div style='display:flex;justify-content:space-between;align-items:center;"
                            "padding:7px 10px;background:#1c2638;border-radius:8px;margin-bottom:4px;gap:10px;'>"
                            "<div style='flex:1;'><span style='font-size:12px;font-weight:600;color:#e2eaf5;'>• {nm}</span> "
                            "{jp}</div>"
                            "<div style='text-align:right;flex-shrink:0;'>"
                            "<div style='font-size:10px;color:#4a6080;'>{lbl}</div>"
                            "<div style='font-size:13px;font-weight:700;color:#60a5fa;"
                            "font-family:IBM Plex Mono,monospace;'>{po}</div>"
                            "</div></div>".format(
                                nm=pi["nama_item"],jp=badge(jp,jpc),lbl=lbl,
                                po=L.fmt_rp(pi["per_orang_rp"])),
                            unsafe_allow_html=True)
                    if show_kel and k_items:
                        st.markdown("<div class='sec-lbl'>🏕️ Item Kelompok (dibagi rata)</div>",unsafe_allow_html=True)
                        for ki in k_items: _rend_item(ki,False)
                    if p_items:
                        st.markdown("<div class='sec-lbl'>👤 Item Personal (tanggung penuh)</div>",unsafe_allow_html=True)
                        for pi in p_items: _rend_item(pi,True)

    with tabs[1]:
        fc1,fc2,fc3=st.columns(3)
        fg=fc1.selectbox("Kelompokkan",["Kategori","Scope","Jenis"],key="rk_fg")
        fsrt=fc2.selectbox("Urut",["Default","Nama A-Z","Harga ↓"],key="rk_srt")
        fq=fc3.text_input("🔍 Cari","",key="rk_q")
        filtered=[i for i in items if not fq or fq.lower() in i["nama_item"].lower()]
        if fsrt=="Nama A-Z": filtered=sorted(filtered,key=lambda x:x["nama_item"])
        elif fsrt=="Harga ↓": filtered=sorted(filtered,key=lambda x:-float(x["subtotal"]))
        def gkey(i):
            if fg=="Scope": return ("",i["tipe_scope"])
            if fg=="Jenis": return ("",i["jenis_pengadaan"])
            return (i.get("icon","📦"),i.get("nama_kategori","?"))
        by_g={}
        for i in filtered: by_g.setdefault(gkey(i),[]).append(i)

        # Untuk member: grand total = tagihan dirinya; untuk admin = semua subtotal mentah
        if admin:
            grand=sum(float(i["subtotal"]) for i in filtered if i["tipe_scope"]=="Kelompok") + \
                  sum(float(i.get("subtotal",0))*len(i.get("assigned_members",[])) for i in filtered if i["tipe_scope"]=="Personal")
        else:
            grand=my_tag if (not admin and my_mid) else sum(float(i["subtotal"]) for i in filtered)

        for (ico,gnm),gitems in sorted(by_g.items()):
            if admin:
                gt=sum(float(i["subtotal"]) for i in gitems if i["tipe_scope"]=="Kelompok") + \
                   sum(float(i.get("subtotal",0))*len(i.get("assigned_members",[])) for i in gitems if i["tipe_scope"]=="Personal")
            else:
                # member: kelompok → per_orang_rp; personal → per_orang_rp (if assigned to them)
                gt_k=sum(float(i["per_orang_rp"]) for i in gitems if i["tipe_scope"]=="Kelompok")
                gt_p=sum(float(i["per_orang_rp"]) for i in gitems
                         if i["tipe_scope"]=="Personal" and any(a["id"]==my_mid for a in i.get("assigned_members",[])))
                gt=gt_k+gt_p
            pct_g=gt/grand*100 if grand else 0
            with st.expander("{} {}  ·  {} item  ·  {}  ({:.1f}%)".format(ico,gnm,len(gitems),L.fmt_rp(gt),pct_g)):
                st.markdown("<div class='prog' style='margin-bottom:12px;'><div class='prog-fill' style='width:{:.0f}%'></div></div>".format(pct_g),unsafe_allow_html=True)
                for i in gitems:
                    asgn=i.get("assigned_members",[])
                    at=(", ".join(m.get("nama_panggilan") or m["nama_lengkap"].split()[0] for m in asgn)
                        if i["tipe_scope"]=="Personal" else "Semua ({})".format(jml))
                    sc="blue" if i["tipe_scope"]=="Kelompok" else "purple"
                    tang=""
                    if i.get("penanggung_nama"): tang="<span style='font-size:11px;color:var(--orange);'>💼 {}</span>".format(i["penanggung_nama"])

                    is_kelompok=(i["tipe_scope"]=="Kelompok")
                    # Check if member is assigned to this personal item
                    member_assigned=(not admin and my_mid and any(a["id"]==my_mid for a in asgn))
                    if not admin and i["tipe_scope"]=="Personal" and not member_assigned:
                        continue  # member: skip personal items not assigned to them

                    if admin:
                        if is_kelompok:
                            # Admin kelompok: Qty | Harga Item | Total Kelompok | —
                            col_labels=("Qty","Harga/Unit","Total Kelompok","—")
                            col_vals=(
                                "{} {}".format(float(i["jumlah"]),i["satuan"]),
                                L.fmt_rp(i["harga_satuan"]),
                                L.fmt_rp(i["subtotal"]),
                                "")
                        else:
                            # Admin personal: Qty | Harga Asli | Jml Orang | Subtotal Total
                            n_asgn=len(asgn) if asgn else jml
                            col_labels=("Qty","Harga/Unit","Jml Orang","Subtotal Total")
                            col_vals=(
                                "{} {}".format(float(i["jumlah"]),i["satuan"]),
                                L.fmt_rp(i["harga_satuan"]),
                                "{}×".format(n_asgn),
                                L.fmt_rp(float(i.get("subtotal",0))*n_asgn))
                    else:
                        if is_kelompok:
                            # Member kelompok: Qty | Total Kelompok | Jumlah Orang | Per Orang (subtotal)
                            col_labels=("Qty","Total Kelompok","Dibagi","Sub/Orang")
                            col_vals=(
                                "{} {}".format(float(i["jumlah"]),i["satuan"]),
                                L.fmt_rp(i["subtotal"]),
                                "{} org".format(jml),
                                L.fmt_rp(i["per_orang_rp"]))
                        else:
                            # Member personal: Qty | Harga Asli | Subtotal
                            col_labels=("Qty","Harga/Unit","Subtotal","")
                            col_vals=(
                                "{} {}".format(float(i["jumlah"]),i["satuan"]),
                                L.fmt_rp(i["harga_satuan"]),
                                L.fmt_rp(i["per_orang_rp"]),
                                "")

                    st.markdown(
                        "<div class='irow' style='display:grid;grid-template-columns:3fr 1fr 1fr 1fr;gap:8px;'>"
                        "<div><div style='font-size:13px;font-weight:700;color:var(--txt);'>{nm}</div>"
                        "<div style='display:flex;gap:6px;align-items:center;margin-top:4px;flex-wrap:wrap;'>"
                        "{sc} <span style='font-size:11px;color:var(--txt3);'>{jenis}</span>"
                        "<span style='font-size:11px;color:var(--txt3);'>👥 {ag}</span>{tang}</div></div>"
                        "<div style='text-align:right;'><div style='font-size:9px;color:var(--txt3);text-transform:uppercase;'>{l0}</div>"
                        "<div style='font-size:12px;color:var(--txt2);font-family:IBM Plex Mono,monospace;'>{v0}</div></div>"
                        "<div style='text-align:right;'><div style='font-size:9px;color:var(--txt3);text-transform:uppercase;'>{l1}</div>"
                        "<div style='font-size:12px;font-weight:600;color:var(--txt2);font-family:IBM Plex Mono,monospace;'>{v1}</div></div>"
                        "<div style='text-align:right;'><div style='font-size:9px;color:var(--txt3);text-transform:uppercase;'>{l2}</div>"
                        "<div style='font-size:14px;font-weight:700;color:var(--accent2);font-family:IBM Plex Mono,monospace;'>{v2}</div></div>"
                        "</div>".format(nm=i["nama_item"],sc=badge(i["tipe_scope"],sc),jenis=i["jenis_pengadaan"],
                            ag=at,tang=tang,
                            l0=col_labels[0],v0=col_vals[0],
                            l1=col_labels[1],v1=col_vals[1],
                            l2=col_labels[2] if len(col_labels)>2 else "",
                            v2=col_vals[2] if len(col_vals)>2 else ""),
                        unsafe_allow_html=True)

    with tabs[2]:
        cl,cr=st.columns(2)
        with cl:
            sec("📊 Komposisi Biaya")
            if admin:
                # Admin: kelompok = raw subtotal (tidak dibagi), personal = subtotal × assigned
                tk2=summary["total_kelompok"]
                tp2=sum(float(i.get("subtotal",0))*len(i.get("assigned_members",[]))
                        for i in items if i["tipe_scope"]=="Personal")
                total=tk2+tp2
            else:
                # Member: kelompok = per_orang_rp, personal = hanya yang ditugaskan ke dirinya
                tk2=summary["per_orang_kelompok"]
                tp2=sum(float(i.get("per_orang_rp",0)) for i in items
                        if i["tipe_scope"]=="Personal" and my_mid and
                        any(a["id"]==my_mid for a in i.get("assigned_members",[])))
                total=tk2+tp2
            if total>0:
                pct_k=tk2/total*100; pct_p=tp2/total*100
                lbl_k="Biaya Kelompok" if admin else "Porsi Kelompok (per orang)"
                lbl_p="Biaya Personal (total semua)" if admin else "Biaya Personal Saya"
                st.markdown("""
<div class='card card-blue' style='margin-bottom:8px;'>
  <div style='font-size:12px;color:var(--txt3);'>{lbl_k}</div>
  <div style='font-size:20px;font-weight:700;color:var(--accent2);font-family:IBM Plex Mono,monospace;'>{bk}</div>
  <div class='prog'><div class='prog-fill' style='width:{pk:.0f}%'></div></div>
  <div style='font-size:11px;color:var(--txt3);margin-top:4px;'>{pk:.1f}% dari total</div>
</div>
<div class='card card-purple' style='margin-bottom:8px;'>
  <div style='font-size:12px;color:var(--txt3);'>{lbl_p}</div>
  <div style='font-size:20px;font-weight:700;color:var(--purple);font-family:IBM Plex Mono,monospace;'>{bp}</div>
  <div class='prog'><div class='prog-fill' style='width:{pp:.0f}%;background:var(--purple);'></div></div>
  <div style='font-size:11px;color:var(--txt3);margin-top:4px;'>{pp:.1f}% dari total</div>
</div>""".format(lbl_k=lbl_k,bk=L.fmt_rp(tk2),pk=pct_k,lbl_p=lbl_p,bp=L.fmt_rp(tp2),pp=pct_p),unsafe_allow_html=True)
        with cr:
            sec("💳 Status Pembayaran")
            if members:
                if admin:
                    # Admin: hitung dari semua anggota
                    tg_gross=sum(tagihan.get(m["id"],0) for m in members)
                    tot_dt=sum(menanggung.get(m["id"],0) for m in members)
                    tot_paid_rk=sum(paid_all_rekap.get(m["id"],0) for m in members)
                    tot_terbayar=tot_paid_rk+tot_dt
                    tot_sisa=max(0,tg_gross-tot_terbayar)
                    pct_paid=tot_terbayar/tg_gross*100 if tg_gross else 100
                    lunas=sum(1 for m in members if paid_all_rekap.get(m["id"],0)>=max(0,tagihan.get(m["id"],0)-menanggung.get(m["id"],0)))
                    st.markdown("""
<div style='background:var(--raised);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:10px;'>
  <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Total Tagihan</div>
    <div style='font-size:16px;font-weight:700;color:var(--txt);font-family:IBM Plex Mono,monospace;margin-top:3px;'>{tg}</div></div>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Ditanggungkan</div>
    <div style='font-size:16px;font-weight:700;color:var(--orange);font-family:IBM Plex Mono,monospace;margin-top:3px;'>{dt}</div></div>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Kas Terkumpul</div>
    <div style='font-size:16px;font-weight:700;color:var(--green);font-family:IBM Plex Mono,monospace;margin-top:3px;'>{pd}</div></div>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Sisa Kurang Bayar</div>
    <div style='font-size:16px;font-weight:700;color:{sc};font-family:IBM Plex Mono,monospace;margin-top:3px;'>{ss}</div></div>
  </div>
  <div class='prog' style='margin-top:14px;'><div class='prog-fill prog-g' style='width:{pct:.0f}%'></div></div>
  <div style='font-size:11px;color:var(--txt3);margin-top:6px;'>{lu}/{tot} anggota lunas · {pct:.1f}% terbayar</div>
</div>""".format(tg=L.fmt_rp(tg_gross),dt=L.fmt_rp(tot_dt),pd=L.fmt_rp(tot_paid_rk),
                     sc="var(--red)" if tot_sisa>0 else "var(--green)",ss=L.fmt_rp(tot_sisa),
                     pct=pct_paid,lu=lunas,tot=len(members)),unsafe_allow_html=True)
                elif my_mid:
                    # Member: tampilkan hanya status dirinya
                    my_tag_r=tagihan.get(my_mid,0)
                    my_mng_r=menanggung.get(my_mid,0)
                    my_paid_r=paid_all_rekap.get(my_mid,0)
                    my_net_r=net_tagihan.get(my_mid,my_tag_r-my_mng_r)
                    my_sisa_r=max(0,my_net_r-my_paid_r)
                    pct_my=((my_paid_r+my_mng_r)/my_tag_r*100) if my_tag_r>0 else 100
                    lunas_my=(my_paid_r>=max(0,my_net_r))
                    st.markdown("""
<div style='background:var(--raised);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:10px;'>
  <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Tagihan Saya</div>
    <div style='font-size:16px;font-weight:700;color:var(--txt);font-family:IBM Plex Mono,monospace;margin-top:3px;'>{tg}</div></div>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Ditanggungkan</div>
    <div style='font-size:16px;font-weight:700;color:var(--orange);font-family:IBM Plex Mono,monospace;margin-top:3px;'>{dt}</div></div>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Sudah Dibayar</div>
    <div style='font-size:16px;font-weight:700;color:var(--green);font-family:IBM Plex Mono,monospace;margin-top:3px;'>{pd}</div></div>
    <div><div style='font-size:9px;color:var(--txt3);font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1.5px;'>Sisa Hutang</div>
    <div style='font-size:16px;font-weight:700;color:{sc};font-family:IBM Plex Mono,monospace;margin-top:3px;'>{ss}</div></div>
  </div>
  <div class='prog' style='margin-top:14px;'><div class='prog-fill prog-g' style='width:{pct:.0f}%'></div></div>
  <div style='font-size:11px;color:var(--txt3);margin-top:6px;'>{lu}</div>
</div>""".format(tg=L.fmt_rp(my_tag_r),dt=L.fmt_rp(my_mng_r),pd=L.fmt_rp(my_paid_r),
                     sc="var(--green)" if lunas_my else "var(--red)",ss=L.fmt_rp(my_sisa_r),
                     pct=pct_my,lu="✅ Lunas" if lunas_my else "⏳ Belum lunas"),unsafe_allow_html=True)

    with tabs[3]:
        sec("📥 Export Data")
        items_df=pd.DataFrame([{
            "Nama Item":i["nama_item"],"Kategori":i.get("nama_kategori",""),"Scope":i["tipe_scope"],
            "Jenis":i["jenis_pengadaan"],"Qty":float(i["jumlah"]),"Satuan":i["satuan"],
            "Harga":float(i["harga_satuan"]),"Subtotal":float(i["subtotal"]),
            "Per Orang":float(i["per_orang_rp"])} for i in items])
        st.download_button("📥 Download Items CSV",items_df.to_csv(index=False).encode(),
            "items_{}.csv".format(trip_id),"text/csv",use_container_width=True)
        if members:
            mem_df=pd.DataFrame([{"Nama":m["nama_lengkap"],"Tagihan":tagihan.get(m["id"],0),
                "Menanggung":menanggung.get(m["id"],0),"Net":net_tagihan.get(m["id"],0),
                "Lunas":L.get_paid(trip_id,m["id"])} for m in members])
            st.download_button("📥 Download Tagihan CSV",mem_df.to_csv(index=False).encode(),
                "tagihan_{}.csv".format(trip_id),"text/csv",use_container_width=True)
    _pw_end()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════
def page_payments():
    _pw()
    ph("💳","Pelacak Pembayaran","Siapa sudah bayar berapa dan kapan")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; jml=trip["jumlah_orang"]
    members=L.get_members(trip_id)
    if not members: alert("Tambahkan anggota dahulu.","warning"); _pw_end(); return
    summary=L.calc_trip_summary(trip_id,jml)
    tagihan=summary["tagihan"]; admin=is_admin_user()
    try:
        menanggung=summary["menanggung"]; net_tagihan=summary["net_tagihan"]
    except:
        menanggung={m["id"]:0 for m in members}
        net_tagihan={mid:tagihan.get(mid,0) for mid in tagihan}
    bank_list=L.get_bank_info()
    tab_list=["📊 Status","➕ Catat Bayar","📋 Riwayat","🏦 Rekening"]
    if admin: tab_list.append("⚙️ Kelola Rekening")
    tabs=st.tabs(tab_list)

    with tabs[0]:
        tg_gross=sum(tagihan.get(m["id"],0) for m in members)
        tot_dt=sum(menanggung.get(m["id"],0) for m in members)
        paid_all=L.get_paid_all(trip_id)
        tot_p=sum(paid_all.get(m["id"],0) for m in members)
        # Kas yang harus masuk = tagihan - yang sudah ditanggung penanggung
        tot_kas=max(0,tg_gross-tot_dt)
        # Sisa ke kas = yang belum masuk ke kas (tidak termasuk tanggungan)
        tot_s=max(0,tot_kas-tot_p)
        # Kurang bayar = total tagihan - semua yang sudah terbayar (kas + tanggungan)
        tot_kurang=max(0,tg_gross-tot_p)
        pct_all=(tot_p+tot_dt)/tg_gross*100 if tg_gross>0 else 100
        lunas=sum(1 for m in members if paid_all.get(m["id"],0)>=max(0,tagihan.get(m["id"],0)-menanggung.get(m["id"],0)))
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Total Tagihan",L.fmt_rp(tg_gross))
        c2.metric("Ditanggungkan",L.fmt_rp(tot_dt),help="Dibayarkan oleh penanggung, termasuk terbayar")
        c3.metric("Terbayar ke Kas",L.fmt_rp(tot_p))
        c4.metric("Kurang Dibayar","-{}".format(L.fmt_rp(tot_kurang)),
                  delta="Lunas ✅" if tot_kurang==0 else "-{}".format(L.fmt_rp(tot_kurang)),
                  delta_color="normal" if tot_kurang==0 else "inverse")
        c5.metric("Sisa ke Kas",L.fmt_rp(tot_s),delta="{}/{} lunas".format(lunas,len(members)))
        pb(pct_all,"green" if pct_all>=100 else "orange")
        msep()
        for m in members:
            mid=m["id"]; tag=tagihan.get(mid,0); mng=menanggung.get(mid,0)
            net=net_tagihan.get(mid,tag-mng); paid=paid_all.get(mid,0)
            if net>0:
                sisa=net-paid; pct=min(100,int(paid/net*100)) if net>0 else 100
                sc="#22c55e" if sisa<=0 else "#f59e0b" if paid>0 else "#ef4444"
                st2="✅ Lunas" if sisa<=0 else "Sisa {}".format(L.fmt_rp(sisa))
            else: pct=100; sc="#06b6d4"; st2="💚 Piutang {}".format(L.fmt_rp(abs(net)+paid))
            mng_str=" · Menanggung: <b style='color:var(--orange);'>{}</b>".format(L.fmt_rp(mng)) if mng>0 else ""
            st.markdown("""
<div class='card'>
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
    <div>
      <div style='font-size:13px;font-weight:700;color:var(--txt);'>👤 {nm}</div>
      <div style='font-size:11px;color:var(--txt3);font-family:IBM Plex Mono,monospace;margin-top:3px;'>Tagihan: {tag}{mng} · Bayar: <b style='color:var(--accent2);'>{paid}</b></div>
    </div>
    <div style='font-size:13px;font-weight:700;color:{sc};'>{st2}</div>
  </div>
  <div class='prog' style='margin-top:8px;'><div class='prog-fill' style='width:{pct}%;background:{sc};'></div></div>
</div>""".format(nm=m["nama_lengkap"],tag=L.fmt_rp(tag),mng=mng_str,paid=L.fmt_rp(paid),sc=sc,st2=st2,pct=pct),unsafe_allow_html=True)

    with tabs[1]:
        if not admin: alert("Pencatatan pembayaran hanya admin.","warning")
        else:
            mo={m["nama_lengkap"]:m["id"] for m in members}
            sm=st.selectbox("Anggota yang Bayar",list(mo.keys()),key="pay_sel")
            mid_p=mo[sm]; tag_m=tagihan.get(mid_p,0)
            net_m=net_tagihan.get(mid_p,tag_m); paid_n=paid_all.get(mid_p,0)
            sisa_m=max(0.0,net_m-paid_n)
            ct1,ct2,ct3=st.columns(3)
            ct1.metric("Net Tagihan",L.fmt_rp(net_m))
            ct2.metric("Sudah Dibayar",L.fmt_rp(paid_n))
            ct3.metric("Sisa",L.fmt_rp(sisa_m),delta="Lunas! ✅" if sisa_m<=0 else None,delta_color="normal")
            msep()
            with st.form("pay_add",clear_on_submit=True):
                pc1,pc2=st.columns(2)
                pjml=pc1.number_input("Jumlah Bayar (Rp)",min_value=0.0,value=float(sisa_m),step=10000.0)
                ptgl=pc2.date_input("Tanggal",value=date.today())
                pmt=st.selectbox("Metode",["Transfer","Tunai","QRIS","Lainnya"])
                pnote=st.text_input("Catatan (opsional)")
                if st.form_submit_button("✅ Catat Pembayaran",use_container_width=True):
                    if pjml<=0: st.error("Jumlah harus > 0!")
                    else:
                        L.add_payment(trip_id,dict(member_id=mid_p,jumlah=pjml,
                            tanggal=ptgl,metode=pmt,catatan=pnote or None))
                        st.success("✅ Pembayaran {} oleh {} dicatat!".format(L.fmt_rp(pjml),sm))
                        st.rerun()

    with tabs[2]:
        payments=L.get_payments(trip_id)
        if not payments: alert("Belum ada pembayaran.","info")
        else:
            total_p2=sum(float(p["jumlah"]) for p in payments)
            st.metric("Total Terbayar",L.fmt_rp(total_p2))
            for p in sorted(payments,key=lambda x:x["tanggal"],reverse=True):
                tgl_f=p["tanggal"].strftime("%d %b %Y") if hasattr(p["tanggal"],"strftime") else str(p["tanggal"])
                st.markdown("""
<div class='card card-green' style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
  <div>
    <div style='font-size:13px;font-weight:700;color:var(--txt);'>👤 {nm}</div>
    <div style='font-size:11px;color:var(--txt3);margin-top:2px;'>📅 {tgl} · 💳 {mt}{ct}</div>
  </div>
  <div style='font-size:20px;font-weight:700;color:var(--green);font-family:IBM Plex Mono,monospace;'>{jml}</div>
</div>""".format(nm=p.get("nama_lengkap",p.get("member_id","")),
                 tgl=tgl_f,mt=p.get("metode","Transfer"),
                 ct=" · "+p["catatan"] if p.get("catatan") else "",
                 jml=L.fmt_rp(p["jumlah"])),unsafe_allow_html=True)

    with tabs[3]:
        sec("🏦 Rekening Transfer")
        if not bank_list: alert("Belum ada rekening. Admin bisa tambahkan di tab Kelola Rekening.","info")
        else:
            for b in bank_list:
                st.markdown("""<div class='bank-card'>
  <div class='bank-logo'>{ic}</div>
  <div>
    <div class='bank-name'>{nm}</div>
    <div class='bank-acc'>{acc}</div>
    <div class='bank-holder'>a.n. {holder}</div>
    {cat}
  </div>
</div>""".format(ic=b.get("icon","🏦"),nm=b["nama_bank"],acc=b["no_rekening"],holder=b["atas_nama"],
                 cat="<div style='font-size:11px;color:var(--txt3);margin-top:4px;'>📝 {}</div>".format(b["catatan"]) if b.get("catatan") else ""),unsafe_allow_html=True)

    if admin:
        with tabs[4]:
            sec("➕ Tambah Rekening")
            with st.form("bank_add",clear_on_submit=True):
                c1,c2=st.columns(2)
                b_nm=c1.text_input("Nama Bank *",placeholder="BCA, BNI, Mandiri...")
                b_ic=c1.text_input("Icon/Emoji",value="🏦")
                b_no=c2.text_input("No. Rekening *")
                b_an=c2.text_input("Atas Nama *")
                b_ct=st.text_input("Catatan")
                b_ur=st.number_input("Urutan tampil",min_value=0,value=0)
                if st.form_submit_button("✅ Tambah Rekening",use_container_width=True):
                    if not b_nm or not b_no or not b_an: st.error("Semua field wajib diisi!")
                    else:
                        L.add_bank_info(dict(nama_bank=b_nm,no_rekening=b_no,atas_nama=b_an,catatan=b_ct or None,icon=b_ic,urutan=b_ur))
                        st.success("✅ Rekening ditambahkan!"); st.rerun()
            if bank_list:
                msep()
                sec("📋 Daftar Rekening")
                for b in bank_list:
                    c1,c2,_=st.columns([5,1,1])
                    c1.markdown("{} **{}** — `{}` — a.n. {}".format(b.get("icon","🏦"),b["nama_bank"],b["no_rekening"],b["atas_nama"]))
                    with c2: confirm_del("bank_{}".format(b["id"]),lambda bid=b["id"]:L.delete_bank_info(bid),"🗑️","Hapus rekening {}?".format(b["nama_bank"]))
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CHECKLIST KELOMPOK
# ═══════════════════════════════════════════════════════════════════════════════
def _cl_filters(prefix):
    c1,c2,c3,c4=st.columns(4)
    fl=c1.selectbox("Label",["Semua","Wajib","Disarankan","Opsional"],key="{}_fl".format(prefix))
    fs=c2.selectbox("Sumber",["Semua","Biaya","Master","Manual"],key="{}_fs".format(prefix))
    so=c3.selectbox("Urut",["Label","Nama","Sumber"],key="{}_so".format(prefix))
    fq=c4.text_input("🔍 Cari","",key="{}_fq".format(prefix))
    return (None if fl=="Semua" else fl),(None if fs=="Semua" else fs),so.lower(),fq

def page_cl_group():
    _pw()
    ph("✅","Checklist Kelompok","Perlengkapan bersama — dari biaya, master, atau manual")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; cats=L.get_categories(); admin=is_admin_user()
    cat_opts={"{} {}".format(c["icon"],c["nama_kategori"]):c["id"] for c in cats}
    fl,fs,so,fq=_cl_filters("clg")
    items=L.get_checklist_group(trip_id,sort_by=so,f_label=fl,f_sumber=fs,search=fq)
    total=len(items); siap=sum(1 for i in items if i["sudah_siap"])
    pct=int(siap/total*100) if total else 0

    # Progress header
    st.markdown("""
<div style='display:flex;justify-content:space-between;align-items:center;
  padding:14px 18px;background:var(--card);border:1px solid var(--border);
  border-radius:12px;margin-bottom:14px;'>
  <div>
    <div style='font-size:15px;font-weight:700;color:var(--txt);'>{siap}/{total} item siap</div>
    <div style='font-size:12px;color:var(--txt3);margin-top:2px;'>{pct}% selesai</div>
  </div>
  <div style='font-size:28px;font-weight:700;color:{col};font-family:IBM Plex Mono,monospace;'>{pct}%</div>
</div>""".format(siap=siap,total=total,pct=pct,col="#22c55e" if pct==100 else "#3b82f6"),unsafe_allow_html=True)
    pb(pct,"green" if pct==100 else "blue")
    if not admin:
        alert("ℹ️ Kamu dapat mencentang item. Hanya admin yang bisa menambah atau menghapus item.","info")
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)

    if not items: alert("Belum ada item. {}".format("Tambahkan di bawah." if admin else "Admin belum menambahkan item."),"info")
    else:
        SRCCOL={"Biaya":"blue","Master":"green","Manual":"gray"}
        by_src={"Biaya":[],"Master":[],"Manual":[]}
        for i in items: by_src.setdefault(i["sumber"],[]).append(i)
        for src in ["Biaya","Master","Manual"]:
            grp=by_src.get(src,[])
            if not grp: continue
            lbl={"Biaya":"dari Input Biaya","Master":"dari Item Master","Manual":"Input Manual"}.get(src,src)
            st.markdown("<div style='font-size:10px;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;padding:10px 0 5px;border-bottom:1px solid var(--border);margin-bottom:8px;'>{} {}</div>".format(badge(src,SRCCOL.get(src,"gray")),lbl),unsafe_allow_html=True)
            for cl in grp:
                done=bool(cl["sudah_siap"]); dibawa=cl.get("dibawa_nama") or ""
                lbl_col={"Wajib":"red","Disarankan":"orange","Opsional":"gray"}.get(cl["label"],"gray")
                bg="rgba(34,197,94,.06)" if done else "var(--raised)"
                bd="rgba(34,197,94,.4)" if done else "var(--border)"
                bl="var(--green)" if done else "var(--border2)"
                op="opacity:.55;" if done else ""
                sth="text-decoration:line-through;" if done else ""
                # Member tidak bisa hapus, hanya centang
                if admin:
                    c_chk,c_info,c_del=st.columns([1,9,1])
                else:
                    c_chk,c_info=st.columns([1,10])
                    c_del=None
                with c_chk:
                    st.markdown("<div style='padding-top:6px;'>",unsafe_allow_html=True)
                    nv=st.checkbox("",value=done,key="clg_{}".format(cl["id"]),label_visibility="collapsed")
                    if nv!=done: L.toggle_checklist_group(cl["id"],nv); st.rerun()
                    st.markdown("</div>",unsafe_allow_html=True)
                with c_info:
                    st.markdown("<div style='background:{bg};border:1px solid {bd};border-left:3px solid {bl};border-radius:10px;padding:9px 14px;{op}{sth}'><div style='font-size:13.5px;font-weight:700;color:var(--txt);line-height:1.3;'>{nm}</div><div style='display:flex;gap:6px;align-items:center;margin-top:4px;flex-wrap:wrap;'>{lb}<span style='font-size:11px;color:var(--txt3);'>{ic} {cat}</span><span style='font-size:11px;color:{dc};'>· {dh}</span></div></div>".format(
                        bg=bg,bd=bd,bl=bl,op=op,sth=sth,nm=cl["nama_item"],lb=badge(cl["label"],lbl_col),
                        ic=cl.get("icon","📦"),cat=cl.get("nama_kategori") or "—",
                        dc="var(--teal)" if dibawa else "var(--txt3)",
                        dh="🎒 {}".format(dibawa) if dibawa else "⏳ belum assign"),unsafe_allow_html=True)
                if c_del is not None:
                    with c_del:
                        st.markdown("<div style='padding-top:6px;'>",unsafe_allow_html=True)
                        confirm_del("clg_{}".format(cl["id"]),lambda cid=cl["id"]:L.delete_checklist_group(cid),"🗑️","Hapus {}?".format(cl["nama_item"]))
                        st.markdown("</div>",unsafe_allow_html=True)

    if admin:
        msep()
        tabs2=st.tabs(["➕ Tambah Manual","✏️ Edit Item"])
        with tabs2[0]:
            with st.form("clg_add",clear_on_submit=True):
                a1,a2,a3=st.columns(3)
                an=a1.text_input("Nama Item *"); ac=a2.selectbox("Kategori",["— Tidak ada —"]+list(cat_opts.keys()))
                al=a3.selectbox("Label",["Wajib","Disarankan","Opsional"])
                acat=cat_opts.get(ac) if ac!="— Tidak ada —" else None
                act=st.text_area("Catatan (opsional)",height=56)
                if st.form_submit_button("➕ Tambah",use_container_width=True):
                    if not an: st.error("Nama wajib!")
                    else:
                        L.add_checklist_group_manual(trip_id,dict(nama_item=an,category_id=acat,label=al,catatan=act or None))
                        st.success("✅ Ditambahkan!"); st.rerun()
        with tabs2[1]:
            all_items=L.get_checklist_group(trip_id)
            if not all_items: st.caption("Tidak ada item.")
            else:
                eopts={i["nama_item"]:i["id"] for i in all_items}
                esel=st.selectbox("🔍 Pilih item",list(eopts.keys()),key="clg_esel")
                ecl=next(i for i in all_items if i["id"]==eopts[esel])
                with st.form("clg_edit_{}".format(ecl["id"])):
                    e1,e2,e3=st.columns(3)
                    en=e1.text_input("Nama",value=ecl["nama_item"])
                    ecat_list=["— Tidak ada —"]+list(cat_opts.keys()); ei=0
                    if ecl.get("category_id") in cat_opts.values():
                        ek=next(k for k,v in cat_opts.items() if v==ecl["category_id"]); ei=ecat_list.index(ek)
                    ec2=e2.selectbox("Kategori",ecat_list,index=ei,key="clg_ec")
                    el=e3.selectbox("Label",["Wajib","Disarankan","Opsional"],index=["Wajib","Disarankan","Opsional"].index(ecl["label"]))
                    ecs=st.checkbox("Sudah Siap",value=bool(ecl["sudah_siap"]))
                    ect=st.text_area("Catatan",value=ecl.get("catatan") or "",height=56)
                    ecatv=cat_opts.get(ec2) if ec2!="— Tidak ada —" else None
                    if st.form_submit_button("💾 Simpan"):
                        L.update_checklist_group(ecl["id"],dict(nama_item=en,category_id=ecatv,label=el,sudah_siap=ecs,catatan=ect or None))
                        st.success("✅ Disimpan!"); st.rerun()
    _pw_end()



# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CHECKLIST PERSONAL
# ═══════════════════════════════════════════════════════════════════════════════
def page_cl_personal():
    _pw()
    ph("🎒","Checklist Personal","Barang bawaan masing-masing anggota")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; members=L.get_members(trip_id); cats=L.get_categories()
    cat_opts={"{} {}".format(c["icon"],c["nama_kategori"]):c["id"] for c in cats}
    admin=is_admin_user(); email=get_email()
    if not members: alert("Tambahkan anggota dahulu.","warning"); _pw_end(); return

    # Admin bisa pilih siapa saja; member hanya bisa lihat semua tapi aksi dirinya saja
    sel_mn=st.selectbox("Pilih Anggota",[m["nama_lengkap"] for m in members],key="clp_sel")
    sel_m=next(m for m in members if m["nama_lengkap"]==sel_mn); mid=sel_m["id"]
    # Cek apakah yang dipilih adalah diri sendiri
    is_own = admin or (sel_m.get("email") or "").lower()==email.lower()

    fl,fs,so,fq=_cl_filters("clp")
    items=L.get_checklist_personal(trip_id,mid,sort_by=so,f_label=fl,f_sumber=fs,search=fq)
    total=len(items); siap=sum(1 for i in items if i["sudah_siap"])
    pct=int(siap/total*100) if total else 0
    st.markdown("""
<div style='display:flex;justify-content:space-between;align-items:center;
  padding:14px 18px;background:var(--card);border:1px solid var(--border);
  border-radius:12px;margin-bottom:14px;'>
  <div>
    <div style='font-size:15px;font-weight:700;color:var(--txt);'>{sel_mn}</div>
    <div style='font-size:12px;color:var(--txt3);margin-top:2px;'>{siap}/{total} siap · {pct}%</div>
  </div>
  <div style='font-size:28px;font-weight:700;color:{col};font-family:IBM Plex Mono,monospace;'>{pct}%</div>
</div>""".format(sel_mn=sel_mn,siap=siap,total=total,pct=pct,col="#22c55e" if pct==100 else "#3b82f6"),unsafe_allow_html=True)
    pb(pct,"green" if pct==100 else "blue")
    if not is_own:
        alert("👁️ Kamu hanya bisa melihat data anggota lain. Pilih namamu untuk mengelola item.","info")
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
    if not items: alert("Belum ada item. {}".format("Tambahkan di bawah." if is_own else ""),"info")
    else:
        SRCCOL={"Biaya":"blue","Master":"green","Manual":"gray"}
        by_src={"Biaya":[],"Master":[],"Manual":[]}
        for i in items: by_src.setdefault(i["sumber"],[]).append(i)
        for src in ["Biaya","Master","Manual"]:
            grp=by_src.get(src,[])
            if not grp: continue
            st.markdown("<div style='font-size:10px;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;padding:10px 0 5px;border-bottom:1px solid var(--border);margin-bottom:8px;'>{}</div>".format(badge(src,SRCCOL.get(src,"gray"))),unsafe_allow_html=True)
            for cl in grp:
                done=bool(cl["sudah_siap"]); lbl_col={"Wajib":"red","Disarankan":"orange","Opsional":"gray"}.get(cl["label"],"gray")
                bg="rgba(34,197,94,.06)" if done else "var(--raised)"; bd="rgba(34,197,94,.4)" if done else "var(--border)"
                bl="var(--green)" if done else "var(--border2)"; op="opacity:.55;" if done else ""; sth="text-decoration:line-through;" if done else ""
                if is_own:
                    c_chk,c_info,c_del=st.columns([1,9,1])
                else:
                    c_chk,c_info=st.columns([1,10]); c_del=None
                with c_chk:
                    st.markdown("<div style='padding-top:6px;'>",unsafe_allow_html=True)
                    if is_own:
                        nv=st.checkbox("",value=done,key="clp_{}".format(cl["id"]),label_visibility="collapsed")
                        if nv!=done: L.toggle_checklist_personal(cl["id"],nv); st.rerun()
                    else:
                        # View-only: show read-only indicator
                        st.markdown("<span style='font-size:16px;'>{}</span>".format("✅" if done else "⬜"),unsafe_allow_html=True)
                    st.markdown("</div>",unsafe_allow_html=True)
                with c_info:
                    st.markdown("<div style='background:{bg};border:1px solid {bd};border-left:3px solid {bl};border-radius:10px;padding:9px 14px;{op}{sth}'><div style='font-size:13.5px;font-weight:700;color:var(--txt);'>{nm}</div><div style='display:flex;gap:6px;align-items:center;margin-top:4px;flex-wrap:wrap;'>{lb}<span style='font-size:11px;color:var(--txt3);'>{ic} {cat}</span></div></div>".format(
                        bg=bg,bd=bd,bl=bl,op=op,sth=sth,nm=cl["nama_item"],lb=badge(cl["label"],lbl_col),
                        ic=cl.get("icon","📦"),cat=cl.get("nama_kategori") or "—"),unsafe_allow_html=True)
                if c_del is not None:
                    with c_del:
                        st.markdown("<div style='padding-top:6px;'>",unsafe_allow_html=True)
                        confirm_del("clp_{}".format(cl["id"]),lambda cid=cl["id"]:L.delete_checklist_personal(cid),"🗑️")
                        st.markdown("</div>",unsafe_allow_html=True)

    if is_own:
        msep()
        tabs2=st.tabs(["➕ Tambah Manual","✏️ Edit Item"])
        with tabs2[0]:
            with st.form("clp_add",clear_on_submit=True):
                a1,a2,a3=st.columns(3)
                an=a1.text_input("Nama Item *"); ac=a2.selectbox("Kategori",["— Tidak ada —"]+list(cat_opts.keys()))
                al=a3.selectbox("Label",["Wajib","Disarankan","Opsional"])
                acat=cat_opts.get(ac) if ac!="— Tidak ada —" else None
                act=st.text_area("Catatan (opsional)",height=56)
                if st.form_submit_button("➕ Tambah",use_container_width=True):
                    if not an: st.error("Nama wajib!")
                    else:
                        L.add_checklist_personal_manual(trip_id,mid,dict(nama_item=an,category_id=acat,label=al,catatan=act or None))
                        st.success("✅ Ditambahkan!"); st.rerun()
        with tabs2[1]:
            all_items=L.get_checklist_personal(trip_id,mid)
            if not all_items: st.caption("Tidak ada item.")
            else:
                eopts={i["nama_item"]:i["id"] for i in all_items}
                esel=st.selectbox("🔍 Pilih item",list(eopts.keys()),key="clp_esel")
                ecl=next(i for i in all_items if i["id"]==eopts[esel])
                with st.form("clp_edit_{}".format(ecl["id"])):
                    e1,e2,e3=st.columns(3)
                    en=e1.text_input("Nama",value=ecl["nama_item"])
                    ecat_list=["— Tidak ada —"]+list(cat_opts.keys()); ei=0
                    if ecl.get("category_id") in cat_opts.values():
                        ek=next(k for k,v in cat_opts.items() if v==ecl["category_id"]); ei=ecat_list.index(ek)
                    ec2=e2.selectbox("Kategori",ecat_list,index=ei,key="clp_ec")
                    el=e3.selectbox("Label",["Wajib","Disarankan","Opsional"],index=["Wajib","Disarankan","Opsional"].index(ecl["label"]))
                    ecs=st.checkbox("Sudah Siap",value=bool(ecl["sudah_siap"]))
                    ect=st.text_area("Catatan",value=ecl.get("catatan") or "",height=56)
                    ecatv=cat_opts.get(ec2) if ec2!="— Tidak ada —" else None
                    if st.form_submit_button("💾 Simpan"):
                        L.update_checklist_personal(ecl["id"],dict(nama_item=en,category_id=ecatv,label=el,sudah_siap=ecs,catatan=ect or None))
                        st.success("✅ Disimpan!"); st.rerun()
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: BAWA APA (Kelompok assignment view)
# ═══════════════════════════════════════════════════════════════════════════════
def page_bawa_apa():
    _pw()
    ph("📦","Bawa Apa?","Siapa bawa apa — penugasan pembawa item kelompok")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; members=L.get_members(trip_id); admin=is_admin_user()
    if not members: alert("Tambahkan anggota dahulu.","warning"); _pw_end(); return
    items=L.get_checklist_group(trip_id)
    if not items: alert("Belum ada item checklist kelompok.","info"); _pw_end(); return
    m_opts={"— Belum ditentukan —":None}
    m_opts.update({m["nama_lengkap"]:m["id"] for m in members})
    if not admin: alert("🔒 Hanya admin yang bisa mengubah penugasan.","info")
    view_opts=["Semua"]+[m["nama_lengkap"] for m in members]
    view_sel=st.selectbox("Tampilkan item milik",view_opts,key="bawa_view")
    by_cat={}
    for i in items: by_cat.setdefault(i.get("nama_kategori","Lain-lain"),[]).append(i)
    for cat_name,citems in sorted(by_cat.items()):
        filt=[cl for cl in citems if view_sel=="Semua" or view_sel==(cl.get("dibawa_nama") or "")]
        if not filt: continue
        cat_ic=citems[0].get("cat_icon") or citems[0].get("icon") or "📦"
        siap_cnt=sum(1 for cl in filt if cl.get("sudah_siap"))
        with st.expander("{} {}  ·  {} item  ·  {}/{} ceklis".format(cat_ic,cat_name,len(filt),siap_cnt,len(filt))):
            for cl in filt:
                done=bool(cl["sudah_siap"]); dibawa=cl.get("dibawa_nama") or ""
                lbl_col={"Wajib":"red","Disarankan":"orange","Opsional":"gray"}.get(cl.get("label","Wajib"),"gray")
                if done: si="✅"; row_bg="rgba(34,197,94,.06)"; row_bd="var(--green)"
                elif dibawa: si="📦"; row_bg="var(--card)"; row_bd="var(--accent)"
                else: si="⏳"; row_bg="rgba(239,68,68,.04)"; row_bd="rgba(239,68,68,.3)"
                st.markdown("<div style='background:{bg};border:1px solid {bd};border-radius:10px;padding:8px 12px;margin-bottom:5px;display:flex;gap:10px;align-items:center;'><span style='font-size:16px;flex-shrink:0;'>{si}</span><div style='flex:1;'><span style='font-size:13px;font-weight:600;color:var(--txt);'>{nm}</span> {lb}{dbw}</div></div>".format(
                    bg=row_bg,bd=row_bd,si=si,nm=cl["nama_item"],lb=badge(cl.get("label","Wajib"),lbl_col),
                    dbw="<div style='font-size:11px;color:var(--teal);margin-top:2px;'>🎒 {}</div>".format(dibawa) if dibawa else "<div style='font-size:11px;color:var(--red);margin-top:2px;'>Belum ditentukan</div>"),unsafe_allow_html=True)
                if admin:
                    cur_key=next((k for k,v in m_opts.items() if v==cl.get("dibawa_oleh")),"— Belum ditentukan —")
                    cur_idx=list(m_opts.keys()).index(cur_key) if cur_key in m_opts else 0
                    new_sel=st.selectbox("Penugasan",list(m_opts.keys()),index=cur_idx,key="bawa_{}".format(cl["id"]),label_visibility="collapsed")
                    new_mid=m_opts[new_sel]
                    if new_mid!=cl.get("dibawa_oleh"): L.assign_pembawa(cl["id"],new_mid); st.rerun()
    msep()
    sec("📊 Ringkasan per Anggota")
    # Ambil semua item personal per member
    all_personal_items={m["id"]:L.get_checklist_personal(trip_id,m["id"]) for m in members}
    for m in members:
        mid=m["id"]
        # Item kelompok yang ditugaskan ke anggota ini (dibawa_oleh == mid)
        kel_milik=[i for i in items if i.get("dibawa_oleh")==mid]
        kel_siap=[i for i in kel_milik if i.get("sudah_siap")]
        # Item personal milik anggota ini
        pers_items=all_personal_items.get(mid,[])
        pers_siap=[i for i in pers_items if i.get("sudah_siap")]
        total_items=len(kel_milik)+len(pers_items)
        total_siap=len(kel_siap)+len(pers_siap)
        pct_m=int(total_siap/total_items*100) if total_items else 0
        ac="#22c55e" if pct_m==100 else "#f59e0b" if pct_m>50 else "#3b82f6"

        # Build chip lists
        kel_chips="".join(
            "<span style='background:{bg};color:{c};padding:4px 10px;border-radius:16px;"
            "font-size:11px;border:1px solid {bc};font-weight:600;white-space:nowrap;'>"
            "{ic} {nm}</span>".format(
                bg="rgba(34,197,94,.1)" if i.get("sudah_siap") else "rgba(59,130,246,.07)",
                c="var(--green)" if i.get("sudah_siap") else "var(--accent2)",
                bc="rgba(34,197,94,.3)" if i.get("sudah_siap") else "rgba(59,130,246,.2)",
                ic="✅" if i.get("sudah_siap") else "📦",
                nm=i["nama_item"])
            for i in kel_milik) if kel_milik else "<span style='color:var(--txt3);font-size:11px;'>Belum ada item kelompok</span>"

        pers_chips="".join(
            "<span style='background:{bg};color:{c};padding:4px 10px;border-radius:16px;"
            "font-size:11px;border:1px solid {bc};font-weight:600;white-space:nowrap;'>"
            "{ic} {nm}</span>".format(
                bg="rgba(34,197,94,.1)" if i.get("sudah_siap") else "rgba(168,85,247,.07)",
                c="var(--green)" if i.get("sudah_siap") else "var(--purple)",
                bc="rgba(34,197,94,.3)" if i.get("sudah_siap") else "rgba(168,85,247,.2)",
                ic="✅" if i.get("sudah_siap") else "🎒",
                nm=i["nama_item"])
            for i in pers_items) if pers_items else "<span style='color:var(--txt3);font-size:11px;'>Tidak ada item personal</span>"

        pb_color="#22c55e" if pct_m==100 else "#f59e0b" if pct_m>50 else "#3b82f6"
        pb_html=("<div style='height:4px;background:var(--border);border-radius:4px;margin-bottom:14px;overflow:hidden;'><div style='height:100%;width:{pct}%;background:{col};border-radius:4px;'></div></div>".format(pct=min(100,max(0,pct_m)),col=pb_color)) if total_items else ""
        st.markdown("""
<div style='background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:16px 18px;margin-bottom:10px;overflow:hidden;'>
  {pb_html}
  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;'>
    <div style='font-size:14px;font-weight:700;color:var(--txt);'>👤 {nm}</div>
    <div style='display:flex;align-items:center;gap:12px;'>
      <span style='font-size:11px;color:var(--txt3);'>🏕️ {kl}/{kt} kelompok · 🎒 {pl}/{pt} personal</span>
      <span style='font-family:IBM Plex Mono,monospace;font-size:15px;font-weight:800;color:{ac};'>{ts}/{tt} ✅</span>
    </div>
  </div>
  <div style='margin-bottom:8px;'>
    <div style='font-size:10px;color:var(--txt3);font-weight:700;text-transform:uppercase;
      letter-spacing:1px;margin-bottom:6px;'>🏕️ Item Kelompok ({kt} item)</div>
    <div style='display:flex;gap:6px;flex-wrap:wrap;'>{kchips}</div>
  </div>
  <div>
    <div style='font-size:10px;color:var(--txt3);font-weight:700;text-transform:uppercase;
      letter-spacing:1px;margin-bottom:6px;'>🎒 Item Personal ({pt} item)</div>
    <div style='display:flex;gap:6px;flex-wrap:wrap;'>{pchips}</div>
  </div>
</div>""".format(
            pb_html=pb_html,nm=m["nama_lengkap"],ac=ac,
            kl=len(kel_siap),kt=len(kel_milik),
            pl=len(pers_siap),pt=len(pers_items),
            ts=total_siap,tt=total_items,
            kchips=kel_chips,pchips=pers_chips),
        unsafe_allow_html=True)
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: BERAT
# ═══════════════════════════════════════════════════════════════════════════════
def page_berat():
    _pw()
    ph("⚖️","Estimasi Berat","Distribusi beban dari biaya trip + item master checklist")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; jml=trip["jumlah_orang"]
    result=L.calc_berat(trip_id,jml); members=result["members"]; items=result["items"]
    berat_po=result["berat_per_orang"]; total_berat=result["berat_total"]; total_kel=result["berat_kelompok"]
    if not members: alert("Tambahkan anggota dahulu.","warning"); _pw_end(); return
    if total_berat==0:
        alert("⚖️ Belum ada data berat. Isi kolom berat di Input Biaya atau Item Master.","warning"); _pw_end(); return
    c1,c2,c3,c4=st.columns(4)
    c1.metric("📦 Total",L.fmt_berat(total_berat))
    c2.metric("🏕️ Kelompok",L.fmt_berat(total_kel))
    c3.metric("👤 Personal",L.fmt_berat(total_berat-total_kel))
    c4.metric("👥 Rata/Orang",L.fmt_berat(total_berat/max(len(members),1)))
    msep()
    alert("📌 Berat tiap orang = porsi item kelompok + item personal miliknya.","info")
    tabs_b=st.tabs(["👤 Per Anggota","📦 Semua Item"])
    with tabs_b[0]:
        max_b=max(berat_po.values()) if berat_po and max(berat_po.values())>0 else 1
        for idx_b,m in enumerate(members):
            mid=m["id"]; bg=berat_po.get(mid,0)
            pct_max=(bg/max_b*100) if max_b>0 else 0
            pct_tot=(bg/total_berat*100) if total_berat>0 else 0
            p_items_m=[i for i in items if i["tipe_scope"]=="Personal" and mid in i.get("assigned_ids",[])]
            k_items_m=[i for i in items if i["tipe_scope"]=="Kelompok" and mid in i.get("assigned_ids",[])]
            p_berat=sum(i["berat_per_orang_item"] for i in p_items_m)
            k_berat=sum(i["berat_per_orang_item"] for i in k_items_m)
            ac="#22c55e" if pct_max<=60 else "#f59e0b" if pct_max<=85 else "#ef4444"
            warn=" ⚠️" if pct_max>85 else ""
            with st.expander("{}{}  —  {}  ({:.0f}% dari terberat)".format(m["nama_lengkap"],warn,L.fmt_berat(bg),pct_max),expanded=(idx_b==0)):
                cl,cr=st.columns([3,1])
                with cl:
                    st.markdown("<div style='font-size:11px;color:var(--txt3);margin-bottom:6px;'>🧳 Personal <b style='color:var(--txt2);'>{}</b> + 🏕️ Kelompok <b style='color:var(--txt2);'>{}</b></div>".format(L.fmt_berat(p_berat),L.fmt_berat(k_berat)),unsafe_allow_html=True)
                    st.markdown("<div class='prog'><div class='prog-fill' style='width:{w:.0f}%;background:{ac};'></div></div><div style='font-size:10px;color:var(--txt3);margin-top:3px;'>{w:.0f}% dari terberat · {pt:.1f}% dari total</div>".format(w=pct_max,ac=ac,pt=pct_tot),unsafe_allow_html=True)
                with cr:
                    st.markdown("<div style='text-align:right;'><div style='font-size:9px;color:var(--txt3);text-transform:uppercase;font-family:IBM Plex Mono,monospace;'>Total Bawa</div><div style='font-size:24px;font-weight:700;color:{ac};font-family:IBM Plex Mono,monospace;margin-top:4px;'>{brt}</div></div>".format(ac=ac,brt=L.fmt_berat(bg)),unsafe_allow_html=True)
                if p_items_m or k_items_m:
                    msep()
                    if k_items_m:
                        st.markdown("<div style='font-size:10px;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>🏕️ Item Kelompok</div>",unsafe_allow_html=True)
                        for it in k_items_m:
                            n_c=len(it.get("assigned_ids",[])); is_sh=n_c>1
                            sl=(" <span style='font-size:10px;color:var(--orange);background:rgba(245,158,11,.12);padding:1px 6px;border-radius:10px;'>dibagi {} org</span>".format(n_c) if is_sh else " <span style='font-size:10px;color:var(--teal);background:rgba(6,182,212,.1);padding:1px 6px;border-radius:10px;'>pembawa tunggal</span>")
                            st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);'><span style='font-size:12px;color:var(--txt2);'>{ic} {nm}{sl}</span><span style='font-size:12px;font-weight:600;color:var(--txt);font-family:IBM Plex Mono,monospace;'>{brt}</span></div>".format(ic=it.get("icon","📦"),nm=it["nama_item"],sl=sl,brt=L.fmt_berat(it["berat_per_orang_item"])),unsafe_allow_html=True)
                    if p_items_m:
                        st.markdown("<div style='font-size:10px;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;margin:10px 0 6px;'>🧳 Item Personal</div>",unsafe_allow_html=True)
                        for it in p_items_m:
                            st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);'><span style='font-size:12px;color:var(--txt2);'>{ic} {nm}</span><span style='font-size:12px;font-weight:600;color:var(--txt);font-family:IBM Plex Mono,monospace;'>{brt}</span></div>".format(ic=it.get("icon","📦"),nm=it["nama_item"],brt=L.fmt_berat(it["berat_per_orang_item"])),unsafe_allow_html=True)
    with tabs_b[1]:
        items_wb=[i for i in items if i.get("berat_total_item",0)>0]
        if not items_wb: alert("Tidak ada item dengan data berat.","info")
        else:
            f1,f2=st.columns(2)
            f_sc=f1.selectbox("Scope",["Semua","Kelompok","Personal"],key="brt_sc")
            f_sr=f2.selectbox("Sumber",["Semua","Biaya","Master (Checklist)"],key="brt_sr")
            fi=[i for i in items_wb if (f_sc=="Semua" or i["tipe_scope"]==f_sc) and (f_sr=="Semua" or i.get("sumber_berat","")==f_sr)]
            by_cat_bw={}
            for i in fi: by_cat_bw.setdefault((i.get("icon","📦"),i.get("nama_kategori","Lain-lain")),[]).append(i)
            for (ic_bw,cat_bw),items_bw in sorted(by_cat_bw.items()):
                cat_tot=sum(i.get("berat_total_item",0) for i in items_bw)
                with st.expander("{} {}  ·  {} item  ·  {}".format(ic_bw,cat_bw,len(items_bw),L.fmt_berat(cat_tot))):
                    for i in items_bw:
                        btu=i.get("berat_total_item",0); bpo=i.get("berat_per_orang_item",0)
                        asgn=i.get("assigned_members",[]); astr=", ".join(m.get("nama_panggilan") or m["nama_lengkap"].split()[0] for m in asgn) if asgn else "Semua"
                        st.markdown("<div class='irow' style='display:grid;grid-template-columns:3fr 1fr 1fr 1fr;gap:8px;'><div><div style='font-size:13px;font-weight:700;color:var(--txt);'>{nm}</div><div style='display:flex;gap:6px;margin-top:4px;'>{sc} <span style='font-size:11px;color:var(--txt3);'>👥 {ag}</span></div></div><div style='text-align:right;font-size:11px;color:var(--txt3);'>Qty<br>{qty} {sat}</div><div style='text-align:right;'><div style='font-size:9px;color:var(--txt3);'>Per Org</div><div style='font-size:12px;font-weight:600;color:var(--accent2);font-family:IBM Plex Mono,monospace;'>{bpo}</div></div><div style='text-align:right;'><div style='font-size:9px;color:var(--txt3);'>Total</div><div style='font-size:14px;font-weight:700;color:var(--txt);font-family:IBM Plex Mono,monospace;'>{btu}</div></div></div>".format(
                            nm=i["nama_item"],sc=badge(i["tipe_scope"],"blue" if i["tipe_scope"]=="Kelompok" else "purple"),ag=astr,qty=float(i["jumlah"]),sat=i["satuan"],bpo=L.fmt_berat(bpo),btu=L.fmt_berat(btu)),unsafe_allow_html=True)
    _pw_end()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
def page_timeline():
    _pw()
    ph("📅","Timeline Rencana","Susun jadwal kegiatan per hari — bisa buat beberapa skenario")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; admin=is_admin_user()
    tb=trip["tanggal_berangkat"]; tk=trip.get("tanggal_kembali") or tb; durasi=(tk-tb).days+1
    TCATS=["Perjalanan","Pendakian","Istirahat","Makan","Dokumentasi","Darurat","Lainnya"]
    TCAT_IC={"Perjalanan":"🚌","Pendakian":"🥾","Istirahat":"⛺","Makan":"🍽️","Dokumentasi":"📷","Darurat":"🚨","Lainnya":"📍"}
    TCAT_CO={"Perjalanan":"#3b82f6","Pendakian":"#22c55e","Istirahat":"#f59e0b","Makan":"#ec4899","Dokumentasi":"#a855f7","Darurat":"#ef4444","Lainnya":"#64748b"}
    def _safe_time(val,default=None):
        import datetime as _dt
        if val is None: return default
        if isinstance(val,_dt.time): return val
        if isinstance(val,_dt.datetime): return val.time()
        if isinstance(val,str):
            try:
                parts=val.split(":")
                return _dt.time(int(parts[0]),int(parts[1]) if len(parts)>1 else 0)
            except: return default
        return default
    scenarios=L.get_timeline_scenarios(trip_id)
    if not scenarios and admin:
        alert("Belum ada skenario timeline. Buat skenario pertama.","info")
        with st.form("sc_first",clear_on_submit=True):
            sc_nm=st.text_input("Nama Skenario *",placeholder="misal: Skenario A — Via Normal")
            sc_ds=st.text_area("Deskripsi (opsional)",height=56)
            if st.form_submit_button("➕ Buat Skenario"):
                if not sc_nm: st.error("Nama skenario wajib!")
                else:
                    L.create_scenario(trip_id,sc_nm,sc_ds); st.success("✅ Skenario dibuat!"); st.rerun()
        _pw_end(); return
    if not scenarios: alert("Belum ada rencana timeline.","info"); _pw_end(); return
    sc_opts={"📌 {}".format(sc["nama"]) if i==0 else "📋 {}".format(sc["nama"]):sc["id"] for i,sc in enumerate(scenarios)}
    sc_col,sc_btn=st.columns([5,1])
    sel_sc=sc_col.selectbox("Skenario",list(sc_opts.keys()),key="tl_sc_sel")
    cur_sc_id=sc_opts[sel_sc]; cur_sc=next(sc for sc in scenarios if sc["id"]==cur_sc_id)
    if admin and sc_btn.button("➕ Baru",key="tl_sc_new"): st.session_state["tl_add_sc"]=True
    if st.session_state.get("tl_add_sc"):
        with st.form("sc_add",clear_on_submit=True):
            sc_nm2=st.text_input("Nama Skenario *"); sc_ds2=st.text_area("Deskripsi",height=56)
            b1c,b2c=st.columns(2)
            if b1c.form_submit_button("➕ Buat"):
                if sc_nm2: L.create_scenario(trip_id,sc_nm2,sc_ds2); st.session_state.pop("tl_add_sc",None); st.success("✅"); st.rerun()
            if b2c.form_submit_button("✖ Batal"): st.session_state.pop("tl_add_sc",None); st.rerun()
    if cur_sc.get("deskripsi"): alert("📝 {}".format(cur_sc["deskripsi"]),"info")
    if admin:
        with st.expander("⚙️ Kelola Skenario Ini"):
            with st.form("sc_edit_{}".format(cur_sc_id)):
                ec1,ec2=st.columns(2)
                en_sc=ec1.text_input("Nama",value=cur_sc["nama"])
                ed_sc=ec2.text_area("Deskripsi",value=cur_sc.get("deskripsi","") or "",height=56)
                if st.form_submit_button("💾 Simpan"): L.update_scenario(cur_sc_id,en_sc,ed_sc); st.success("✅"); st.rerun()
            if len(scenarios)>1:
                confirm_del("sc_{}".format(cur_sc_id),lambda sid=cur_sc_id:L.delete_scenario(sid),"🗑️ Hapus Skenario","Hapus skenario beserta semua kegiatannya?")
            else: st.caption("Minimal satu skenario harus ada.")
    msep()
    tabs=st.tabs(["🗓️ Timeline Visual","➕ Tambah Kegiatan","✏️ Edit / Hapus"] if admin else ["🗓️ Timeline Visual"])
    days_data=L.get_timeline_by_scenario(trip_id,cur_sc_id)
    with tabs[0]:
        if not days_data: alert("Skenario ini belum punya kegiatan. {}".format("Tambah di tab ➕." if admin else ""),"info")
        else:
            total_ev=sum(len(v) for v in days_data.values())
            st.markdown("**{} kegiatan di {} hari**".format(total_ev,len(days_data)))
            for hari in sorted(days_data.keys()):
                tgl_hari=tb+timedelta(days=hari-1); events=days_data[hari]
                with st.expander("📅 Hari {} — {}  ({} kegiatan)".format(hari,tgl_hari.strftime("%A, %d %b %Y"),len(events)),expanded=(hari==1)):
                    for ev in events:
                        cat=ev.get("kategori","Lainnya"); color=TCAT_CO.get(cat,"#64748b"); icon=TCAT_IC.get(cat,"📍")
                        jm=str(ev["jam_mulai"])[:5] if ev.get("jam_mulai") else ""; js=str(ev["jam_selesai"])[:5] if ev.get("jam_selesai") else ""
                        jmk=str(ev.get("jam_mulai_kira",""))[:5] if ev.get("jam_mulai_kira") else ""; jsk=str(ev.get("jam_selesai_kira",""))[:5] if ev.get("jam_selesai_kira") else ""
                        jam_s=(jm+"~"+jmk if jm and jmk else jm or "—"); jam_e=(js+"~"+jsk if js and jsk else js)
                        jam_str=jam_s+(" → {}".format(jam_e) if jam_e else "")
                        st.markdown("""<div style="display:flex;gap:14px;margin-bottom:10px;align-items:flex-start;">
  <div style="min-width:72px;text-align:right;font-size:11px;font-weight:700;color:{c};font-family:IBM Plex Mono,monospace;">{jam}</div>
  <div style="width:10px;min-width:10px;display:flex;flex-direction:column;align-items:center;">
    <div style="width:10px;height:10px;border-radius:50%;background:{c};margin-top:1px;"></div>
    <div style="width:2px;flex:1;background:{c};opacity:.25;min-height:24px;"></div>
  </div>
  <div style="background:var(--card);border:1px solid var(--border);border-left:3px solid {c};border-radius:10px;padding:10px 14px;flex:1;">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span style="font-size:17px;">{ic}</span>
      <span style="font-size:14px;font-weight:700;color:var(--txt);">{jd}</span>
      <span style="font-size:10px;font-weight:700;color:{c};background:{c}22;padding:2px 8px;border-radius:10px;border:1px solid {c}44;">{cat}</span>
    </div>
    {lok}{desk}
  </div>
</div>""".format(c=color,jam=jam_str,ic=icon,jd=ev["judul"],cat=cat,
                 lok="<div style='font-size:12px;color:var(--txt3);margin-top:5px;'>📍 {}</div>".format(ev["lokasi"]) if ev.get("lokasi") else "",
                 desk="<div style='font-size:12px;color:var(--txt2);margin-top:4px;line-height:1.5;'>{}</div>".format(ev["deskripsi"]) if ev.get("deskripsi") else ""),unsafe_allow_html=True)
    if not admin: _pw_end(); return
    with tabs[1]:
        with st.form("tl_add",clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1:
                judul_tl=st.text_input("Nama Kegiatan *",placeholder="misal: Start pendakian")
                cat_tl=st.selectbox("Kategori",TCATS)
                lokasi_tl=st.text_input("Lokasi")
                desk_tl=st.text_area("Deskripsi (opsional)",height=68)
            with c2:
                tgl_tl=st.date_input("Tanggal Kegiatan",value=tb,key="tl_add_tgl")
                hari_ke_calc=(tgl_tl-tb).days+1
                st.info("📅 Hari ke-{} dari {} hari trip".format(hari_ke_calc,durasi))
                urutan_tl=st.number_input("Urutan (dalam hari)",min_value=0,value=0)
            t1,t2,t3,t4=st.columns(4)
            jam_m_tl=t1.time_input("Mulai (dari)",value=dtime(6,0),key="tl_jm")
            jam_mk_tl=t2.time_input("Mulai (s/d kira²)",value=dtime(6,30),key="tl_jmk")
            jam_s_tl=t3.time_input("Selesai (dari)",value=dtime(8,0),key="tl_js")
            jam_sk_tl=t4.time_input("Selesai (s/d kira²)",value=dtime(9,0),key="tl_jsk")
            if st.form_submit_button("✅ Tambah Kegiatan",use_container_width=True):
                if not judul_tl: st.error("Nama kegiatan wajib!")
                else:
                    L.add_timeline(trip_id,dict(hari_ke=hari_ke_calc,tanggal=tgl_tl,
                        jam_mulai=jam_m_tl,jam_mulai_kira=jam_mk_tl if jam_mk_tl!=jam_m_tl else None,
                        jam_selesai=jam_s_tl if jam_s_tl!=jam_m_tl else None,
                        jam_selesai_kira=jam_sk_tl if jam_sk_tl!=jam_s_tl else None,
                        judul=judul_tl,deskripsi=desk_tl or None,
                        lokasi=lokasi_tl or None,kategori=cat_tl,
                        urutan=int(urutan_tl),scenario_id=cur_sc_id))
                    st.success("✅ Kegiatan ditambahkan!"); st.rerun()
    with tabs[2]:
        all_tl=L.get_timeline(trip_id); all_tl_sc=[e for e in all_tl if e.get("scenario_id")==cur_sc_id]
        if not all_tl_sc: alert("Skenario ini belum punya kegiatan.","info")
        else:
            ev_opts={"H{} — {} — {}".format(ev["hari_ke"],str(ev["jam_mulai"])[:5] if ev.get("jam_mulai") else "??:??",ev["judul"]):ev["id"] for ev in all_tl_sc}
            def _on_tl_ch():
                for k in [k2 for k2 in st.session_state if k2.startswith("tl_edit_")]: del st.session_state[k]
            esel_tl=st.selectbox("Pilih kegiatan",list(ev_opts.keys()),key="tl_ev_sel",on_change=_on_tl_ch)
            ev_d=next(e for e in all_tl_sc if e["id"]==ev_opts[esel_tl])
            import datetime as _dt2
            with st.form("tl_edit_{}".format(ev_d["id"])):
                c1,c2=st.columns(2)
                with c1:
                    ejd=st.text_input("Nama",value=ev_d["judul"])
                    ecat=st.selectbox("Kategori",TCATS,index=TCATS.index(ev_d["kategori"]) if ev_d["kategori"] in TCATS else 0)
                    elok=st.text_input("Lokasi",value=ev_d.get("lokasi") or "")
                    edsk=st.text_area("Deskripsi",value=ev_d.get("deskripsi") or "",height=68)
                with c2:
                    etgl=st.date_input("Tanggal",value=ev_d.get("tanggal") or tb,key="tl_edit_tgl")
                    e_hk=(etgl-tb).days+1; st.info("Hari ke-{}".format(e_hk))
                    eord=st.number_input("Urutan",min_value=0,value=ev_d.get("urutan") or 0)
                t1,t2,t3,t4=st.columns(4)
                ejm=t1.time_input("Mulai (dari)",value=_safe_time(ev_d.get("jam_mulai"),dtime(6,0)),key="tl_edit_jm")
                ejmk=t2.time_input("Mulai (kira²)",value=_safe_time(ev_d.get("jam_mulai_kira"),dtime(6,30)),key="tl_edit_jmk")
                ejs=t3.time_input("Selesai (dari)",value=_safe_time(ev_d.get("jam_selesai"),dtime(8,0)),key="tl_edit_js")
                ejsk=t4.time_input("Selesai (kira²)",value=_safe_time(ev_d.get("jam_selesai_kira"),dtime(9,0)),key="tl_edit_jsk")
                if st.form_submit_button("💾 Simpan",use_container_width=True):
                    L.update_timeline(ev_d["id"],dict(hari_ke=e_hk,tanggal=etgl,
                        jam_mulai=ejm,jam_mulai_kira=ejmk if ejmk!=ejm else None,
                        jam_selesai=ejs if ejs!=ejm else None,
                        jam_selesai_kira=ejsk if ejsk!=ejs else None,
                        judul=ejd,deskripsi=edsk or None,lokasi=elok or None,
                        kategori=ecat,urutan=int(eord),scenario_id=cur_sc_id))
                    st.success("✅ Diperbarui!"); st.rerun()
            confirm_del("tl_ev_{}".format(ev_d["id"]),lambda eid=ev_d["id"]:L.delete_timeline(eid),"🗑️ Hapus Kegiatan","Hapus kegiatan ini?")
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: LOGISTIK
# ═══════════════════════════════════════════════════════════════════════════════
def page_logistik():
    _pw()
    ph("🍱","Logistik Makanan","Perencanaan konsumsi dan logistik makanan trip")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; admin=is_admin_user(); durasi=trip.get("durasi_hari") or 1
    items=L.get_logistik(trip_id)
    total_est=sum(float(i["estimasi_harga"])*float(i["jumlah"]) for i in items)
    LCATS=["Sarapan","Makan Siang","Makan Malam","Snack","Minuman","Bumbu","Lainnya"]
    LIC={"Sarapan":"🌅","Makan Siang":"☀️","Makan Malam":"🌙","Snack":"🍫","Minuman":"💧","Bumbu":"🧂","Lainnya":"📦"}
    if items:
        c1,c2,c3=st.columns(3)
        c1.metric("Total Item",len(items)); c2.metric("Est. Total",L.fmt_rp(total_est)); c3.metric("Hari Trip","{} hari".format(durasi))
    if not items: alert("Belum ada item logistik. Tambahkan di bawah.","info")
    else:
        by_hari={}
        for i in items: by_hari.setdefault(i["hari_ke"],[]).append(i)
        for hari in sorted(by_hari.keys()):
            hi=by_hari[hari]; ht=sum(float(i["estimasi_harga"])*float(i["jumlah"]) for i in hi)
            with st.expander("📅 Hari ke-{}  ·  {} item  ·  Est. {}".format(hari,len(hi),L.fmt_rp(ht)),expanded=(hari==1)):
                by_kat={}
                for i in hi: by_kat.setdefault(i["kategori"],[]).append(i)
                for kat in LCATS:
                    ki=by_kat.get(kat,[])
                    if not ki: continue
                    st.markdown("<div style='font-size:11px;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;margin:10px 0 6px;'>{} {}</div>".format(LIC.get(kat,"📦"),kat),unsafe_allow_html=True)
                    for it in ki:
                        ht2=float(it["estimasi_harga"])*float(it["jumlah"])
                        cn,cq,ch,ca=st.columns([4,2,2,1])
                        cn.markdown("<div style='font-size:13px;font-weight:600;color:var(--txt);padding:6px 0;'>{}</div>{}".format(it["nama_item"],"<div style='font-size:11px;color:var(--txt3);'>{}</div>".format(it["catatan"]) if it.get("catatan") else ""),unsafe_allow_html=True)
                        cq.markdown("<div style='font-size:12px;color:var(--txt2);padding:6px 0;'>{} {}</div>".format(it["jumlah"],it["satuan"]),unsafe_allow_html=True)
                        ch.markdown("<div style='font-size:12px;color:var(--accent2);font-family:IBM Plex Mono,monospace;padding:6px 0;font-weight:600;'>{}</div>".format(L.fmt_rp(ht2)),unsafe_allow_html=True)
                        with ca:
                            if admin: confirm_del("log_{}".format(it["id"]),lambda lid=it["id"]:L.delete_logistik(lid),"🗑️")
                        st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:2px 0;'>",unsafe_allow_html=True)
    if admin:
        msep()
        t1,t2=st.tabs(["➕ Tambah Item","✏️ Edit"])
        with t1:
            with st.form("log_add",clear_on_submit=True):
                c1,c2=st.columns(2)
                with c1:
                    ln=st.text_input("Nama Item *"); lk=st.selectbox("Kategori",LCATS); lh=st.number_input("Hari ke-",min_value=1,max_value=max(durasi,1),value=1)
                with c2:
                    lq=st.number_input("Jumlah",min_value=0.0,value=1.0,step=0.5); ls=st.text_input("Satuan",value="porsi/orang"); le=st.number_input("Est. Harga (Rp)",min_value=0,value=0,step=1000)
                lct=st.text_area("Catatan",height=56)
                if st.form_submit_button("➕ Tambah",use_container_width=True):
                    if not ln: st.error("Nama wajib!")
                    else: L.create_logistik(trip_id,dict(nama_item=ln,kategori=lk,jumlah=lq,satuan=ls,hari_ke=lh,estimasi_harga=le,catatan=lct)); st.success("✅"); st.rerun()
        with t2:
            if not items: st.caption("Belum ada item.")
            else:
                opts={"{} (H{}) — {}".format(i["nama_item"],i["hari_ke"],i["kategori"]):i["id"] for i in items}
                sel=st.selectbox("Pilih item",list(opts.keys())); it=next(i for i in items if i["id"]==opts[sel])
                with st.form("log_edit_{}".format(it["id"])):
                    c1,c2=st.columns(2)
                    with c1:
                        en=st.text_input("Nama",value=it["nama_item"]); ek=st.selectbox("Kategori",LCATS,index=LCATS.index(it["kategori"])); eh=st.number_input("Hari ke-",min_value=1,max_value=max(durasi,1),value=it["hari_ke"])
                    with c2:
                        eq=st.number_input("Jumlah",min_value=0.0,value=float(it["jumlah"]),step=0.5); es=st.text_input("Satuan",value=it["satuan"]); ee=st.number_input("Est. Harga",min_value=0,value=int(it["estimasi_harga"]),step=1000)
                    ect=st.text_area("Catatan",value=it.get("catatan") or "",height=56)
                    if st.form_submit_button("💾 Simpan",use_container_width=True):
                        L.update_logistik(it["id"],dict(nama_item=en,kategori=ek,jumlah=eq,satuan=es,hari_ke=eh,estimasi_harga=ee,catatan=ect)); st.success("✅"); st.rerun()
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MEDIS / P3K
# ═══════════════════════════════════════════════════════════════════════════════
def page_medis():
    _pw()
    ph("💊","P3K & Medis","Daftar obat-obatan dan peralatan medis")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; admin=is_admin_user()
    P3K_CATS=["Obat Umum","Luka & Perban","Antiseptik","Alat Medis","Suplemen","Darurat","Lainnya"]
    P3K_IC={"Obat Umum":"💊","Luka & Perban":"🩹","Antiseptik":"🧴","Alat Medis":"🩺","Suplemen":"💪","Darurat":"🚨","Lainnya":"📦"}
    items=L.get_p3k(trip_id)
    if not items and admin:
        if st.button("🌱 Isi dari Template Standar"):
            n=L.seed_p3k_from_template(trip_id); st.success("✅ {} item P3K standar ditambahkan!".format(n)); st.rerun()
    total=len(items); siap=sum(1 for i in items if i["sudah_disiapkan"]); pct=int(siap/total*100) if total else 0
    if items:
        c1,c2,c3=st.columns(3)
        c1.metric("Total Item",total); c2.metric("Sudah Disiapkan","{}/{}".format(siap,total)); c3.metric("Progress","{}%".format(pct))
        pb(pct,"green" if pct==100 else "orange" if pct>50 else "blue")
        st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
    if not items: alert("Belum ada item P3K. Klik template atau tambah manual.","info")
    else:
        by_kat={}
        for i in items: by_kat.setdefault(i["kategori"],[]).append(i)
        for kat in P3K_CATS:
            ki=by_kat.get(kat,[])
            if not ki: continue
            sk=sum(1 for i in ki if i["sudah_disiapkan"])
            with st.expander("{} {}  ·  {}/{} siap".format(P3K_IC.get(kat,"📦"),kat,sk,len(ki)),expanded=True):
                for it in ki:
                    done=bool(it["sudah_disiapkan"]); lbl_col={"Wajib":"red","Disarankan":"orange","Opsional":"gray"}.get(it["label"],"gray")
                    bg="rgba(34,197,94,.06)" if done else "var(--raised)"; bd="rgba(34,197,94,.4)" if done else "var(--border)"
                    bl="var(--green)" if done else "var(--border2)"; op="opacity:.55;" if done else ""; sth="text-decoration:line-through;" if done else ""
                    c_chk,c_info,c_del=st.columns([1,9,1])
                    with c_chk:
                        st.markdown("<div style='padding-top:6px;'>",unsafe_allow_html=True)
                        nv=st.checkbox("",value=done,key="p3k_{}".format(it["id"]),label_visibility="collapsed")
                        if nv!=done: L.toggle_p3k(it["id"],nv); st.rerun()
                        st.markdown("</div>",unsafe_allow_html=True)
                    with c_info:
                        st.markdown("<div style='background:{bg};border:1px solid {bd};border-left:3px solid {bl};border-radius:10px;padding:9px 14px;{op}{sth}'><div style='font-size:13px;font-weight:700;color:var(--txt);'>{nm}</div><div style='display:flex;gap:6px;align-items:center;margin-top:4px;flex-wrap:wrap;'>{lb}<span style='font-size:11px;color:var(--txt3);'>{jml} {sat}</span>{ct}</div></div>".format(
                            bg=bg,bd=bd,bl=bl,op=op,sth=sth,nm=it["nama_item"],lb=badge(it["label"],lbl_col),
                            jml=it["jumlah"],sat=it["satuan"],
                            ct="<span style='font-size:11px;color:var(--txt3);'>· {}</span>".format(it["catatan"]) if it.get("catatan") else ""),unsafe_allow_html=True)
                    with c_del:
                        if admin:
                            st.markdown("<div style='padding-top:6px;'>",unsafe_allow_html=True)
                            confirm_del("p3k_{}".format(it["id"]),lambda pid=it["id"]:L.delete_p3k(pid),"🗑️")
                            st.markdown("</div>",unsafe_allow_html=True)
    if admin:
        msep()
        t1,t2=st.tabs(["➕ Tambah Item","✏️ Edit"])
        with t1:
            with st.form("p3k_add",clear_on_submit=True):
                c1,c2=st.columns(2)
                with c1:
                    pn=st.text_input("Nama Item *"); pk=st.selectbox("Kategori",P3K_CATS); pl=st.selectbox("Label",["Wajib","Disarankan","Opsional"])
                with c2:
                    pq=st.number_input("Jumlah",min_value=1,value=1); ps=st.text_input("Satuan",value="tablet")
                pct_txt=st.text_area("Keterangan/Fungsi",height=56)
                if st.form_submit_button("➕ Tambah",use_container_width=True):
                    if not pn: st.error("Nama wajib!")
                    else: L.create_p3k(trip_id,dict(nama_item=pn,kategori=pk,jumlah=pq,satuan=ps,label=pl,catatan=pct_txt)); st.success("✅"); st.rerun()
        with t2:
            if not items: st.caption("Belum ada item.")
            else:
                opts={"{} — {}".format(i["nama_item"],i["kategori"]):i["id"] for i in items}
                sel=st.selectbox("Pilih item",list(opts.keys())); it=next(i for i in items if i["id"]==opts[sel])
                with st.form("p3k_edit_{}".format(it["id"])):
                    c1,c2=st.columns(2)
                    with c1:
                        en=st.text_input("Nama",value=it["nama_item"]); ek=st.selectbox("Kategori",P3K_CATS,index=P3K_CATS.index(it["kategori"])); el=st.selectbox("Label",["Wajib","Disarankan","Opsional"],index=["Wajib","Disarankan","Opsional"].index(it["label"]))
                    with c2:
                        eq=st.number_input("Jumlah",min_value=1,value=it["jumlah"]); es=st.text_input("Satuan",value=it["satuan"])
                    ect=st.text_area("Keterangan",value=it.get("catatan") or "",height=56)
                    if st.form_submit_button("💾 Simpan",use_container_width=True):
                        L.update_p3k(it["id"],dict(nama_item=en,kategori=ek,jumlah=eq,satuan=es,label=el,catatan=ect)); st.success("✅"); st.rerun()
                confirm_del("p3kd_{}".format(it["id"]),lambda pid=it["id"]:L.delete_p3k(pid),"🗑️ Hapus","Hapus {}?".format(it["nama_item"]))
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: NOTES
# ═══════════════════════════════════════════════════════════════════════════════
def page_notes():
    _pw()
    ph("📝","Catatan Trip","Catatan, pengumuman, dan info penting")
    trip=trip_selector()
    if not trip: _pw_end(); return
    trip_id=trip["id"]; admin=is_admin_user()
    notes=L.get_notes(trip_id)
    NTYPE=["Umum","Penting","Darurat","Info"]; NIC={"Umum":"📝","Penting":"📌","Darurat":"🚨","Info":"ℹ️"}
    NIC_COL={"Umum":"gray","Penting":"orange","Darurat":"red","Info":"blue"}
    tabs=st.tabs(["📋 Semua Catatan","➕ Tambah","✏️ Edit"])
    with tabs[0]:
        if not notes: alert("Belum ada catatan.","info")
        else:
            for n in notes:
                ic=NIC.get(n["tipe"],"📝"); col=NIC_COL.get(n["tipe"],"gray")
                tgl=n["dibuat_pada"].strftime("%d %b %Y %H:%M") if hasattr(n.get("dibuat_pada",""),"strftime") else str(n.get("dibuat_pada",""))
                st.markdown("""
<div class='card card-{col}'>
  <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;'>
    <div style='display:flex;align-items:center;gap:8px;'>
      <span style='font-size:18px;'>{ic}</span>
      <div>
        <div style='font-size:14px;font-weight:700;color:var(--txt);'>{jd}</div>
        <div style='font-size:11px;color:var(--txt3);margin-top:1px;'>{tgl} · {tp}</div>
      </div>
    </div>
    {admin_del}
  </div>
  <div style='font-size:13px;color:var(--txt2);line-height:1.6;'>{isi}</div>
</div>""".format(col=col,ic=ic,jd=n["judul"],tgl=tgl,tp=n["tipe"],isi=n["isi"],
                 admin_del=""),unsafe_allow_html=True)
                if admin:
                    b1,b2,_=st.columns([1,1,5])
                    with b1:
                        st.markdown('<div class="btn-warn">',unsafe_allow_html=True)
                        if st.button("✏️",key="ne_{}".format(n["id"])):
                            st.session_state["edit_note_id"]=n["id"]; st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)
                    with b2: confirm_del("note_{}".format(n["id"]),lambda nid=n["id"]:L.delete_note(nid),"🗑️","Hapus catatan?")
    with tabs[1]:
        if not admin: alert("Hanya admin yang bisa menambah catatan.","warning")
        else:
            with st.form("note_add",clear_on_submit=True):
                jd=st.text_input("Judul *"); tp=st.selectbox("Tipe",NTYPE)
                isi=st.text_area("Isi Catatan *",height=120)
                if st.form_submit_button("📝 Simpan Catatan",use_container_width=True):
                    if not jd or not isi: st.error("Judul dan isi wajib!")
                    else: L.add_note(trip_id,dict(judul=jd,tipe=tp,isi=isi)); st.success("✅ Catatan disimpan!"); st.rerun()
    with tabs[2]:
        if not admin: alert("Hanya admin.","warning")
        elif not notes: st.caption("Belum ada catatan.")
        else:
            opts={"{} — {}".format(n["judul"],n["tipe"]):n["id"] for n in notes}
            di=0
            if "edit_note_id" in st.session_state:
                ids=list(opts.values())
                if st.session_state["edit_note_id"] in ids: di=ids.index(st.session_state["edit_note_id"])
            sel=st.selectbox("Pilih catatan",list(opts.keys()),index=di)
            nd=next(n for n in notes if n["id"]==opts[sel])
            with st.form("note_edit_{}".format(nd["id"])):
                ejd=st.text_input("Judul",value=nd["judul"]); etp=st.selectbox("Tipe",NTYPE,index=NTYPE.index(nd["tipe"]))
                eisi=st.text_area("Isi",value=nd["isi"],height=120)
                if st.form_submit_button("💾 Simpan",use_container_width=True):
                    L.update_note(nd["id"],dict(judul=ejd,tipe=etp,isi=eisi)); st.success("✅ Diperbarui!"); st.rerun()
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: EXERCISES
# ═══════════════════════════════════════════════════════════════════════════════
def page_exercises():
    _pw()
    import os
    ph("💪","Latihan Fisik","Program latihan persiapan pendakian")
    admin=is_admin_user()
    ex_cats=L.get_exercise_categories() if hasattr(L,"get_exercise_categories") else []
    ex_cat_opts={"{} {}".format(ec["icon"],ec["nama"]):ec["id"] for ec in ex_cats}
    LEVELS=["Pemula","Menengah","Lanjutan"]
    LVL_COL={"Pemula":"#22c55e","Menengah":"#f59e0b","Lanjutan":"#ef4444"}
    LVL_BG ={"Pemula":"rgba(34,197,94,.12)","Menengah":"rgba(245,158,11,.12)","Lanjutan":"rgba(239,68,68,.12)"}

    # ── Admin: Add new ──
    if admin:
        with st.expander("➕ Tambah Latihan Baru",expanded=False):
            ex_cat_opts2={"{} {}".format(ec["icon"],ec["nama"]):ec["id"] for ec in ex_cats}
            with st.form("ex_new",clear_on_submit=True):
                c1,c2=st.columns(2)
                with c1:
                    enm=st.text_input("Nama Latihan *",placeholder="misal: Squat Pendakian")
                    ecat=st.selectbox("Kategori *",list(ex_cat_opts2.keys()) if ex_cat_opts2 else ["—"])
                    efok=st.text_input("Fokus/Tujuan",placeholder="Daya tahan kaki, keseimbangan...")
                    elvl=st.selectbox("Level",LEVELS)
                with c2:
                    edur=st.number_input("Durasi (mnt)",min_value=1,value=30)
                    ekal=st.number_input("Kalori Estimasi",min_value=0,value=0)
                    eotot=st.text_input("Otot Utama",placeholder="Quadriceps, Glutes...")
                    ealat=st.text_input("Peralatan",value="Tanpa Alat")
                eins=st.text_area("Instruksi (satu langkah per baris)",height=100,placeholder="Berdiri tegak\nTekuk lutut 90°\n...")
                etip=st.text_area("Tips",height=60,placeholder="Tips keamanan dan teknik...")
                st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                if st.form_submit_button("✅ Tambah Latihan",use_container_width=True):
                    if not enm: st.error("Nama wajib!")
                    elif not ex_cat_opts2: st.error("Buat kategori latihan dulu!")
                    else:
                        L.create_exercise(dict(nama_latihan=enm,category_id=ex_cat_opts2.get(ecat),
                            fokus=efok,level=elvl,durasi_menit=edur,kalori_estimasi=ekal,
                            otot_utama=eotot,peralatan=ealat,instruksi=eins,tips=etip))
                        st.success("✅ **{}** ditambahkan!".format(enm)); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

    # ── Filters ──
    fc1,fc2,fc3=st.columns(3)
    f_cat=fc1.selectbox("Kategori",["Semua"]+list(ex_cat_opts.keys()),key="ex_fc")
    f_lvl=fc2.selectbox("Level",["Semua"]+LEVELS,key="ex_fl")
    f_q=fc3.text_input("🔍 Cari","",key="ex_fq",placeholder="Nama latihan...")
    cat_id=ex_cat_opts.get(f_cat) if f_cat!="Semua" else None
    lvl=f_lvl if f_lvl!="Semua" else None
    exercises=L.get_exercises(cat_id,lvl,f_q)
    if not exercises:
        alert("Belum ada latihan. {}".format("Tambahkan di atas." if admin else ""),"info")
        _pw_end(); return

    # Group by category
    by_cat={}
    for ex in exercises: by_cat.setdefault((ex.get("cat_icon","💪"),ex.get("nama_kategori","Umum")),[]).append(ex)

    for (cic,cnm),exes in sorted(by_cat.items()):
        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;margin:20px 0 10px;"
            "padding-bottom:8px;border-bottom:2px solid #243044;'>"
            "<span style='font-size:22px;'>{}</span>"
            "<span style='font-size:15px;font-weight:800;color:#e2eaf5;'>{}</span>"
            "<span style='font-size:11px;color:#4a6080;margin-left:4px;'>· {} latihan</span>"
            "</div>".format(cic,cnm,len(exes)),unsafe_allow_html=True)

        for ex in exes:
            lvl_c=LVL_COL.get(ex["level"],"#64748b")
            lvl_bg=LVL_BG.get(ex["level"],"rgba(100,116,139,.12)")
            otot=ex.get("otot_utama","") or ""
            alat=ex.get("peralatan","Tanpa Alat") or "Tanpa Alat"
            img_url=ex.get("gambar_url") or ex.get("image_url") or ""
            open_key="ex_open_{}".format(ex["id"])
            is_open=st.session_state.get(open_key,False)

            # ── Full card in pure HTML ──────────────────────────────────────
            img_html=""
            if img_url:
                img_html="<div style='width:100%;height:180px;overflow:hidden;border-radius:10px 10px 0 0;background:#0b0f14;margin-bottom:0;'><img src='{}' style='width:100%;height:100%;object-fit:cover;opacity:.88;display:block;'></div>".format(img_url)

            stats_chips=(
                "<span style='background:#1c2638;border:1px solid #2e3f58;border-radius:20px;"
                "padding:5px 12px;font-size:12px;color:#8aa0c0;font-weight:600;'>⏱️ {} mnt</span>"
                "<span style='background:#1c2638;border:1px solid #2e3f58;border-radius:20px;"
                "padding:5px 12px;font-size:12px;color:#8aa0c0;font-weight:600;'>🔥 {} kal</span>".format(
                ex["durasi_menit"],ex["kalori_estimasi"])
            )
            if ex.get("fokus"):
                stats_chips+="<span style='background:#1c2638;border:1px solid #2e3f58;border-radius:20px;padding:5px 12px;font-size:12px;color:#8aa0c0;font-weight:600;'>🎯 {}</span>".format(ex["fokus"])
            if alat!="Tanpa Alat":
                stats_chips+="<span style='background:#1c2638;border:1px solid #2e3f58;border-radius:20px;padding:5px 12px;font-size:12px;color:#8aa0c0;font-weight:600;'>🔧 {}</span>".format(alat)

            otot_row=""
            if otot:
                otot_row="<div style='margin-top:10px;font-size:11px;color:#4a6080;'><span style='color:#3b82f650;'>▸</span> 💪 Otot: <span style='color:#6b8ab0;'>{}</span></div>".format(otot)

            card_html=(
                "<div style='background:#161e2a;border:1px solid #243044;border-left:4px solid {lvl_c};"
                "border-radius:14px;margin-bottom:16px;overflow:hidden;'>"
                "{img}"
                "<div style='padding:16px 20px 14px;'>"
                "<div style='display:flex;align-items:flex-start;justify-content:space-between;gap:10px;'>"
                "<div style='flex:1;'>"
                "<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>"
                "<span style='background:{lvl_bg};color:{lvl_c};border:1px solid {lvl_c}50;"
                "padding:4px 14px;border-radius:20px;font-size:11px;font-weight:800;"
                "font-family:IBM Plex Mono,monospace;letter-spacing:.5px;flex-shrink:0;'>{lvl}</span>"
                "<span style='font-size:17px;font-weight:800;color:#e2eaf5;line-height:1.3;'>{nm}</span>"
                "</div>"
                "<div style='display:flex;gap:8px;flex-wrap:wrap;'>{chips}</div>"
                "{otot}"
                "</div>"
                "</div>"
                "</div></div>"
            ).format(lvl_c=lvl_c,lvl_bg=lvl_bg,lvl=ex["level"],nm=ex["nama_latihan"],
                     img=img_html,chips=stats_chips,otot=otot_row)
            st.markdown(card_html,unsafe_allow_html=True)

            # Action button OUTSIDE html using st.button
            btn_lbl=("✏️ Edit" if admin else "👁️ Detail")+" — "+ex["nama_latihan"]
            btn_icon="✏️ Edit" if admin else "👁️ Detail"
            col_l,col_r=st.columns([9,1])
            with col_r:
                st.markdown("<div style='margin-top:-58px;'>",unsafe_allow_html=True)
                if st.button(btn_icon,key="ex_btn_{}".format(ex["id"]),use_container_width=True,
                             help="Edit" if admin else "Lihat detail"):
                    st.session_state[open_key]=not is_open; st.rerun()
                st.markdown("</div>",unsafe_allow_html=True)
            st.markdown("<div style='height:2px'></div>",unsafe_allow_html=True)

            # ── Inline detail / edit panel ───────────────────────────────────
            if is_open:
                st.markdown(
                    "<div style='background:#111720;border:1px solid #3b82f640;"
                    "border-left:4px solid #3b82f6;border-radius:12px;padding:20px;margin:-6px 0 16px;'>",
                    unsafe_allow_html=True)
                if admin:
                    ex_cat_opts3={"{} {}".format(ec["icon"],ec["nama"]):ec["id"] for ec in ex_cats}
                    with st.form("ex_edit_{}".format(ex["id"])):
                        r1,r2=st.columns(2)
                        with r1:
                            enm2=st.text_input("Nama",value=ex["nama_latihan"])
                            cur_c=next((k for k,v in ex_cat_opts3.items() if v==ex["category_id"]),list(ex_cat_opts3.keys())[0] if ex_cat_opts3 else "")
                            ecat2=st.selectbox("Kategori",list(ex_cat_opts3.keys()),index=list(ex_cat_opts3.keys()).index(cur_c) if cur_c in ex_cat_opts3 else 0)
                            efok2=st.text_input("Fokus",value=ex.get("fokus",""))
                            elvl2=st.selectbox("Level",LEVELS,index=LEVELS.index(ex["level"]))
                        with r2:
                            edur2=st.number_input("Durasi (mnt)",min_value=1,value=ex["durasi_menit"])
                            ekal2=st.number_input("Kalori",min_value=0,value=ex["kalori_estimasi"])
                            eotot2=st.text_input("Otot Utama",value=ex.get("otot_utama",""))
                            ealat2=st.text_input("Peralatan",value=ex.get("peralatan","Tanpa Alat"))
                        eimg2=st.text_input("🖼️ URL Gambar (opsional)",value=ex.get("gambar_url") or ex.get("image_url") or "",placeholder="https://images.example.com/foto.jpg")
                        eins2=st.text_area("📋 Instruksi (satu langkah per baris)",value=ex.get("instruksi","") or "",height=110)
                        etip2=st.text_area("💡 Tips",value=ex.get("tips","") or "",height=68)
                        ba2,bb2=st.columns(2)
                        with ba2:
                            st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                            if st.form_submit_button("💾 Simpan",use_container_width=True):
                                L.update_exercise(ex["id"],dict(
                                    nama_latihan=enm2,category_id=ex_cat_opts3.get(ecat2,ex["category_id"]),
                                    fokus=efok2,level=elvl2,durasi_menit=edur2,kalori_estimasi=ekal2,
                                    otot_utama=eotot2,peralatan=ealat2,instruksi=eins2,tips=etip2,
                                    gambar_url=eimg2 or None))
                                st.session_state.pop(open_key,None); st.success("✅ Diperbarui!"); st.rerun()
                            st.markdown('</div>',unsafe_allow_html=True)
                        with bb2:
                            st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                            if st.form_submit_button("🗑️ Hapus",use_container_width=True):
                                L.delete_exercise(ex["id"]); st.session_state.pop(open_key,None); st.rerun()
                            st.markdown('</div>',unsafe_allow_html=True)
                else:
                    # Read-only detail
                    if ex.get("instruksi"):
                        st.markdown("<div style='font-size:12px;font-weight:700;color:#4a6080;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;'>📋 Cara Melakukan</div>",unsafe_allow_html=True)
                        steps=[s.strip() for s in ex["instruksi"].split("\n") if s.strip()]
                        step_html="".join(
                            "<div style='display:flex;gap:14px;padding:10px 0;border-bottom:1px solid #1c2638;align-items:flex-start;'>"
                            "<span style='background:linear-gradient(135deg,#3b82f6,#6366f1);color:#fff;border-radius:50%;width:26px;height:26px;min-width:26px;"
                            "display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;margin-top:1px;flex-shrink:0;'>{n}</span>"
                            "<span style='font-size:13px;color:#e2eaf5;line-height:1.65;'>{s}</span>"
                            "</div>".format(n=i,s=step)
                            for i,step in enumerate(steps,1))
                        st.markdown(step_html,unsafe_allow_html=True)
                    if ex.get("tips"):
                        st.markdown(
                            "<div style='background:rgba(245,158,11,.08);border-left:3px solid #f59e0b;"
                            "border-radius:8px;padding:14px 18px;font-size:13px;color:#fcd34d;margin-top:16px;line-height:1.7;'>"
                            "💡 <b>Tips:</b> {}</div>".format(ex["tips"]),unsafe_allow_html=True)
                st.markdown("</div>",unsafe_allow_html=True)


    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS (Kategori + Master Item + Checklist Master)
# ═══════════════════════════════════════════════════════════════════════════════
def page_categories():
    if not is_admin_user(): alert("Hanya admin.","warning"); return
    tabs=st.tabs(["➕ Tambah","📋 Kelola"])
    with tabs[0]:
        with st.form("cat_new",clear_on_submit=True):
            c1,c2,c3=st.columns(3)
            nm=c1.text_input("Nama *"); jn=c2.selectbox("Jenis",["Alat","Logistik","Simaksi","Transportasi","Lainnya"]); ic=c3.text_input("Icon","📦")
            ds=st.text_area("Deskripsi",height=68); ur=st.number_input("Urutan",min_value=0,value=10)
            if st.form_submit_button("✅ Tambah",use_container_width=True):
                if not nm: st.error("Nama wajib!")
                else:
                    try: L.create_category(dict(nama_kategori=nm,jenis=jn,icon=ic,deskripsi=ds,urutan=ur)); st.success("✅"); st.rerun()
                    except: st.error("Nama sudah ada!")
    with tabs[1]:
        for c in L.get_categories():
            with st.expander("{} {} — {}".format(c["icon"],c["nama_kategori"],c["jenis"])):
                with st.form("ce_{}".format(c["id"])):
                    e1,e2,e3=st.columns(3)
                    en=e1.text_input("Nama",value=c["nama_kategori"],key="cn_{}".format(c["id"]))
                    ej=e2.selectbox("Jenis",["Alat","Logistik","Simaksi","Transportasi","Lainnya"],index=["Alat","Logistik","Simaksi","Transportasi","Lainnya"].index(c["jenis"]),key="cj_{}".format(c["id"]))
                    ei=e3.text_input("Icon",value=c["icon"] or "📦",key="ci_{}".format(c["id"]))
                    ed=st.text_area("Deskripsi",value=c.get("deskripsi") or "",key="cd_{}".format(c["id"]),height=68); eu=st.number_input("Urutan",value=c["urutan"] or 0,key="cu_{}".format(c["id"]))
                    if st.form_submit_button("💾 Simpan"): L.update_category(c["id"],dict(nama_kategori=en,jenis=ej,icon=ei,deskripsi=ed,urutan=eu)); st.success("✅"); st.rerun()
                confirm_del("cat_{}".format(c["id"]),lambda cid=c["id"]:L.delete_category(cid),"🗑️ Hapus","Hapus kategori {}?".format(c["nama_kategori"]))

def page_items():
    if not is_admin_user(): alert("Hanya admin.","warning"); return
    cats=L.get_categories(); cat_opts={"{} {}".format(c["icon"],c["nama_kategori"]):c["id"] for c in cats}
    cat_by_id={c["id"]:c for c in cats}

    # ── Tambah item baru ──
    with st.expander("➕ Tambah Item Master Baru", expanded=False):
        with st.form("im_new",clear_on_submit=True):
            c1,c2,c3=st.columns(3)
            nm=c1.text_input("Nama Item *",placeholder="misal: Carrier 60L")
            ck=c2.selectbox("Kategori *",list(cat_opts.keys()))
            st2=c3.text_input("Satuan","pcs")
            c4,c5,c6=st.columns(3)
            br=c4.number_input("Berat/unit (gram)",min_value=0,value=0)
            tj=c5.selectbox("Tujuan",["Personal","Kelompok"])
            lb=c6.selectbox("Label",["Wajib","Disarankan","Opsional"])
            ds=st.text_area("Deskripsi/Catatan (opsional)",height=56,placeholder="Keterangan tambahan...")
            st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
            if st.form_submit_button("✅ Tambah Item",use_container_width=True):
                if not nm: st.error("Nama wajib!")
                else:
                    L.create_item_master(dict(nama_item=nm,category_id=cat_opts[ck],satuan=st2,berat_gram=br,tujuan=tj,label=lb,deskripsi=ds))
                    st.success("✅ **{}** ditambahkan!".format(nm)); st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

    msep()

    # ── Filter ──
    st.markdown("<div style='background:#1c2638;border:1px solid #243044;border-radius:10px;padding:12px 14px;margin-bottom:14px;'>",unsafe_allow_html=True)
    fc1,fc2,fc3=st.columns(3)
    fcat=fc1.selectbox("Kategori",["Semua"]+list(cat_opts.keys()),key="im_fc")
    ftj=fc2.selectbox("Tujuan",["Semua","Personal","Kelompok"],key="im_ft")
    fq=fc3.text_input("🔍 Cari nama","",key="im_fq",placeholder="Ketik untuk filter...")
    st.markdown("</div>",unsafe_allow_html=True)
    catf=cat_opts.get(fcat) if fcat!="Semua" else None
    tjf=ftj if ftj!="Semua" else None
    all_items=L.get_items_master(catf,fq,tjf)

    # Group by category
    by_cat={}
    for item in all_items: by_cat.setdefault(item.get("nama_kategori","?"),[]).append(item)

    st.markdown("<div style='font-size:12px;color:#4a6080;margin-bottom:12px;'>Menampilkan <b style='color:#e2eaf5;'>{}</b> item dalam {} kategori</div>".format(len(all_items),len(by_cat)),unsafe_allow_html=True)

    LBL_COL={"Wajib":"#ef4444","Disarankan":"#f59e0b","Opsional":"#64748b"}
    TJ_COL={"Kelompok":"#3b82f6","Personal":"#a855f7"}

    for cat_name,citems in sorted(by_cat.items()):
        cat_obj=cat_by_id.get(citems[0]["category_id"],{})
        cat_ic=cat_obj.get("icon","📦")
        st.markdown(
            "<div style='display:flex;align-items:center;gap:8px;padding:8px 0 6px;"
            "border-bottom:1px solid #243044;margin-bottom:8px;'>"
            "<span style='font-size:18px;'>{}</span>"
            "<span style='font-size:13px;font-weight:700;color:#e2eaf5;'>{}</span>"
            "<span style='font-size:11px;color:#4a6080;margin-left:4px;'>· {} item</span>"
            "</div>".format(cat_ic,cat_name,len(citems)),unsafe_allow_html=True)

        for item in citems:
            lb_c=LBL_COL.get(item["label"],"#64748b")
            tj_c=TJ_COL.get(item["tujuan"],"#64748b")
            berat_str=L.fmt_berat(item.get("berat_gram",0)) if item.get("berat_gram") else "—"
            # Item card header
            col_card,col_edit=st.columns([9,1])
            with col_card:
                st.markdown(
                    "<div style='background:#1c2638;border:1px solid #243044;border-radius:10px;"
                    "padding:12px 16px;display:flex;align-items:center;gap:14px;'>"
                    "<div style='width:40px;height:40px;background:{tj_c}18;border:1px solid {tj_c}40;"
                    "border-radius:9px;display:flex;align-items:center;justify-content:center;"
                    "font-size:18px;flex-shrink:0;'>{ic}</div>"
                    "<div style='flex:1;min-width:0;'>"
                    "<div style='font-size:13px;font-weight:700;color:#e2eaf5;margin-bottom:5px;'>{nm}</div>"
                    "<div style='display:flex;gap:6px;flex-wrap:wrap;align-items:center;'>"
                    "<span style='background:{lb_c}20;color:{lb_c};border:1px solid {lb_c}40;"
                    "padding:2px 8px;border-radius:12px;font-size:10px;font-weight:700;"
                    "font-family:IBM Plex Mono,monospace;'>{lb}</span>"
                    "<span style='background:{tj_c}18;color:{tj_c};border:1px solid {tj_c}40;"
                    "padding:2px 8px;border-radius:12px;font-size:10px;font-weight:700;"
                    "font-family:IBM Plex Mono,monospace;'>{tj}</span>"
                    "<span style='font-size:11px;color:#4a6080;'>⚖️ {brt}</span>"
                    "<span style='font-size:11px;color:#4a6080;'>📦 {sat}</span>"
                    "{ds}"
                    "</div></div>"
                    "</div>".format(
                        tj_c=tj_c,ic=item.get("icon",cat_ic),
                        nm=item["nama_item"],lb_c=lb_c,
                        lb=item["label"],tj=item["tujuan"],
                        brt=berat_str,sat=item["satuan"] or "pcs",
                        ds="<span style='font-size:11px;color:#4a6080;'>· {}</span>".format(item["deskripsi"][:40]) if item.get("deskripsi") else ""),
                    unsafe_allow_html=True)
            with col_edit:
                st.markdown("<div style='padding-top:4px;display:flex;flex-direction:column;gap:4px;'>",unsafe_allow_html=True)
                st.markdown('<div class="btn-warn">',unsafe_allow_html=True)
                if st.button("✏️",key="im_ed_btn_{}".format(item["id"]),use_container_width=True,help="Edit {}".format(item["nama_item"])):
                    ek="im_open_{}".format(item["id"])
                    st.session_state[ek]=not st.session_state.get(ek,False); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
                confirm_del("im_{}".format(item["id"]),lambda iid=item["id"]:L.delete_item_master(iid),"🗑️","Hapus {}?".format(item["nama_item"]))
                st.markdown("</div>",unsafe_allow_html=True)

            # Inline edit form — shows only when ✏️ clicked
            if st.session_state.get("im_open_{}".format(item["id"])):
                with st.container():
                    st.markdown(
                        "<div style='background:#161e2a;border:1px solid #3b82f640;"
                        "border-left:3px solid #3b82f6;border-radius:10px;padding:16px;margin:4px 0 8px;'>",
                        unsafe_allow_html=True)
                    with st.form("ie_{}".format(item["id"])):
                        r1c1,r1c2,r1c3=st.columns(3)
                        en=r1c1.text_input("Nama",value=item["nama_item"],key="in_{}".format(item["id"]))
                        cl2=list(cat_opts.keys())
                        ci=list(cat_opts.values()).index(item["category_id"]) if item["category_id"] in cat_opts.values() else 0
                        ec=r1c2.selectbox("Kategori",cl2,index=ci,key="ic_{}".format(item["id"]))
                        es=r1c3.text_input("Satuan",value=item["satuan"] or "pcs",key="is_{}".format(item["id"]))
                        r2c1,r2c2,r2c3=st.columns(3)
                        eb=r2c1.number_input("Berat (gram)",value=float(item.get("berat_gram") or 0),key="ib_{}".format(item["id"]))
                        et=r2c2.selectbox("Tujuan",["Personal","Kelompok"],index=["Personal","Kelompok"].index(item["tujuan"]),key="it_{}".format(item["id"]))
                        el=r2c3.selectbox("Label",["Wajib","Disarankan","Opsional"],index=["Wajib","Disarankan","Opsional"].index(item["label"]),key="il_{}".format(item["id"]))
                        ed=st.text_area("Deskripsi",value=item.get("deskripsi") or "",key="id_{}".format(item["id"]),height=56)
                        ba,bb=st.columns(2)
                        with ba:
                            st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                            if st.form_submit_button("💾 Simpan",use_container_width=True):
                                L.update_item_master(item["id"],dict(nama_item=en,category_id=cat_opts[ec],satuan=es,berat_gram=eb,tujuan=et,label=el,deskripsi=ed))
                                st.session_state.pop("im_open_{}".format(item["id"]),None)
                                st.success("✅ **{}** diperbarui!".format(en)); st.rerun()
                            st.markdown('</div>',unsafe_allow_html=True)
                        with bb:
                            st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                            if st.form_submit_button("🗑️ Hapus Item",use_container_width=True):
                                L.delete_item_master(item["id"])
                                st.session_state.pop("im_open_{}".format(item["id"]),None)
                                st.rerun()
                            st.markdown('</div>',unsafe_allow_html=True)
                    st.markdown("</div>",unsafe_allow_html=True)

            st.markdown("<div style='height:4px'></div>",unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)

def page_cl_master():
    if not is_admin_user(): alert("Hanya admin.","warning"); return
    trip=trip_selector()
    if not trip: return
    trip_id=trip["id"]; cats=L.get_categories()
    cat_opts={"{} {}".format(c["icon"],c["nama_kategori"]):c["id"] for c in cats}
    members=L.get_members(trip_id)
    member_opts={"🏕️ Semua Anggota (Checklist Kelompok)": None}
    for m in members: member_opts["👤 "+m["nama_lengkap"]]=m["id"]

    st.markdown("""
<div style='background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.25);border-left:3px solid #3b82f6;
border-radius:10px;padding:12px 16px;font-size:13px;color:#93c5fd;margin-bottom:16px;'>
💡 <b>Cara pakai:</b> Centang item yang ingin ditambahkan, atur jumlah, pilih target anggota, lalu klik <b>Assign</b>. Semua pilihan dikumpulkan dulu — tidak ada loading per centang.
</div>""", unsafe_allow_html=True)

    fc1,fc2,fc3,fc4=st.columns(4)
    fcat=fc1.selectbox("Kategori",["Semua"]+list(cat_opts.keys()),key="clm_fc")
    ftj=fc2.selectbox("Tujuan",["Semua","Personal","Kelompok"],key="clm_ft")
    fq=fc3.text_input("🔍 Cari","",key="clm_fq")
    fgrp=fc4.selectbox("Kelompokkan",["Default","Kategori","Tujuan","Label"],key="clm_grp")

    assign_target=st.selectbox("📋 Assign ke",list(member_opts.keys()),key="clm_target",
        help="Semua Anggota = tambah ke checklist kelompok. Pilih nama = tambah ke checklist personal orang itu.")
    assign_mid=member_opts[assign_target]

    catf=cat_opts.get(fcat) if fcat!="Semua" else None
    tjf=ftj if ftj!="Semua" else None
    all_items=L.get_items_master(catf,fq,tjf)

    if not all_items:
        alert("Tidak ada item master.","warning"); return

    if fgrp=="Default": grouped=[("","",all_items)]
    else:
        def _gkey(i):
            if fgrp=="Kategori": return (i.get("icon","📦"),i.get("nama_kategori","?"))
            if fgrp=="Tujuan": return ("🎯" if i["tujuan"]=="Kelompok" else "👤",i["tujuan"])
            if fgrp=="Label": return ("🏷️",i["label"])
            return ("","")
        by_g={}
        for i in all_items: k=_gkey(i); by_g.setdefault(k,[]).append(i)
        grouped=[(k[0],k[1],v) for k,v in sorted(by_g.items())]

    # ── FORM: semua checkbox+qty dalam satu form, tidak ada rerun per input ──
    with st.form("clm_form",clear_on_submit=True):
        item_inputs={}
        for g_ic,g_nm,g_items in grouped:
            if fgrp!="Default":
                st.markdown(
                    "<div style='font-size:10px;font-weight:700;color:#4a6080;text-transform:uppercase;"
                    "letter-spacing:1.5px;padding:10px 0 6px;border-bottom:1px solid #243044;"
                    "margin-bottom:8px;'>{} {} <span style='float:right;'>{} item</span></div>".format(
                    g_ic,g_nm,len(g_items)),unsafe_allow_html=True)
            for item in g_items:
                lb_c={"Wajib":"red","Disarankan":"orange","Opsional":"gray"}.get(item["label"],"gray")
                tj_c="blue" if item["tujuan"]=="Kelompok" else "purple"
                c1,c2,c3,c4,c5=st.columns([4,1.2,1.2,1.5,2])
                with c1:
                    chk=st.checkbox("{} {}".format(item.get("icon","📦"),item["nama_item"]),
                        value=False,key="clmf_{}".format(item["id"]))
                c2.markdown(badge(item["label"],lb_c),unsafe_allow_html=True)
                c3.markdown(badge(item["tujuan"],tj_c),unsafe_allow_html=True)
                with c4:
                    qty=st.number_input("Qty",min_value=1,max_value=99,value=1,
                        key="clmfq_{}".format(item["id"]),label_visibility="collapsed")
                c5.markdown("<span style='font-size:11px;color:#8aa0c0;'>{}</span>".format(
                    item.get("nama_kategori","")),unsafe_allow_html=True)
                item_inputs[item["id"]]=(chk,qty)

        st.markdown('<div style="height:8px"></div>',unsafe_allow_html=True)
        submitted=st.form_submit_button(
            "📋 Assign Item Terpilih ke {} ".format(assign_target),
            use_container_width=True)

    if submitted:
        qty_map={iid:q for iid,(chk,q) in item_inputs.items() if chk}
        if not qty_map:
            st.warning("⚠️ Tidak ada item yang dicentang.")
        else:
            if assign_mid is None:
                added=L.sync_master_to_checklist_with_qty(trip_id,qty_map)
            else:
                added=L.sync_master_to_personal_checklist(trip_id,assign_mid,qty_map)
            st.success("✅ {} item berhasil ditambahkan ke {}!".format(added,assign_target))
            st.rerun()

def page_settings():
    _pw()
    if not is_admin_user(): alert("Hanya admin yang bisa mengakses pengaturan.","warning"); _pw_end(); return
    ph("⚙️","Pengaturan","Konfigurasi sistem TrailLog")
    tabs=st.tabs(["🏷️ Kategori","📦 Master Item","📋 Checklist Master"])
    with tabs[0]: page_categories()
    with tabs[1]: page_items()
    with tabs[2]: page_cl_master()
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MASTER ANGGOTA
# ═══════════════════════════════════════════════════════════════════════════════
def _member_fields_full(prefix, d=None):
    d=d or {}
    sec("👤 Identitas")
    c1,c2,c3=st.columns(3)
    with c1:
        nm=st.text_input("Nama Lengkap *",value=d.get("nama_lengkap",""),key="{}_nm".format(prefix))
        pg=st.text_input("Nama Panggilan",value=d.get("nama_panggilan","") or "",key="{}_pg".format(prefix))
        nik=st.text_input("NIK *",value=d.get("nik","") or "",key="{}_nik".format(prefix),max_chars=16)
    with c2:
        ttl_disp=d.get("tempat_lahir","") or "—"
        st.markdown("<div style='font-size:12px;color:var(--txt2);margin-bottom:2px;'>Tempat Lahir</div><div style='font-size:13px;color:var(--txt);background:var(--raised);border:1px solid var(--border);border-radius:9px;padding:8px 12px;margin-bottom:8px;'>📍 {}</div>".format(ttl_disp),unsafe_allow_html=True)
        tgl=st.date_input("Tanggal Lahir *",value=d.get("tanggal_lahir",date(1995,1,1)),min_value=date(1900,1,1),key="{}_tgl".format(prefix))
        jk=st.selectbox("Jenis Kelamin *",["Laki-laki","Perempuan"],index=["Laki-laki","Perempuan"].index(d.get("jenis_kelamin","Laki-laki")),key="{}_jk".format(prefix))
    with c3:
        hp=st.text_input("No. HP *",value=d.get("no_hp","") or "",key="{}_hp".format(prefix))
        em=st.text_input("Email",value=d.get("email","") or "",key="{}_em".format(prefix))
        rp=st.text_area("Riwayat Penyakit (opsional)",value=d.get("riwayat_penyakit","") or "",height=80,key="{}_rp".format(prefix))
    sec("🆘 Kontak Darurat")
    k1,k2,k3=st.columns(3)
    HUB=["Orang Tua","Saudara","Pasangan","Teman","Lainnya"]
    kdn=k1.text_input("Nama Kontak *",value=d.get("kontak_darurat_nama","") or "",key="{}_kdn".format(prefix))
    kdh=k2.text_input("No. HP Kontak *",value=d.get("kontak_darurat_hp","") or "",key="{}_kdh".format(prefix))
    kdr=k3.selectbox("Hubungan *",HUB,index=HUB.index(d.get("kontak_darurat_hubungan","Orang Tua")) if d.get("kontak_darurat_hubungan","Orang Tua") in HUB else 0,key="{}_kdr".format(prefix))
    sec("📝 Catatan")
    ct=st.text_area("Catatan (opsional)",value=d.get("catatan","") or "",height=56,key="{}_ct".format(prefix))
    return dict(nama_lengkap=nm,nama_panggilan=pg or None,nik=nik,tanggal_lahir=tgl,jenis_kelamin=jk,no_hp=hp,email=em or None,riwayat_penyakit=rp or None,kontak_darurat_nama=kdn,kontak_darurat_hp=kdh,kontak_darurat_hubungan=kdr,catatan=ct or None)

def page_members_master():
    _pw()
    if not is_admin_user(): alert("Hanya admin.","warning"); _pw_end(); return
    ph("👤","Master Anggota","Database anggota global — pilih saat tambah ke trip tanpa isi ulang")
    tabs=st.tabs(["📋 Daftar","➕ Tambah Baru","✏️ Edit"])
    with tabs[0]:
        fq=st.text_input("🔍 Cari nama / email / HP","",key="mm_fq")
        masters=L.get_members_master(fq); st.markdown("**{} anggota terdaftar**".format(len(masters)))
        if not masters: alert("Belum ada. Tambahkan di tab ➕.","info")
        for mm in masters:
            usia=L.hitung_usia(mm.get("tanggal_lahir"))
            dom=", ".join(p for p in [mm.get("kelurahan_nama"),mm.get("kecamatan_nama"),mm.get("kota_nama"),mm.get("provinsi_nama")] if p) or "—"
            jk_ic="🧑" if mm.get("jenis_kelamin")=="Laki-laki" else "👩"
            medis_bar=""
            if mm.get("riwayat_penyakit"):
                medis_bar="<div style='background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:6px;padding:6px 10px;font-size:11px;color:#fca5a5;margin-top:8px;'>🏥 {}</div>".format(mm["riwayat_penyakit"])
            col_c,col_b=st.columns([9,1])
            with col_c:
                st.markdown(
                    "<div style='background:#161e2a;border:1px solid #243044;border-left:3px solid #3b82f6;"
                    "border-radius:12px;padding:14px 18px;'>"
                    "<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>"
                    "<div style='width:38px;height:38px;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3);"
                    "border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;'>{jk}</div>"
                    "<div style='flex:1;'><div style='font-size:15px;font-weight:700;color:#e2eaf5;'>{nm}</div>"
                    "<div style='font-size:11px;color:#4a6080;margin-top:2px;'>@{pan} · {usia}</div></div>"
                    "<div style='text-align:right;font-size:11px;color:#4a6080;'><div>📱 {hp}</div><div>📧 {em}</div></div>"
                    "</div>"
                    "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:11px;'>"
                    "<div style='background:#1c2638;border-radius:8px;padding:8px 10px;'>"
                    "<span style='color:#4a6080;font-size:9px;display:block;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;'>🪪 Identitas</span>"
                    "<span style='color:#8aa0c0;'>NIK: {nik}</span><br>"
                    "<span style='color:#8aa0c0;'>TTL: {ttl}</span></div>"
                    "<div style='background:#1c2638;border-radius:8px;padding:8px 10px;'>"
                    "<span style='color:#4a6080;font-size:9px;display:block;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;'>📞 Darurat</span>"
                    "<span style='color:#8aa0c0;'>{kdn} ({kdh})</span><br>"
                    "<span style='color:#8aa0c0;'>📱 {kdhp}</span></div>"
                    "<div style='background:#1c2638;border-radius:8px;padding:8px 10px;'>"
                    "<span style='color:#4a6080;font-size:9px;display:block;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;'>🏠 Domisili</span>"
                    "<span style='color:#8aa0c0;'>{dom}</span></div>"
                    "</div>{medis}</div>".format(
                        jk=jk_ic,nm=mm["nama_lengkap"],
                        pan=mm.get("nama_panggilan") or mm["nama_lengkap"].split()[0],
                        usia="{} thn".format(usia) if usia else "—",
                        hp=mm.get("no_hp") or "—",em=mm.get("email") or "—",
                        nik=mm.get("nik") or "—",
                        ttl="{}, {}".format(mm.get("tempat_lahir") or "—",str(mm["tanggal_lahir"]) if mm.get("tanggal_lahir") else ""),
                        kdn=mm.get("kontak_darurat_nama") or "—",kdh=mm.get("kontak_darurat_hubungan") or "—",
                        kdhp=mm.get("kontak_darurat_hp") or "—",dom=dom,medis=medis_bar),
                    unsafe_allow_html=True)
            with col_b:
                st.markdown("<div style='padding-top:14px;display:flex;flex-direction:column;gap:6px;'>",unsafe_allow_html=True)
                st.markdown('<div class="btn-warn">',unsafe_allow_html=True)
                if st.button("✏️",key="emm_{}".format(mm["id"]),help="Edit {}".format(mm["nama_lengkap"]),use_container_width=True):
                    st.session_state["edit_mm_id"]=mm["id"]; st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
                confirm_del("mm_{}".format(mm["id"]),lambda mid=mm["id"]:L.delete_member_master(mid),"🗑️","Hapus {}?".format(mm["nama_lengkap"]))
                st.markdown("</div>",unsafe_allow_html=True)
            st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)
    with tabs[1]:
        _api_status_indicator(); sec("📍 Tempat Lahir")
        ttl_new=_tempat_lahir_selectbox("mm_new",""); sec("🏠 Domisili"); wil_new=wilayah_form("mm_new")
        al_new=st.text_area("Alamat Lengkap *",height=68,key="mm_new_al"); msep()
        with st.form("mm_new_form",clear_on_submit=True):
            fd=_member_fields_full("mmf_new")
            st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
            if st.form_submit_button("✅ Simpan Anggota",use_container_width=True):
                if not fd["nama_lengkap"]: st.error("Nama wajib!")
                else:
                    fd["tempat_lahir"]=ttl_new or "—"; fd.update(wil_new); fd["alamat_lengkap"]=al_new
                    L.create_member_master(fd)
                    if fd.get("email"): L.create_user_if_not_exist(fd["email"])
                    st.success("✅ Anggota ditambahkan!")
                    for k in [k2 for k2 in st.session_state if k2.startswith("mm_new_") or k2.startswith("mmf_new_")]: del st.session_state[k]
                    st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
    with tabs[2]:
        masters2=L.get_members_master()
        if not masters2: st.caption("Belum ada anggota.")
        else:
            opts2={m["nama_lengkap"]:m["id"] for m in masters2}; di2=0
            if "edit_mm_id" in st.session_state:
                ids2=list(opts2.values())
                if st.session_state["edit_mm_id"] in ids2: di2=ids2.index(st.session_state["edit_mm_id"])
            def _on_mm_sel():
                to_del=[k for k in st.session_state if k.startswith("mm_edit_") or k.startswith("mmf_edit_")]
                for k in to_del: del st.session_state[k]
            esel2=st.selectbox("🔍 Pilih Anggota yang akan Diedit",list(opts2.keys()),index=di2,key="mm_edit_sel",on_change=_on_mm_sel)
            mm_data=L.get_member_master(opts2[esel2])
            if mm_data:
                mmk=str(mm_data["id"])
                jk_ic3="🧑" if mm_data.get("jenis_kelamin")=="Laki-laki" else "👩"
                usia3=L.hitung_usia(mm_data.get("tanggal_lahir"))
                st.markdown(
                    "<div style='background:#1c2638;border:1px solid #243044;border-left:4px solid #3b82f6;"
                    "border-radius:12px;padding:14px 18px;margin-bottom:16px;'>"
                    "<div style='font-size:11px;color:#4a6080;margin-bottom:6px;'>✏️ Mengedit master anggota:</div>"
                    "<div style='display:flex;align-items:center;gap:12px;'>"
                    "<span style='font-size:28px;'>{jk}</span>"
                    "<div><div style='font-size:15px;font-weight:800;color:#e2eaf5;'>{nm}</div>"
                    "<div style='font-size:12px;color:#8aa0c0;margin-top:3px;'>NIK: {nik} · {usia} · {hp}</div>"
                    "</div></div></div>".format(
                        jk=jk_ic3,nm=mm_data["nama_lengkap"],
                        nik=mm_data.get("nik") or "—",usia=usia3 or "—",hp=mm_data.get("no_hp") or "—"),
                    unsafe_allow_html=True)
                pfx2="mm_edit_{}".format(mmk)
                _api_status_indicator()
                sec("📍 Tempat Lahir")
                ettl2=_tempat_lahir_selectbox(pfx2, mm_data.get("tempat_lahir",""))
                sec("🏠 Domisili")
                ewil2=wilayah_form(pfx2, mm_data)
                eal2=st.text_area("Alamat Lengkap *",value=mm_data.get("alamat_lengkap","") or "",height=68,key="{}_al".format(pfx2))
                msep()
                with st.form("mm_edit_{}_form".format(mmk)):
                    efd2=_member_fields_full("mmf_edit_{}".format(mmk), mm_data)
                    st.markdown('<div class="btn-ok">',unsafe_allow_html=True)
                    if st.form_submit_button("💾 Simpan Perubahan",use_container_width=True):
                        efd2["tempat_lahir"]=ettl2 or mm_data.get("tempat_lahir","—")
                        efd2.update(ewil2); efd2["alamat_lengkap"]=eal2
                        L.update_member_master(mm_data["id"],efd2)
                        st.success("✅ **{}** berhasil diperbarui!".format(efd2.get("nama_lengkap","")))
                        st.session_state.pop("edit_mm_id",None)
                        st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)
    _pw_end()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def _init_once():
    init_database(); init_timeline_table(); init_bank_table(); seed_from_sql()
    return True

def main():
    try:
        _init_once()
    except Exception as e:
        st.error("❌ Gagal konek ke database Supabase: {}".format(e))
        st.info("Pastikan secrets.toml sudah benar dan Supabase project aktif.")
        st.stop()

    _check_localstorage_restore()
    if not st.session_state.get("logged_in_email"):
        page_login(); return
    _save_session_to_url()
    page=render_sidebar()
    page_map={
        "dashboard":page_dashboard,"trips":page_trips,"timeline":page_timeline,
        "members":page_members,"members_master":page_members_master,
        "biaya":page_biaya,"rekap":page_rekap,"payments":page_payments,
        "cl_group":page_cl_group,"cl_personal":page_cl_personal,
        "bawa_apa":page_bawa_apa,"berat":page_berat,"notes":page_notes,
        "exercises":page_exercises,"logistik":page_logistik,"medis":page_medis,
        "settings":page_settings,"categories":page_categories,
        "items":page_items,"cl_master":page_cl_master,
    }
    page_map.get(page,page_dashboard)()
    toast=st.session_state.pop("_toast",None)
    if toast: st.toast(toast)

if __name__=="__main__":
    main()