import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Perpus Baitul Hikmah", layout="wide", page_icon="🕌")

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. CSS UNTUK TAMPILAN ---
st.markdown("""
    <style>
    .stApp { background-color: #f0fdf4; }
    .digital-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #10b981 100%);
        color: white; padding: 25px; border-radius: 20px; text-align: center;
        border: 4px double rgba(255,255,255,0.3);
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.8);
        padding: 20px; border-radius: 15px; margin-bottom: 15px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #10b981 100%);
        color: white; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA MASTER & HELPER ---
LIST_KELAS = [f"{t} {h}" for t in ['X', 'XI', 'XII'] for h in ['A','B','C','D','E','F','G']]
DENDA_PER_HARI = 500

def get_data(worksheet_name):
    return conn.read(worksheet=worksheet_name, ttl=0)

def hitung_denda(tgl_kembali):
    if isinstance(tgl_kembali, str):
        try: tgl_kembali = datetime.strptime(tgl_kembali, '%Y-%m-%d').date()
        except: return 0
    hari_ini = date.today()
    if hari_ini > tgl_kembali:
        return (hari_ini - tgl_kembali).days * DENDA_PER_HARI
    return 0

def kirim_wa(nama, buku, tgl, no_wa):
    no_wa_fix = str(no_wa).replace("08", "628", 1) if str(no_wa).startswith("08") else str(no_wa)
    pesan = f"Assalamu'alaikum {nama}, buku '{buku}' jatuh tempo {tgl}. Segera kembalikan ya. Syukron."
    return f"https://wa.me/{no_wa_fix}?text={pesan.replace(' ', '%20')}"

# --- 5. LOGIKA LOGIN & SESSION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🕌 Perpustakaan Baitul Hikmah")
    st.caption("SMA Muhammadiyah 4 Banjarnegara")
    
    tab_login, tab_reg = st.tabs(["🔐 Login", "📝 Registrasi Siswa"])
    
    with tab_login:
        with st.form("form_login"):
            u_in = st.text_input("Username / NIS").strip()
            p_in = st.text_input("Password", type="password").strip()
            if st.form_submit_button("Masuk"):
                df_u = get_data("users")
                if not df_u.empty:
                    # Filter data dengan mencocokkan username & password
                    match = df_u[(df_u['username'].astype(str).str.strip() == u_in) & 
                                 (df_u['password'].astype(str).str.strip() == p_in)]
                    if not match.empty:
                        st.session_state.logged_in = True
                        st.session_state.user_info = match.iloc[0].to_dict()
                        st.rerun()
                    else:
                        st.error("Login Gagal! Akun tidak ditemukan atau password salah.")

    with tab_reg:
        with st.form("form_reg"):
            r_nama = st.text_input("Nama Lengkap")
            r_nis = st.text_input("NIS (Akan jadi Username)")
            r_wa = st.text_input("Nomor WA (Awali 62)")
            r_kelas = st.selectbox("Pilih Kelas", LIST_KELAS)
            r_pass = st.text_input("Buat Password", type="password")
            
            if st.form_submit_button("Daftar Sekarang"):
                df_u = get_data("users")
                # KUNCI URUTAN KOLOM: username, password, role, nama, kelas, no_wa
                new_row = pd.DataFrame([{
                    "username": str(r_nis),
                    "password": str(r_pass),
                    "role": "Siswa",
                    "nama": r_nama,
                    "kelas": r_kelas,
                    "no_wa": str(r_wa)
                }])
                # Pastikan urutan kolom sesuai Google Sheet (A-F)
                new_row = new_row[["username", "password", "role", "nama", "kelas", "no_wa"]]
                updated_df = pd.concat([df_u, new_row], ignore_index=True)
                conn.update(worksheet="users", data=updated_df)
                st.success("Registrasi Berhasil! Silakan Login.")

# --- 6. HALAMAN DALAM (SETELAH LOGIN) ---
else:
    u = st.session_state.user_info
    
    with st.sidebar:
        st.markdown(f"### 🕌 Perpus Hikmah\n**{u['nama']}**")
        if st.button("🚪 Keluar"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        
        # Penentuan Menu berdasarkan Role
        role = u.get('role', 'Siswa')
        if role == "Admin":
            nav = st.radio("Menu", ["Dashboard", "Manajemen Buku", "Transaksi Pinjam", "Laporan & WA"])
        elif role == "Wali Kelas":
            nav = st.radio("Menu", ["Monitor Kelas", "Katalog Buku"])
        else:
            nav = st.radio("Menu", ["Kartu Digital", "Katalog Buku", "Pinjaman Saya"])

    # --- ISI MENU ---
    if nav == "Dashboard":
        st.title("📊 Statistik Perpustakaan")
        df_b = get_data("buku")
        df_p = get_data("pinjam")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Buku", len(df_b) if not df_b.empty else 0)
        col2.metric("Peminjaman Aktif", len(df_p[df_p['status']=='Dipinjam']) if not df_p.empty else 0)
        
        if not df_p.empty and not df_b.empty:
            populer = df_p['id_buku'].value_counts().reset_index().head(5)
            populer.columns = ['id_buku', 'jumlah']
            populer = pd.merge(populer, df_b[['id_buku', 'judul']], on='id_buku')
            fig = px.bar(populer, x='jumlah', y='judul', orientation='h', title="Buku Favorit")
            st.plotly_chart(fig, use_container_width=True)

    elif nav == "Kartu Digital":
        st.title("🪪 Kartu Anggota Digital")
        st.markdown(f"""
        <div class="digital-card">
            <h2>BAITUL HIKMAH</h2>
            <hr>
            <h1>{u['nama']}</h1>
            <p>NIS: {u['username']} | Kelas: {u['kelas']}</p>
        </div>
        """, unsafe_allow_html=True)

    elif nav == "Katalog Buku":
        st.title("📚 Katalog Buku")
        st.dataframe(get_data("buku"), use_container_width=True)

    elif nav == "Manajemen Buku":
        st.title("⚙️ Atur Koleksi Buku")
        df_b = get_data("buku")
        with st.expander("➕ Tambah Buku"):
            with st.form("add_book"):
                b_id = st.text_input("ID Buku")
                b_jd = st.text_input("Judul")
                if st.form_submit_button("Simpan"):
                    nb = pd.DataFrame([{"id_buku":b_id, "judul":b_jd, "status":"Tersedia"}])
                    conn.update(worksheet="buku", data=pd.concat([df_b, nb], ignore_index=True))
                    st.success("Berhasil!"); st.rerun()
        st.dataframe(df_b, use_container_width=True)

    elif nav == "Transaksi Pinjam":
        st.title("📝 Input Peminjaman")
        df_p = get_data("pinjam")
        with st.form("t_pinjam"):
            p_nis = st.text_input("NIS Siswa")
            p_idb = st.text_input("ID Buku")
            if st.form_submit_button("Proses Pinjam"):
                tgl_k = date.today() + timedelta(days=7)
                np = pd.DataFrame([{"username":p_nis, "id_buku":p_idb, "tgl_pinjam":str(date.today()), "tgl_kembali":str(tgl_k), "status":"Dipinjam"}])
                conn.update(worksheet="pinjam", data=pd.concat([df_p, np], ignore_index=True))
                st.success(f"Berhasil! Kembali: {tgl_k}")

    elif nav == "Laporan & WA":
        st.title("📱 WA Reminder")
        df_p = get_data("pinjam")
        df_u = get_data("users")
        if not df_p.empty and not df_u.empty:
            m = pd.merge(df_p, df_u[['username', 'nama', 'no_wa']], on="username", how="left")
            for i, r in m[m['status'] == "Dipinjam"].iterrows():
                denda = hitung_denda(r['tgl_kembali'])
                with st.container():
                    st.markdown(f'<div class="glass-card">', unsafe_allow_html=True)
                    st.write(f"👤 **{r['nama']}** | 📖 {r['id_buku']} | 💰 Denda: Rp{denda}")
                    link = kirim_wa(r['nama'], r['id_buku'], r['tgl_kembali'], r['no_wa'])
                    st.markdown(f'<a href="{link}" target="_blank"><button style="background:#25D366; color:white; border:none; padding:8px; border-radius:5px;">Kirim Pesan WA</button></a>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
