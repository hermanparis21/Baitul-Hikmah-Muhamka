import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
# Library baru untuk scan
from streamlit_barcode_scanner import st_barcode_scanner 

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Perpus Baitul Hikmah", layout="wide", page_icon="🕌")

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. CSS CUSTOM ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .digital-card {
        background: linear-gradient(135deg, #064e3b 0%, #10b981 100%);
        color: white; padding: 30px; border-radius: 20px; text-align: center;
        border: 2px solid #fcd34d;
    }
    .scan-area {
        border: 3px dashed #10b981; padding: 20px; border-radius: 15px; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA MASTER & HELPER ---
LIST_KELAS = [f"{t} {h}" for t in ['X', 'XI', 'XII'] for h in ['A','B','C','D','E','F','G']]
DENDA_PER_HARI = 500 

def get_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0).fillna("")
    except:
        return pd.DataFrame()

def hitung_selisih_hari(tgl_kembali):
    if not tgl_kembali: return 0
    if isinstance(tgl_kembali, str):
        try: tgl_kembali = datetime.strptime(tgl_kembali, '%Y-%m-%d').date()
        except: return 0
    hari_ini = date.today()
    return (hari_ini - tgl_kembali).days if hari_ini > tgl_kembali else 0

# --- 5. LOGIKA LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🕌 E-Perpus Baitul Hikmah")
    tab_l, tab_r = st.tabs(["🔐 Login", "📝 Registrasi"])
    with tab_l:
        with st.form("l_form"):
            u_in = st.text_input("Username / NIS").strip()
            p_in = st.text_input("Password", type="password").strip()
            if st.form_submit_button("Masuk"):
                df_u = get_data("users")
                match = df_u[(df_u['username'].astype(str) == u_in) & (df_u['password'].astype(str) == p_in)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_info = match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("NIS/Password Salah")
    with tab_r:
        # (Fitur Registrasi tetap sama seperti sebelumnya)
        pass 

# --- 6. HALAMAN UTAMA ---
else:
    u = st.session_state.user_info
    role = u.get('role', 'Siswa')

    with st.sidebar:
        st.title("Baitul Hikmah")
        st.write(f"👤 {u['nama']}")
        if role == "Admin":
            menu = st.radio("Navigasi", ["Dashboard", "Cari Buku", "📸 Scan Pinjam (Kamera)", "Laporan"])
        else:
            menu = st.radio("Navigasi", ["Kartu Digital", "Cari Buku", "Pinjaman Saya"])
        if st.button("🚪 Keluar"):
            st.session_state.logged_in = False
            st.rerun()

    # --- FITUR SCAN KAMERA (REVISI UTAMA) ---
    if menu == "📸 Scan Pinjam (Kamera)":
        st.title("📸 Scan Barcode/QR Buku")
        st.write("Arahkan Barcode Buku atau QR Siswa ke Kamera")
        
        # Komponen Scanner Kamera
        barcode_data = st_barcode_scanner()
        
        if barcode_data:
            st.success(f"Terscan: {barcode_data}")
            
            with st.form("proses_scan"):
                st.write("### Konfirmasi Data")
                # Jika yang terscan adalah ID Buku (misal format buku 'BK-xxx')
                # Kita asumsikan input manual/scan otomatis masuk ke field ini
                c1, c2 = st.columns(2)
                res_id = c1.text_input("ID Buku Terscan", value=barcode_data)
                res_nis = c2.text_input("NIS Siswa (Input/Scan)")
                durasi = st.selectbox("Durasi (Hari)", [3, 7, 14])
                
                if st.form_submit_button("Proses Pinjam"):
                    df_p = get_data("pinjam")
                    tgl_k = date.today() + timedelta(days=durasi)
                    new_p = pd.DataFrame([{"username":res_nis, "id_buku":res_id, "tgl_pinjam":str(date.today()), "tgl_kembali":str(tgl_k), "status":"Dipinjam"}])
                    conn.update(worksheet="pinjam", data=pd.concat([df_p, new_row], ignore_index=True))
                    st.balloons()
                    st.success("Data Berhasil Masuk ke Database!")

    # --- FITUR CARI BUKU ---
    elif menu == "Cari Buku":
        st.title("🔍 Cari Koleksi")
        df_b = get_data("buku")
        search = st.text_input("Masukkan Judul atau ID...")
        if not df_b.empty:
            filtered = df_b[df_b['judul'].str.contains(search, case=False)] if search else df_b
            st.table(filtered[['id_buku', 'judul', 'status']])

    # --- FITUR KARTU DIGITAL (QR UNTUK DISCAN ADMIN) ---
    elif menu == "Kartu Digital":
        st.title("🪪 Kartu Anggota")
        st.markdown(f"""
        <div class="digital-card">
            <h2>BAITUL HIKMAH</h2>
            <hr>
            <h1>{u['nama']}</h1>
            <p>NIS: {u['username']}</p>
            <div style="background:white; display:inline-block; padding:10px; border-radius:10px;">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={u['username']}">
            </div>
            <p><small>Tunjukkan QR ini ke Admin untuk Pinjam Buku</small></p>
        </div>
        """, unsafe_allow_html=True)

    # --- FITUR PINJAMAN SAYA & DENDA ---
    elif menu == "Pinjaman Saya":
        st.title("📚 Buku Saya")
        df_p = get_data("pinjam")
        my_p = df_p[df_p['username'].astype(str) == str(u['username'])]
        if not my_p.empty:
            for i, r in my_p.iterrows():
                hari_telat = hitung_selisih_hari(r['tgl_kembali'])
                denda = hari_telat * DENDA_PER_HARI
                st.warning(f"📖 {r['id_buku']} | Kembali: {r['tgl_kembali']} | Denda: Rp{denda}")
        else:
            st.info("Anda tidak sedang meminjam buku.")
