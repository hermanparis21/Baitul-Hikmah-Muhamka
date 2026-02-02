import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
# Baris di bawah ini disesuaikan agar tidak memicu ModuleNotFoundError
from streamlit_gsheets import GSheetsConnection 

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Perpus Baitul Hikmah", layout="wide", page_icon="🕌")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- KONFIGURASI TEMA & CSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #f0fdf4; 
        background-image: url("https://www.transparenttextures.com/patterns/islamic-art.png");
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(12px);
        border-radius: 15px;
        border: 1px solid rgba(16, 185, 129, 0.2);
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .digital-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #10b981 100%);
        color: white; padding: 25px; border-radius: 20px;
        text-align: center; border: 4px double rgba(255,255,255,0.3);
    }
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #10b981 100%);
        color: white; border: none; border-radius: 8px;
        width: 100%; transition: 0.3s;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATA MASTER ---
LIST_KELAS = [f"{t} {h}" for t in ['X', 'XI', 'XII'] for h in ['A','B','C','D','E','F','G']]
JENIS_BUKU = ["Buku Paket", "Referensi", "Fiksi/Novel", "Agama", "Majalah", "Lainnya"]
DENDA_PER_HARI = 500 

# --- FUNGSI HELPER ---
def get_data(worksheet_name):
    return conn.read(worksheet=worksheet_name, ttl=0)

def hitung_denda(tgl_seharusnya_kembali):
    tgl_skrg = date.today()
    if isinstance(tgl_seharusnya_kembali, str):
        try:
            tgl_seharusnya_kembali = datetime.strptime(tgl_seharusnya_kembali, '%Y-%m-%d').date()
        except:
            return 0
    if tgl_skrg > tgl_seharusnya_kembali:
        return (tgl_skrg - tgl_seharusnya_kembali).days * DENDA_PER_HARI
    return 0

def kirim_wa(nama, buku, tgl, no_wa):
    no_wa_bersih = str(no_wa).replace("+", "").replace(" ", "").replace("-", "")
    if not no_wa_bersih.startswith('62'):
        if no_wa_bersih.startswith('0'):
            no_wa_bersih = '62' + no_wa_bersih[1:]
    pesan = f"Assalamu'alaikum {nama}, ini dari Perpus Baitul Hikmah SMAM4. Mengingatkan pengembalian buku '{buku}' jatuh pada {tgl}. Syukron."
    url = f"https://wa.me/{no_wa_bersih}?text={pesan.replace(' ', '%20')}"
    return url

# --- LOGIKA SESSION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- HALAMAN LOGIN & REGISTRASI ---
if not st.session_state.logged_in:
    st.title("🕌 Perpustakaan Baitul Hikmah")
    st.caption("SMA Muhammadiyah 4 Banjarnegara")
    tab_login, tab_reg = st.tabs(["🔐 Login", "📝 Registrasi Siswa"])
    
    with tab_login:
        with st.form("form_login"):
            user_input = st.text_input("Username / NIS")
            pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                df_users = get_data("users")
                if not df_users.empty:
                    u_in = str(user_input).strip()
                    p_in = str(pass_input).strip()
                    user_data = df_users[
                        (df_users['username'].astype(str).str.strip() == u_in) & 
                        (df_users['password'].astype(str).str.strip() == p_in)
                    ]
                    if not user_data.empty:
                        st.session_state.logged_in = True
                        st.session_state.user_info = user_data.iloc[0].fillna("").to_dict()
                        st.rerun()
                    else:
                        st.error("Username atau Password salah!")

    with tab_reg:
        with st.form("form_reg"):
            r_nama = st.text_input("Nama Lengkap")
            r_nis = st.text_input("NIS")
            r_wa = st.text_input("Nomor WA (Contoh: 6281xxx)")
            r_kelas = st.selectbox("Pilih Kelas", LIST_KELAS)
            r_pass = st.text_input("Buat Password", type="password")
            if st.form_submit_button("Daftar Sekarang"):
                df_u = get_data("users")
                new_user = pd.DataFrame([{
                    "username": str(r_nis), "password": str(r_pass), 
                    "role": "Siswa", "nama": r_nama, 
                    "kelas": r_kelas, "no_wa": str(r_wa)
                }])
                conn.update(worksheet="users", data=pd.concat([df_u, new_user], ignore_index=True))
                st.success("Registrasi Berhasil!")

# --- HALAMAN UTAMA ---
else:
    u_info = st.session_state.user_info
    with st.sidebar:
        st.markdown(f"### 🕌 Baitul Hikmah\n**{u_info['nama']}**")
        if st.button("🚪 Keluar"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        if u_info['role'] == "Admin":
            nav = st.radio("Menu", ["Dashboard", "Manajemen Buku", "Transaksi Pinjam", "Laporan & WA Reminder"])
        elif u_info['role'] == "Wali Kelas":
            nav = st.radio("Menu", ["Monitor Kelas", "Katalog Buku"])
        else:
            nav = st.radio("Menu", ["Kartu Pinjam Digital", "Katalog Buku", "Pinjaman Saya"])

    if nav == "Dashboard":
        st.title("📊 Statistik Baitul Hikmah")
        df_p = get_data("pinjam")
        df_b = get_data("buku")
        col1, col2 = st.columns(2)
        with col1:
            if not df_p.empty and not df_b.empty:
                populer = df_p['id_buku'].value_counts().reset_index()
                populer.columns = ['id_buku', 'jumlah']
                populer = pd.merge(populer, df_b[['id_buku', 'judul']], on='id_buku').head(5)
                fig = px.bar(populer, x='jumlah', y='judul', orientation='h', title="Buku Populer", color_discrete_sequence=['#10b981'])
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.metric("Total Koleksi", len(df_b))

    elif nav == "Kartu Pinjam Digital":
        st.title("🪪 Kartu Anggota")
        st.markdown(f"""<div class="digital-card"><h2>BAITUL HIKMAH</h2><hr><h3>{u_info['nama']}</h3><p>NIS: {u_info['username']} | Kelas: {u_info['kelas']}</p></div>""", unsafe_allow_html=True)

    elif nav == "Laporan & WA Reminder":
        st.title("📱 Pengingat WhatsApp")
        df_p = get_data("pinjam")
        df_u = get_data("users")
        if not df_p.empty:
            merged = pd.merge(df_p, df_u[['username', 'nama', 'no_wa']], on="username", how="left")
            for i, row in merged[merged['status'] == "Dipinjam"].iterrows():
                with st.container():
                    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                    st.write(f"👤 {row['nama']} | 📖 {row['id_buku']}")
                    st.markdown(f'<a href="{kirim_wa(row["nama"], row["id_buku"], row["tgl_kembali"], row["no_wa"])}" target="_blank"><button style="background:#25D366; color:white; border:none; padding:8px; border-radius:5px;">Kirim WA</button></a>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "Katalog Buku":
        st.title("📚 Katalog")
        st.dataframe(get_data("buku"), use_container_width=True)

    elif nav == "Manajemen Buku":
        st.title("⚙️ Manajemen")
        df_b = get_data("buku")
        with st.form("add_b"):
            b_id = st.text_input("ID")
            b_jd = st.text_input("Judul")
            if st.form_submit_button("Simpan"):
                new_b = pd.DataFrame([{"id_buku":b_id, "judul":b_jd, "status":"Tersedia"}])
                conn.update(worksheet="buku", data=pd.concat([df_b, new_b], ignore_index=True))
                st.rerun()
        st.dataframe(df_b)

    elif nav == "Transaksi Pinjam":
        st.title("📝 Peminjaman")
        df_p = get_data("pinjam")
        with st.form("p_f"):
            p_n = st.text_input("NIS")
            p_b = st.text_input("ID Buku")
            if st.form_submit_button("Proses"):
                new_p = pd.DataFrame([{"username":p_n, "id_buku":p_b, "tgl_pinjam":str(date.today()), "tgl_kembali":str(date.today()+timedelta(days=7)), "status":"Dipinjam"}])
                conn.update(worksheet="pinjam", data=pd.concat([df_p, new_p], ignore_index=True))
                st.success("Berhasil")
