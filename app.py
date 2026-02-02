import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURASI ---
st.set_page_config(page_title="E-Perpus Baitul Hikmah", layout="wide", page_icon="🕌")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- STYLE ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .digital-card {
        background: linear-gradient(135deg, #064e3b 0%, #10b981 100%);
        color: white; padding: 30px; border-radius: 20px; text-align: center;
        border: 2px solid #fcd34d;
    }
    .glass-card {
        background: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); color: black; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI ---
def get_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0).fillna("")
    except:
        return pd.DataFrame()

def hitung_denda(tgl_kembali):
    if not tgl_kembali: return 0
    try:
        if isinstance(tgl_kembali, str):
            tgl_kembali = datetime.strptime(tgl_kembali, '%Y-%m-%d').date()
        hari_ini = date.today()
        if hari_ini > tgl_kembali:
            return (hari_ini - tgl_kembali).days * 500
    except: pass
    return 0

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🕌 E-Perpus Baitul Hikmah")
    t_login, t_reg = st.tabs(["🔐 Login", "📝 Daftar"])
    with t_login:
        with st.form("login"):
            u = st.text_input("NIS").strip()
            p = st.text_input("Password", type="password").strip()
            if st.form_submit_button("Masuk"):
                df_u = get_data("users")
                match = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_info = match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("NIS/Password Salah")
    with t_reg:
        with st.form("reg"):
            n_nama = st.text_input("Nama Lengkap")
            n_nis = st.text_input("NIS")
            n_pass = st.text_input("Password", type="password")
            n_kls = st.selectbox("Kelas", [f"{k} {h}" for k in ['X','XI','XII'] for h in ['A','B','C']])
            if st.form_submit_button("Daftar"):
                df_u = get_data("users")
                new_u = pd.DataFrame([{"username":n_nis,"password":n_pass,"role":"Siswa","nama":n_nama,"kelas":n_kls}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True))
                st.success("Sukses! Silakan Login.")

else:
    u = st.session_state.user_info
    role = u.get('role', 'Siswa')

    with st.sidebar:
        st.title("🕌 Baitul Hikmah")
        st.write(f"Halo, **{u['nama']}**")
        menu = ["Dashboard", "Cari Buku", "Kartu Digital", "Pinjaman Saya"]
        if role == "Admin":
            menu = ["Dashboard", "Kelola Buku", "Scan Pinjam Buku", "Laporan"]
        choice = st.radio("Menu", menu)
        if st.button("🚪 Keluar"):
            st.session_state.logged_in = False
            st.rerun()

    # --- FITUR SCAN (PAKAI KAMERA BAWAAN) ---
    if choice == "Scan Pinjam Buku":
        st.title("📸 Scan Barcode Buku")
        st.write("Gunakan kamera untuk mengambil foto barcode pada buku")
        
        foto = st.camera_input("Ambil Foto Barcode")
        if foto:
            st.image(foto, caption="Barcode terscan", width=300)
            st.success("Foto berhasil diambil. Masukkan ID Buku di bawah untuk konfirmasi.")
            
        with st.form("f_pinjam"):
            col1, col2 = st.columns(2)
            p_idb = col1.text_input("ID Buku (Sesuai Barcode)")
            p_nis = col1.text_input("NIS Siswa")
            p_dur = col2.selectbox("Durasi", [7, 14, 21])
            if st.form_submit_button("Proses Pinjam"):
                df_p = get_data("pinjam")
                tgl_k = date.today() + timedelta(days=p_dur)
                new_p = pd.DataFrame([{"username":p_nis, "id_buku":p_idb, "tgl_pinjam":str(date.today()), "tgl_kembali":str(tgl_k), "status":"Dipinjam"}])
                conn.update(worksheet="pinjam", data=pd.concat([df_p, new_p], ignore_index=True))
                st.success("Buku Berhasil Dipinjam!")

    # --- CARI BUKU ---
    elif "Cari Buku" in choice or "Kelola Buku" in choice:
        st.title("📚 Katalog Buku")
        df_b = get_data("buku")
        cari = st.text_input("Cari Judul...")
        if not df_b.empty:
            res = df_b[df_b['judul'].str.contains(cari, case=False)] if cari else df_b
            st.dataframe(res, use_container_width=True)

    # --- KARTU DIGITAL ---
    elif choice == "Kartu Digital":
        st.title("🪪 Kartu Anggota")
        st.markdown(f"""
        <div class="digital-card">
            <h2>BAITUL HIKMAH</h2>
            <h1>{u['nama']}</h1>
            <p>NIS: {u['username']} | Kelas: {u.get('kelas','-')}</p>
            <div style="background:white; display:inline-block; padding:10px; border-radius:10px;">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={u['username']}">
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- PINJAMAN SAYA ---
    elif choice == "Pinjaman Saya" or choice == "Laporan":
        st.title("📋 Data Pinjaman")
        df_p = get_data("pinjam")
        if role == "Siswa":
            df_p = df_p[df_p['username'].astype(str) == str(u['username'])]
        
        for _, r in df_p.iterrows():
            denda = hitung_denda(r['tgl_kembali'])
            with st.container():
                st.markdown(f"""
                <div class="glass-card">
                    <b>📖 {r['id_buku']}</b> | Kembali: {r['tgl_kembali']} <br>
                    <span style="color:red;">💰 Potensi Denda: Rp {denda:,}</span>
                </div>
                """, unsafe_allow_html=True)

    # --- DASHBOARD ---
    elif choice == "Dashboard":
        st.title("📊 Statistik")
        st.info("Selamat datang di sistem Perpustakaan Baitul Hikmah.")
        df_b = get_data("buku")
        df_p = get_data("pinjam")
        c1, c2 = st.columns(2)
        c1.metric("Koleksi Buku", len(df_b))
        c2.metric("Total Transaksi", len(df_p))
