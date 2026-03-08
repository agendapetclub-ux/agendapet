import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import base64
import uuid
import secrets
from datetime import datetime, date, time, timedelta
from PIL import Image
import io
import re

# Configurações
DB_PATH = "petclub.db"
APP_NAME = "PET CLUB"
YEAR = "2026"
MIN_HORAS_ANTECEDENCIA_CANCEL = 6
MAX_IMAGE_DIMENSION = 1024
JPEG_QUALITY = 85
MAX_UPLOAD_SIZE_MB = 5
HORARIO_ABERTURA = time(8, 0)
HORARIO_FECHAMENTO = time(18, 0)
INTERVALO_MINIMO_MINUTOS = 30
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def generate_salt():
    return base64.b64encode(secrets.token_bytes(16)).decode()

def hash_password(plain, salt):
    return base64.b64encode(hashlib.pbkdf2_hmac("sha256", plain.encode(), base64.b64decode(salt), 100000)).decode()

def verify_password(plain, stored_hash, stored_salt):
    return hash_password(plain, stored_salt) == stored_hash

def normalize_username(username):
    return (username or "").strip().lower()

def resize_and_optimize_image(uploaded_file):
    if uploaded_file is None:
        return None
    if uploaded_file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        st.error(f"Imagem muito grande (máx {MAX_UPLOAD_SIZE_MB} MB)")
        return None
    try:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return output.getvalue()
    except Exception as e:
        st.warning(f"Erro na imagem: {str(e)}")
        return None

def show_paw_prints():
    st.markdown("""
        <style>
        @keyframes pawStep {
            0% { opacity: 0; transform: translate(0vw, 100vh) scale(0.7) rotate(0deg); }
            40% { opacity: 1; transform: translate(5vw, 70vh) scale(1.0) rotate(5deg); }
            100% { opacity: 0.9; transform: translate(35vw, -20vh) scale(1.1) rotate(10deg); }
        }
        .paw-step {
            position: fixed;
            font-size: 100px;
            color: #006400;
            pointer-events: none;
            z-index: 9999;
            animation: pawStep 2.2s ease-out forwards;
            animation-delay: calc(var(--step) * 0.4s);
            left: var(--start-x);
            top: var(--start-y);
            text-shadow: 0 0 20px rgba(0, 100, 0, 0.8);
        }
        </style>
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 9999; overflow: hidden;">
            <div class="paw-step" style="--step:0; --start-x:10%; --start-y:90%;">🐾</div>
            <div class="paw-step" style="--step:1; --start-x:18%; --start-y:75%;">🐾</div>
            <div class="paw-step" style="--step:2; --start-x:26%; --start-y:60%;">🐾</div>
            <div class="paw-step" style="--step:3; --start-x:34%; --start-y:45%;">🐾</div>
            <div class="paw-step" style="--step:4; --start-x:42%; --start-y:32%;">🐾</div>
            <div class="paw-step" style="--step:5; --start-x:52%; --start-y:20%;">🐾</div>
            <div class="paw-step" style="--step:6; --start-x:62%; --start-y:10%;">🐾</div>
            <div class="paw-step" style="--step:7; --start-x:74%; --start-y:5%;">🐾</div>
            <div class="paw-step" style="--step:8; --start-x:87%; --start-y:2%;">🐾</div>
        </div>
    """, unsafe_allow_html=True)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        role TEXT NOT NULL, nome_completo TEXT NOT NULL, telefone TEXT, email TEXT UNIQUE,
        endereco TEXT, funcao TEXT, data_cadastro TEXT DEFAULT (datetime('now','localtime')), ativo INTEGER DEFAULT 1,
        profissional_id INTEGER,
        FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, criado_por TEXT NOT NULL, nome TEXT NOT NULL,
        especie_raca TEXT NOT NULL, idade INTEGER, porte TEXT, observacoes TEXT, foto_base64 TEXT,
        data_cadastro TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (criado_por) REFERENCES usuarios(username)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS atendimentos (
        id TEXT PRIMARY KEY, servico TEXT NOT NULL, pet_id INTEGER NOT NULL,
        data_hora_pref TEXT NOT NULL, descricao TEXT, status TEXT DEFAULT 'Pendente',
        data_agendamento TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        criado_por TEXT NOT NULL, profissional_id INTEGER, data_cancelamento TEXT,
        FOREIGN KEY (criado_por) REFERENCES usuarios(username),
        FOREIGN KEY (pet_id) REFERENCES pets(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS profissionais (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome_completo TEXT NOT NULL,
        funcao TEXT NOT NULL, telefone TEXT, email TEXT, foto_base64 TEXT,
        cor_calendario TEXT, ativo INTEGER DEFAULT 1
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS bloqueios_horarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profissional_id INTEGER NOT NULL,
        dia_semana TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        hora_fim TEXT NOT NULL,
        motivo TEXT,
        criado_por TEXT NOT NULL,
        data_criacao TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
        FOREIGN KEY (criado_por) REFERENCES usuarios(username)
    )""")
    cur.execute("PRAGMA table_info(atendimentos)")
    columns = [col[1] for col in cur.fetchall()]
    if 'data_cancelamento' not in columns:
        cur.execute("ALTER TABLE atendimentos ADD COLUMN data_cancelamento TEXT")
        conn.commit()
    cur.execute("PRAGMA table_info(usuarios)")
    columns = [col[1] for col in cur.fetchall()]
    if 'endereco' not in columns:
        cur.execute("ALTER TABLE usuarios ADD COLUMN endereco TEXT")
        conn.commit()
    if 'profissional_id' not in columns:
        cur.execute("ALTER TABLE usuarios ADD COLUMN profissional_id INTEGER")
        conn.commit()
    if 'last_login' not in columns:
        cur.execute("ALTER TABLE usuarios ADD COLUMN last_login TEXT")
        conn.commit()
    if not cur.execute("SELECT 1 FROM profissionais LIMIT 1").fetchone():
        cur.executemany("INSERT OR IGNORE INTO profissionais (nome_completo, funcao, telefone, email, ativo) VALUES (?, ?, ?, ?, ?)",
                        [("Ana Silva", "Tosadora", "(19) 99999-9999", "ana@petclub.com", 1),
                         ("Carlos Souza", "Tosador", "(19) 88888-8888", "carlos@petclub.com", 1),
                         ("Dr. Mariana Lopes", "Veterinária", "(19) 77777-7777", "mariana@petclub.com", 1)])
    if not cur.execute("SELECT 1 FROM usuarios WHERE username = 'admin'").fetchone():
        salt = generate_salt()
        hash_pw = hash_password("admin123", salt)
        cur.execute("INSERT INTO usuarios (username, password_hash, salt, role, nome_completo, email) VALUES (?, ?, ?, 'admin', 'Administrador Principal', 'admin@petclub.local')",
                    ("admin", hash_pw, salt))
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title=f"{APP_NAME} - Agendamentos", layout="wide", page_icon="🐾")

st.markdown("""
    <style>
    .stButton > button {width: 100%; border-radius: 8px; font-weight: bold; margin: 10px 0; padding: 12px;}
    .success-box {background-color: #e6f4ea; color: #1e4d2b; padding: 20px; border-radius: 10px; border: 1px solid #b3e0c4; margin: 20px 0;}
    .warning-box {background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; border: 1px solid #ffeeba; margin: 15px 0;}
    </style>
""", unsafe_allow_html=True)

# Ocultar menu superior e footer (recomendado para app público)
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

for key in ["user", "nome", "email", "role", "menu", "agendamento_sucesso", "profissional_id"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.user and st.session_state.menu is None:
    st.session_state.menu = "Serviços Agendados" if st.session_state.role == "admin" else ("Meus Pets" if st.session_state.role == "cliente" else "Meus Atendimentos")

# SIDEBAR
st.sidebar.title(f"🐾 {APP_NAME}")
if st.session_state.user:
    st.sidebar.write(f"Olá, **{st.session_state.nome or st.session_state.user}** ({st.session_state.role.capitalize()})")
    if st.session_state.role == "admin":
        menu_options = ["Serviços Agendados", "Relatórios", "Clientes Cadastrados", "Pets Cadastrados", "Profissionais", "Bloqueios de Agenda", "Sair"]
    elif st.session_state.role == "profissional":
        menu_options = ["Meus Atendimentos", "Sair"]
    else:
        menu_options = ["Agendar Serviço", "Meus Pets", "Meus Agendamentos", "Editar Cadastro", "Sair"]
    selected = st.sidebar.radio("Menu", menu_options,
                                index=menu_options.index(st.session_state.menu) if st.session_state.menu in menu_options else 0)
    st.session_state.menu = selected
    if st.session_state.menu == "Sair":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.sidebar.caption(f"{APP_NAME} • Sistema de Agendamento • {YEAR}")

# CONSULTA PÚBLICA
st.markdown("### Consultar Agendamento pelo Protocolo")
col1, col2 = st.columns([3, 1])
with col1:
    protocolo = st.text_input("Protocolo", placeholder="Ex: B5363589E", key="consulta_pub")
with col2:
    if st.button("Consultar", type="primary"):
        if protocolo.strip():
            conn = get_conn()
            row = conn.execute("""
                SELECT
                    a.id, a.servico, a.data_hora_pref, a.status, a.descricao,
                    p.nome as pet_nome, p.especie_raca, u.nome_completo as dono,
                    a.data_cancelamento, pr.nome_completo as profissional
                FROM atendimentos a
                JOIN pets p ON a.pet_id = p.id
                JOIN usuarios u ON a.criado_por = u.username
                LEFT JOIN profissionais pr ON a.profissional_id = pr.id
                WHERE a.id = ?
            """, (protocolo.upper(),)).fetchone()
            conn.close()
            if row:
                status_text = row[3]
                if row[3] == "Cancelado" and row[8]:
                    try:
                        cancel_dt = datetime.strptime(row[8], "%Y-%m-%d %H:%M:%S")
                        status_text += f" em {cancel_dt.strftime('%d/%m/%Y às %H:%M')}"
                    except:
                        status_text += f" em {row[8]}"
                profissional_display = row[9] if row[9] else "Ainda não atribuído"
                st.markdown(f"""
                <div class="success-box">
                    <strong>Protocolo:</strong> {row[0]}<br>
                    <strong>Status:</strong> {status_text}<br>
                    <strong>Pet:</strong> {row[5]} ({row[6]})<br>
                    <strong>Serviço:</strong> {row[1]}<br>
                    <strong>Data/Hora:</strong> {row[2]}<br>
                    <strong>Profissional Responsável:</strong> {profissional_display}<br>
                    <strong>Detalhes:</strong> {row[4] or '—'}<br>
                    <strong>Responsável (dono):</strong> {row[7]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Protocolo não encontrado.")
        else:
            st.warning("Digite o protocolo.")

st.markdown("---")

# LOGIN / CADASTRO
if st.session_state.user is None:
    st.header(f"Bem-vindo ao {APP_NAME}")
    tab_login, tab_cad = st.tabs(["Entrar", "Criar conta"])
    with tab_login:
        usr = st.text_input("Usuário ou E-mail", key="login_usr")
        pwd = st.text_input("Senha", type="password", key="login_pwd")
        if st.button("Entrar", type="primary"):
            conn = get_conn()
            row = conn.execute("""
                SELECT username, password_hash, salt, role, nome_completo, email, ativo, profissional_id
                FROM usuarios WHERE (username = ? OR email = ?) AND ativo = 1
            """, (usr.strip(), usr.strip())).fetchone()
            conn.close()
            if row and verify_password(pwd, row[1], row[2]):
                st.session_state.user = normalize_username(row[0])
                st.session_state.nome = row[4]
                st.session_state.email = row[5]
                st.session_state.role = row[3]
                st.session_state.profissional_id = row[7]
                conn = get_conn()
                conn.execute("UPDATE usuarios SET last_login = datetime('now','localtime') WHERE username = ?", (st.session_state.user,))
                conn.commit()
                conn.close()
                st.success(f"Bem-vindo(a), {row[4]}!")
                st.rerun()
            else:
                st.error("Credenciais inválidas ou conta inativa.")
    with tab_cad:
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome completo *")
            email_cad = st.text_input("E-mail *")
        with col2:
            tel = st.text_input("Telefone / WhatsApp")
            usuario = st.text_input("Usuário *")
        st.subheader("Endereço")
        col_cep, col_uf = st.columns([2, 1])
        with col_cep:
            cep = st.text_input("CEP", placeholder="00000-000", max_chars=9)
        with col_uf:
            uf = st.selectbox("UF", ["", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
                                    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
                                    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"])
        col_rua, col_num = st.columns([3, 1])
        with col_rua:
            logradouro = st.text_input("Rua / Avenida / Logradouro")
        with col_num:
            numero = st.text_input("Número", max_chars=10)
        complemento = st.text_input("Complemento (bloco, apto, etc.)", placeholder="Apto 101, Bloco B, etc.")
        bairro = st.text_input("Bairro")
        cidade = st.text_input("Cidade")
        referencia = st.text_area("Ponto de referência (opcional)", height=80, placeholder="Ex: Próximo ao mercado X, em frente à praça Y")
        senha1 = st.text_input("Senha *", type="password")
        senha2 = st.text_input("Confirme a senha *", type="password")
        if st.button("Criar conta", type="primary"):
            if not all([nome.strip(), email_cad.strip(), usuario.strip(), senha1]):
                st.error("Preencha os campos obrigatórios")
            elif senha1 != senha2:
                st.error("Senhas não coincidem")
            else:
                username_norm = normalize_username(usuario)
                salt = generate_salt()
                hash_pw = hash_password(senha1, salt)
                endereco_novo = []
                if logradouro: endereco_novo.append(logradouro.strip())
                if numero: endereco_novo.append(f", {numero.strip()}")
                if complemento: endereco_novo.append(f" - {complemento.strip()}")
                if bairro: endereco_novo.append(f" - {bairro.strip()}")
                if cidade or uf:
                    cid_uf = f"{cidade.strip()}" if cidade else ""
                    if uf: cid_uf += f"/{uf}" if cid_uf else uf
                    endereco_novo.append(f", {cid_uf}")
                if cep: endereco_novo.append(f" - CEP {cep.strip()}")
                if referencia: endereco_novo.append(f" ({referencia.strip()})")
                endereco_final = "".join(endereco_novo).strip(", -")
                try:
                    conn = get_conn()
                    conn.execute("""
                        INSERT INTO usuarios (username, password_hash, salt, role, nome_completo, email, telefone, endereco)
                        VALUES (?, ?, ?, 'cliente', ?, ?, ?, ?)
                    """, (username_norm, hash_pw, salt, nome.strip(), email_cad.strip(), tel.strip() or None, endereco_final or None))
                    conn.commit()
                    conn.close()
                    st.session_state.user = username_norm
                    st.session_state.nome = nome.strip()
                    st.session_state.email = email_cad.strip()
                    st.session_state.role = 'cliente'
                    st.success("Conta criada! Você já está logado.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Usuário ou e-mail já cadastrado.")
                except Exception as e:
                    st.error(str(e))

else:
    # ÁREA LOGADA
    if st.session_state.role == "profissional":
        if st.session_state.menu == "Meus Atendimentos":
            st.header(f"Meus Atendimentos Pendentes - {st.session_state.nome}")
            conn = get_conn()
            last_login = conn.execute("SELECT last_login FROM usuarios WHERE username = ?", (st.session_state.user,)).fetchone()[0]
            new_count = conn.execute("""
                SELECT COUNT(*) FROM atendimentos
                WHERE profissional_id = ?
                  AND status = 'Pendente'
                  AND data_agendamento > ?
            """, (st.session_state.profissional_id, last_login or '1900-01-01 00:00:00')).fetchone()[0]
            if new_count > 0:
                st.info(f"Você tem {new_count} novos agendamentos desde o último login!")
            df = pd.read_sql_query("""
                SELECT
                    a.id AS protocolo,
                    p.nome AS pet,
                    a.servico,
                    a.data_hora_pref AS data_hora,
                    a.status,
                    u.nome_completo AS cliente,
                    a.descricao
                FROM atendimentos a
                JOIN pets p ON a.pet_id = p.id
                JOIN usuarios u ON a.criado_por = u.username
                WHERE a.profissional_id = ?
                  AND a.status = 'Pendente'
                ORDER BY a.data_agendamento DESC
            """, conn, params=(st.session_state.profissional_id,))
            conn.close()
            if df.empty:
                st.info("Você não tem atendimentos pendentes no momento.")
            else:
                st.success(f"Encontrados {len(df)} atendimentos pendentes")
                for idx, row in df.iterrows():
                    with st.expander(f"{row['servico']} • {row['pet']} • {row['data_hora']}"):
                        st.markdown(f"**Protocolo:** {row['protocolo']}")
                        st.markdown(f"**Cliente:** {row['cliente']}")
                        st.markdown(f"**Pet:** {row['pet']}")
                        st.markdown(f"**Horário:** {row['data_hora']}")
                        st.markdown(f"**Observações:** {row['descricao'] or '—'}")
                        if st.button("Finalizar este atendimento", key=f"finalizar_prof_{row['protocolo']}"):
                            conn = get_conn()
                            try:
                                conn.execute("""
                                    UPDATE atendimentos
                                    SET status = 'Finalizado'
                                    WHERE id = ? AND profissional_id = ?
                                """, (row['protocolo'], st.session_state.profissional_id))
                                conn.commit()
                                st.success(f"Atendimento {row['protocolo']} finalizado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao finalizar: {str(e)}")
                            finally:
                                conn.close()

    if st.session_state.role == "admin":
        if st.session_state.menu == "Serviços Agendados":
            st.header(f"Serviços Agendados - {APP_NAME}")
            conn = get_conn()
            df = pd.read_sql_query("""
                SELECT
                    a.id AS protocolo,
                    a.servico,
                    p.nome AS pet,
                    a.data_hora_pref AS data_hora,
                    a.status,
                    a.data_cancelamento,
                    u.nome_completo AS cliente,
                    pr.nome_completo AS profissional,
                    a.descricao,
                    a.data_agendamento
                FROM atendimentos a
                JOIN pets p ON a.pet_id = p.id
                JOIN usuarios u ON a.criado_por = u.username
                LEFT JOIN profissionais pr ON a.profissional_id = pr.id
                ORDER BY a.data_agendamento DESC
            """, conn)
            conn.close()
            if df.empty:
                st.info("Nenhum agendamento cadastrado ainda.")
            else:
                df['data_cancelamento_formatted'] = df['data_cancelamento'].apply(
                    lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") if pd.notna(x) else "—"
                )
                df['data_agendamento_formatted'] = df['data_agendamento'].apply(
                    lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") if pd.notna(x) else "—"
                )
                st.success(f"Total de {len(df)} agendamentos encontrados")
                for idx, row in df.iterrows():
                    cols = st.columns([2, 3, 2, 3, 2, 3, 3, 3, 4, 3, 2, 2])
                    cols[0].write(row['protocolo'])
                    cols[1].write(row['servico'])
                    cols[2].write(row['pet'])
                    cols[3].write(row['data_hora'])
                    cols[4].write(row['status'])
                    cols[5].write(row['data_cancelamento_formatted'])
                    cols[6].write(row['cliente'])
                    cols[7].write(row['profissional'] or "—")
                    cols[8].write(row['descricao'] or "—")
                    cols[9].write(row['data_agendamento_formatted'])
                    with cols[10]:
                        if row['status'] == "Pendente":
                            if st.button("Finalizar", key=f"finalizar_{row['protocolo']}"):
                                conn = get_conn()
                                try:
                                    conn.execute("UPDATE atendimentos SET status = 'Finalizado' WHERE id = ?", (row['protocolo'],))
                                    conn.commit()
                                    st.success(f"Agendamento {row['protocolo']} finalizado!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao finalizar: {str(e)}")
                                finally:
                                    conn.close()
                    with cols[11]:
                        if st.button("Excluir", key=f"excluir_{row['protocolo']}"):
                            if st.session_state.get(f"confirm_excluir_{row['protocolo']}", False):
                                conn = get_conn()
                                try:
                                    conn.execute("DELETE FROM atendimentos WHERE id = ?", (row['protocolo'],))
                                    conn.commit()
                                    st.session_state[f"confirm_excluir_{row['protocolo']}"] = False
                                    st.success(f"Agendamento {row['protocolo']} excluído permanentemente!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {str(e)}")
                                finally:
                                    conn.close()
                            else:
                                st.session_state[f"confirm_excluir_{row['protocolo']}"] = True
                                st.rerun()
                    if st.session_state.get(f"confirm_excluir_{row['protocolo']}", False):
                        st.warning(f"Confirma exclusão definitiva do agendamento {row['protocolo']}?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Sim, excluir", key=f"yes_excluir_{row['protocolo']}"):
                                conn = get_conn()
                                try:
                                    conn.execute("DELETE FROM atendimentos WHERE id = ?", (row['protocolo'],))
                                    conn.commit()
                                    st.session_state[f"confirm_excluir_{row['protocolo']}"] = False
                                    st.success(f"Agendamento {row['protocolo']} excluído!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {str(e)}")
                                finally:
                                    conn.close()
                        with col_no:
                            if st.button("Cancelar", key=f"no_excluir_{row['protocolo']}"):
                                st.session_state[f"confirm_excluir_{row['protocolo']}"] = False
                                st.rerun()
                st.dataframe(
                    df,
                    column_config={
                        "protocolo": "Protocolo",
                        "servico": "Serviço",
                        "pet": "Pet",
                        "data_hora": "Data/Hora Preferida",
                        "status": "Status",
                        "data_cancelamento_formatted": "Cancelado em",
                        "cliente": "Cliente",
                        "profissional": "Profissional",
                        "descricao": "Observações",
                        "data_agendamento_formatted": "Agendado em"
                    },
                    use_container_width=True,
                    hide_index=True
                )

        elif st.session_state.menu == "Relatórios":
            st.header(f"Relatórios Gerenciais - {APP_NAME}")
            st.caption("Visão geral do negócio - atualizado em tempo real")
            conn = get_conn()
            st.subheader("Visão Geral")
            col1, col2, col3, col4 = st.columns(4)
            total_agend = conn.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
            pendentes = conn.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Pendente'").fetchone()[0]
            concluidos = conn.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Finalizado'").fetchone()[0]
            cancelados = conn.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Cancelado'").fetchone()[0]
            col1.metric("Total Agendamentos", total_agend)
            col2.metric("Pendentes", pendentes)
            col3.metric("Concluídos", concluidos)
            col4.metric("Cancelados", cancelados)
            st.subheader("Últimos 30 Dias")
            df_recente = pd.read_sql_query("""
                SELECT
                    date(data_agendamento) as data,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Finalizado' THEN 1 ELSE 0 END) as concluidos,
                    SUM(CASE WHEN status = 'Cancelado' THEN 1 ELSE 0 END) as cancelados
                FROM atendimentos
                WHERE data_agendamento >= date('now', '-30 days')
                GROUP BY date(data_agendamento)
                ORDER BY data
            """, conn)
            if not df_recente.empty:
                st.line_chart(df_recente.set_index("data")[["total", "concluidos"]])
                st.dataframe(df_recente, use_container_width=True)
            else:
                st.info("Nenhum agendamento nos últimos 30 dias.")
            st.subheader("Serviços mais procurados")
            df_serv = pd.read_sql_query("""
                SELECT servico, COUNT(*) as qtd
                FROM atendimentos
                GROUP BY servico
                ORDER BY qtd DESC
                LIMIT 10
            """, conn)
            st.bar_chart(df_serv.set_index("servico")["qtd"])
            st.subheader("Clientes mais frequentes")
            df_clientes = pd.read_sql_query("""
                SELECT u.nome_completo, COUNT(a.id) as agendamentos
                FROM atendimentos a
                JOIN usuarios u ON a.criado_por = u.username
                GROUP BY u.username, u.nome_completo
                ORDER BY agendamentos DESC
                LIMIT 10
            """, conn)
            st.dataframe(df_clientes, use_container_width=True)
            st.subheader("Profissionais mais solicitados")
            df_prof = pd.read_sql_query("""
                SELECT pr.nome_completo, COUNT(a.id) as atendimentos
                FROM atendimentos a
                JOIN profissionais pr ON a.profissional_id = pr.id
                GROUP BY pr.id
                ORDER BY atendimentos DESC
                LIMIT 8
            """, conn)
            st.dataframe(df_prof, use_container_width=True)
            conn.close()
            st.markdown("---")
            st.caption(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} - {APP_NAME}")

        elif st.session_state.menu == "Clientes Cadastrados":
            st.header(f"Clientes Cadastrados - {APP_NAME}")
            conn = get_conn()
            clientes_df = pd.read_sql_query("""
                SELECT username, nome_completo, email, telefone, data_cadastro, ativo
                FROM usuarios
                WHERE role = 'cliente' AND ativo = 1
                ORDER BY nome_completo
            """, conn)
            conn.close()
            if clientes_df.empty:
                st.info("Nenhum cliente cadastrado ainda.")
            else:
                st.success(f"Encontrados {len(clientes_df)} clientes cadastrados")
                dados_tabela = []
                for _, cliente in clientes_df.iterrows():
                    conn_pet = get_conn()
                    pet_nomes = conn_pet.execute("""
                        SELECT GROUP_CONCAT(nome, ', ')
                        FROM pets
                        WHERE criado_por = ?
                    """, (cliente['username'],)).fetchone()[0] or "Nenhum pet"
                    conn_pet.close()
                    dados_tabela.append({
                        "Nome": cliente['nome_completo'],
                        "E-mail": cliente['email'],
                        "Telefone": cliente['telefone'] or "None",
                        "Pet": pet_nomes,
                        "Cadastrado em": datetime.strptime(cliente['data_cadastro'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") if cliente['data_cadastro'] else "—",
                        "Ativo": "Sim" if cliente['ativo'] else "Não"
                    })
                st.dataframe(
                    pd.DataFrame(dados_tabela),
                    column_config={
                        "Nome": "Nome",
                        "E-mail": "E-mail",
                        "Telefone": "Telefone",
                        "Pet": "Pet(s)",
                        "Cadastrado em": "Cadastrado em",
                        "Ativo": "Ativo"
                    },
                    use_container_width=True,
                    hide_index=True
                )

        elif st.session_state.menu == "Profissionais":
            st.header(f"Profissionais - {APP_NAME}")
            st.subheader("Adicionar Novo Profissional")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                novo_nome = st.text_input("Nome completo *", key="novo_prof_nome")
            with col2:
                novo_telefone = st.text_input("Telefone", key="novo_prof_tel")
            with col3:
                novo_email = st.text_input("E-mail", key="novo_prof_email")
            with col4:
                nova_funcao = st.selectbox("Função", ["Tosador(a)", "Veterinário(a)", "Auxiliar", "Balconista", "Recepcionista", "Estagiário", "Motorista / Taxi Dog"], key="novo_prof_funcao")
            col_foto, col_ativo = st.columns(2)
            with col_foto:
                nova_foto = st.file_uploader("Foto (opcional)", type=["jpg","jpeg","png"], key="novo_prof_foto")
            with col_ativo:
                ativo = st.checkbox("Ativo", value=True, key="novo_prof_ativo")
            username_prof = st.text_input("Usuário para login (opcional)", key="username_prof")
            email_prof_login = st.text_input("E-mail para login (obrigatório se criar login)", key="email_prof_login")
            senha_prof = st.text_input("Senha inicial (se criar login)", type="password", key="senha_prof")
            if st.button("Adicionar Profissional", type="primary"):
                if not novo_nome.strip():
                    st.error("Nome completo é obrigatório")
                else:
                    foto_b64 = None
                    if nova_foto is not None:
                        resized_bytes = resize_and_optimize_image(nova_foto)
                        if resized_bytes:
                            foto_b64 = base64.b64encode(resized_bytes).decode()
                    conn = get_conn()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO profissionais (nome_completo, funcao, telefone, email, foto_base64, ativo)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            novo_nome.strip(),
                            nova_funcao,
                            novo_telefone.strip() or None,
                            novo_email.strip() or None,
                            foto_b64,
                            1 if ativo else 0
                        ))
                        last_id = cur.lastrowid
                        if username_prof.strip() and senha_prof and email_prof_login.strip():
                            salt = generate_salt()
                            hash_pw = hash_password(senha_prof, salt)
                            cur.execute("""
                                INSERT INTO usuarios (username, password_hash, salt, role, nome_completo, email, profissional_id)
                                VALUES (?, ?, ?, 'profissional', ?, ?, ?)
                            """, (normalize_username(username_prof), hash_pw, salt, novo_nome.strip(), email_prof_login.strip(), last_id))
                            st.success(f"Login criado para o funcionário: usuário = {username_prof}")
                        conn.commit()
                        st.success(f"Profissional **{novo_nome.strip()}** adicionado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Usuário ou e-mail já cadastrado.")
                    except Exception as e:
                        st.error(f"Erro ao adicionar: {str(e)}")
                    finally:
                        conn.close()
            st.subheader("Profissionais Cadastrados")
            conn = get_conn()
            df = pd.read_sql_query("""
                SELECT id, nome_completo, funcao, telefone, email, foto_base64, ativo
                FROM profissionais
                ORDER BY nome_completo
            """, conn)
            if df.empty:
                st.info("Nenhum profissional cadastrado ainda.")
            else:
                st.success(f"Encontrados {len(df)} profissionais")
                for idx, row in df.iterrows():
                    cols = st.columns([1, 3, 2, 2, 1, 2, 1])
                    with cols[0]:
                        if row['foto_base64']:
                            st.image(base64.b64decode(row['foto_base64']), width=60)
                        else:
                            st.image("https://via.placeholder.com/60?text=Sem+foto")
                    with cols[1]:
                        st.write(f"**{row['nome_completo']}**")
                    with cols[2]:
                        st.write(row['funcao'])
                    with cols[3]:
                        st.write(row['telefone'] or "—")
                        st.write(row['email'] or "—")
                    with cols[4]:
                        st.write("Ativo" if row['ativo'] else "Inativo")
                    with cols[5]:
                        novo_status = 1 if row['ativo'] == 0 else 0
                        texto_botao = "Ativar" if row['ativo'] == 0 else "Desativar"
                        if st.button(texto_botao, key=f"toggle_prof_{row['id']}", type="primary" if novo_status == 1 else "secondary"):
                            conn_toggle = get_conn()
                            try:
                                conn_toggle.execute("UPDATE profissionais SET ativo = ? WHERE id = ?", (novo_status, row['id']))
                                conn_toggle.commit()
                                st.success(f"Profissional **{row['nome_completo']}** {'ativado' if novo_status == 1 else 'desativado'}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao alterar status: {str(e)}")
                            finally:
                                conn_toggle.close()
                    with cols[6]:
                        if st.button("Excluir", key=f"del_prof_{row['id']}"):
                            conn_del = get_conn()
                            try:
                                conn_del.execute("DELETE FROM profissionais WHERE id = ?", (row['id'],))
                                conn_del.execute("DELETE FROM usuarios WHERE profissional_id = ?", (row['id'],))
                                conn_del.commit()
                                st.success("Profissional e login associado excluídos!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {str(e)}")
                            finally:
                                conn_del.close()
            conn.close()

        elif st.session_state.menu == "Bloqueios de Agenda":
            st.header(f"Bloqueios de Agenda - {APP_NAME}")
            conn = get_conn()
            profs_df = pd.read_sql_query("SELECT id, nome_completo FROM profissionais WHERE ativo = 1 ORDER BY nome_completo", conn)
            conn.close()
            st.subheader("Adicionar Novo Bloqueio de Horário")
            col_prof, col_dia = st.columns(2)
            with col_prof:
                prof_selecionado = st.selectbox("Profissional", profs_df['nome_completo'].tolist() if not profs_df.empty else ["Nenhum profissional ativo"], key="bloq_prof")
            with col_dia:
                dia_semana = st.selectbox("Dia da semana", DIAS_SEMANA, key="bloq_dia")
            col_hora_ini, col_hora_fim = st.columns(2)
            with col_hora_ini:
                hora_inicio = st.time_input("Horário inicial", time(8, 0), step=1800, key="bloq_hini")
            with col_hora_fim:
                hora_fim = st.time_input("Horário final", time(12, 0), step=1800, key="bloq_hfim")
            motivo = st.text_input("Motivo do bloqueio (opcional)", key="bloq_motivo")
            if st.button("Adicionar Bloqueio", type="primary"):
                if profs_df.empty:
                    st.error("Nenhum profissional ativo encontrado.")
                elif hora_inicio >= hora_fim:
                    st.error("Horário final deve ser maior que o horário inicial.")
                else:
                    prof_id = profs_df[profs_df['nome_completo'] == prof_selecionado]['id'].iloc[0]
                    conn = get_conn()
                    try:
                        conn.execute("""
                            INSERT INTO bloqueios_horarios (profissional_id, dia_semana, hora_inicio, hora_fim, motivo, criado_por)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (prof_id, dia_semana, hora_inicio.strftime("%H:%M"), hora_fim.strftime("%H:%M"), motivo or None, st.session_state.user))
                        conn.commit()
                        st.success(f"Bloqueio adicionado para {prof_selecionado} - {dia_semana} das {hora_inicio.strftime('%H:%M')} às {hora_fim.strftime('%H:%M')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao adicionar bloqueio: {str(e)}")
                    finally:
                        conn.close()
            st.subheader("Bloqueios Cadastrados")
            conn = get_conn()
            bloqueios_df = pd.read_sql_query("""
                SELECT
                    b.id, p.nome_completo AS profissional, b.dia_semana, b.hora_inicio, b.hora_fim, b.motivo, b.criado_por
                FROM bloqueios_horarios b
                JOIN profissionais p ON b.profissional_id = p.id
                ORDER BY b.dia_semana, b.hora_inicio
            """, conn)
            conn.close()
            if bloqueios_df.empty:
                st.info("Nenhum bloqueio cadastrado ainda.")
            else:
                for _, bloq in bloqueios_df.iterrows():
                    with st.expander(f"{bloq['profissional']} - {bloq['dia_semana']} ({bloq['hora_inicio']} às {bloq['hora_fim']})"):
                        st.write(f"**Motivo:** {bloq['motivo'] or 'Sem motivo informado'}")
                        st.write(f"**Criado por:** {bloq['criado_por']}")
                        if st.button("Excluir este bloqueio", key=f"del_bloq_{bloq['id']}"):
                            conn_del = get_conn()
                            try:
                                conn_del.execute("DELETE FROM bloqueios_horarios WHERE id = ?", (bloq['id'],))
                                conn_del.commit()
                                st.success("Bloqueio excluído!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {str(e)}")
                            finally:
                                conn_del.close()

    else:  # Área do cliente
        if st.session_state.menu == "Editar Cadastro":
            st.header(f"Editar Meu Cadastro - {st.session_state.nome or st.session_state.user}")
            conn = get_conn()
            user_data = conn.execute("""
                SELECT nome_completo, email, telefone, endereco
                FROM usuarios
                WHERE username = ?
            """, (st.session_state.user,)).fetchone()
            conn.close()
            if not user_data:
                st.error("Erro ao carregar seus dados. Tente novamente.")
            else:
                nome_atual, email_atual, telefone_atual, endereco_atual = user_data
                def parse_endereco(texto):
                    if not texto:
                        return {}
                    partes = {}
                    cep_match = re.search(r'CEP\s*(\d{5}-?\d{3})', texto, re.IGNORECASE)
                    if cep_match:
                        partes['cep'] = cep_match.group(1)
                    uf_match = re.search(r'/([A-Z]{2})\b', texto.upper())
                    if uf_match:
                        partes['uf'] = uf_match.group(1)
                    elif re.search(r'([A-Z]{2})\b', texto.upper()):
                        uf_match = re.search(r'([A-Z]{2})\b', texto.upper())
                        if uf_match:
                            partes['uf'] = uf_match.group(1)
                    num_match = re.search(r',\s*(\d+[A-Za-z]?)(?:\s|$)', texto)
                    if num_match:
                        partes['numero'] = num_match.group(1)
                        rua_part = texto.split(',')[0].strip()
                        partes['logradouro'] = rua_part
                    comp_match = re.search(r'-\s*(.*?)\s*-\s*Bairro', texto, re.IGNORECASE)
                    if comp_match:
                        partes['complemento'] = comp_match.group(1)
                    bairro_match = re.search(r'-\s*(.*?)\s*,\s*Cidade', texto, re.IGNORECASE)
                    if bairro_match:
                        partes['bairro'] = bairro_match.group(1)
                    cidade_match = re.search(r',\s*(.*?)/[A-Z]{2}', texto)
                    if cidade_match:
                        partes['cidade'] = cidade_match.group(1).strip()
                    ref_match = re.search(r'\((.*?)\)', texto)
                    if ref_match:
                        partes['referencia'] = ref_match.group(1)
                    return partes
                endereco_partes = parse_endereco(endereco_atual)
                st.subheader("Dados Pessoais")
                with st.form("form_editar_dados"):
                    novo_nome = st.text_input("Nome completo", value=nome_atual)
                    novo_email = st.text_input("E-mail", value=email_atual)
                    novo_telefone = st.text_input("Telefone / WhatsApp", value=telefone_atual or "")
                    st.subheader("Endereço")
                    col_cep, col_uf = st.columns([2, 1])
                    with col_cep:
                        cep = st.text_input("CEP", value=endereco_partes.get('cep', ''), placeholder="00000-000", max_chars=9)
                    with col_uf:
                        uf_options = [""] + ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
                                            "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
                        uf_index = uf_options.index(endereco_partes.get('uf', '')) if endereco_partes.get('uf') in uf_options else 0
                        uf = st.selectbox("UF", uf_options, index=uf_index)
                    col_rua, col_num = st.columns([3, 1])
                    with col_rua:
                        logradouro = st.text_input("Rua / Avenida / Logradouro", value=endereco_partes.get('logradouro', ''))
                    with col_num:
                        numero = st.text_input("Número", value=endereco_partes.get('numero', ''), max_chars=10)
                    complemento = st.text_input("Complemento (bloco, apto, etc.)", value=endereco_partes.get('complemento', ''), placeholder="Apto 101, Bloco B, etc.")
                    bairro = st.text_input("Bairro", value=endereco_partes.get('bairro', ''))
                    cidade = st.text_input("Cidade", value=endereco_partes.get('cidade', ''))
                    referencia = st.text_area("Ponto de referência (opcional)", value=endereco_partes.get('referencia', ''), height=80, placeholder="Ex: Próximo ao mercado X, em frente à praça Y")
                    submitted_dados = st.form_submit_button("Salvar Dados Pessoais", type="primary")
                    if submitted_dados:
                        endereco_novo = []
                        if logradouro: endereco_novo.append(logradouro.strip())
                        if numero: endereco_novo.append(f", {numero.strip()}")
                        if complemento: endereco_novo.append(f" - {complemento.strip()}")
                        if bairro: endereco_novo.append(f" - {bairro.strip()}")
                        if cidade or uf:
                            cid_uf = f"{cidade.strip()}" if cidade else ""
                            if uf: cid_uf += f"/{uf}" if cid_uf else uf
                            endereco_novo.append(f", {cid_uf}")
                        if cep: endereco_novo.append(f" - CEP {cep.strip()}")
                        if referencia: endereco_novo.append(f" ({referencia.strip()})")
                        endereco_final = "".join(endereco_novo).strip(", -")
                        conn = get_conn()
                        try:
                            updates = []
                            params = []
                            if novo_nome.strip() and novo_nome.strip() != nome_atual:
                                updates.append("nome_completo = ?")
                                params.append(novo_nome.strip())
                            if novo_email.strip() and novo_email.strip() != email_atual:
                                updates.append("email = ?")
                                params.append(novo_email.strip())
                            if novo_telefone.strip() != (telefone_atual or ""):
                                updates.append("telefone = ?")
                                params.append(novo_telefone.strip())
                            if endereco_final != (endereco_atual or ""):
                                updates.append("endereco = ?")
                                params.append(endereco_final)
                            if updates:
                                query = f"UPDATE usuarios SET {', '.join(updates)} WHERE username = ?"
                                params.append(st.session_state.user)
                                conn.execute(query, params)
                                conn.commit()
                                st.session_state.nome = novo_nome.strip() if novo_nome.strip() else st.session_state.nome
                                st.success("Dados atualizados com sucesso!")
                                st.rerun()
                            else:
                                st.info("Nenhuma alteração detectada.")
                        except sqlite3.IntegrityError:
                            st.error("Este e-mail já está em uso por outro usuário.")
                        except Exception as e:
                            st.error(f"Erro ao salvar dados: {str(e)}")
                        finally:
                            conn.close()
                st.subheader("Alterar Senha (opcional)")
                with st.form("form_editar_senha"):
                    senha_atual_input = st.text_input("Senha atual", type="password")
                    nova_senha = st.text_input("Nova senha", type="password")
                    confirma_senha = st.text_input("Confirmar nova senha", type="password")
                    submitted_senha = st.form_submit_button("Alterar Senha", type="primary")
                    if submitted_senha:
                        if not senha_atual_input or not nova_senha:
                            st.error("Preencha todos os campos de senha para alterar.")
                        elif nova_senha != confirma_senha:
                            st.error("As novas senhas não coincidem.")
                        else:
                            conn = get_conn()
                            try:
                                user_row = conn.execute("SELECT password_hash, salt FROM usuarios WHERE username = ?", (st.session_state.user,)).fetchone()
                                if not verify_password(senha_atual_input, user_row[0], user_row[1]):
                                    st.error("Senha atual incorreta.")
                                else:
                                    salt_novo = generate_salt()
                                    hash_novo = hash_password(nova_senha, salt_novo)
                                    conn.execute("""
                                        UPDATE usuarios
                                        SET password_hash = ?, salt = ?
                                        WHERE username = ?
                                    """, (hash_novo, salt_novo, st.session_state.user))
                                    conn.commit()
                                    st.success("Senha alterada com sucesso!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao alterar senha: {str(e)}")
                            finally:
                                conn.close()

        elif st.session_state.menu == "Meus Pets":
            st.header(f"Meus Pets - {st.session_state.nome or st.session_state.user}")
            conn = get_conn()
            pets_df = pd.read_sql_query(
                "SELECT id, nome, especie_raca, idade, porte, observacoes, foto_base64 FROM pets WHERE criado_por = ? ORDER BY nome",
                conn, params=(st.session_state.user,)
            )
            conn.close()
            if pets_df.empty:
                st.info("Você ainda não cadastrou nenhum pet.")
            else:
                for _, pet in pets_df.iterrows():
                    with st.expander(f"{pet['nome']} ({pet['especie_raca']})"):
                        col_img, col_info = st.columns([1, 3])
                        with col_img:
                            if pet['foto_base64']:
                                st.image(base64.b64decode(pet['foto_base64']), width=200)
                            else:
                                st.image("https://via.placeholder.com/200?text=Sem+foto")
                        with col_info:
                            st.write(f"**Idade:** {pet['idade'] if pet['idade'] is not None else '—'} anos")
                            st.write(f"**Porte:** {pet['porte'] or '—'}")
                            st.write(f"**Observações:** {pet['observacoes'] or '—'}")
                            st.subheader("Editar pet")
                            edit_nome = st.text_input("Nome", value=pet['nome'], key=f"nome_edit_{pet['id']}")
                            edit_raca = st.text_input("Raça/Espécie", value=pet['especie_raca'], key=f"raca_edit_{pet['id']}")
                            edit_idade = st.number_input("Idade", min_value=0, value=pet['idade'] or 0, key=f"idade_edit_{pet['id']}")
                            edit_porte = st.selectbox("Porte", ["", "Pequeno", "Médio", "Grande", "Gigante"],
                                                     index=0 if not pet['porte'] else ["", "Pequeno", "Médio", "Grande", "Gigante"].index(pet['porte']),
                                                     key=f"porte_edit_{pet['id']}")
                            edit_obs = st.text_area("Observações", value=pet['observacoes'] or "", key=f"obs_edit_{pet['id']}")
                            edit_foto = st.file_uploader("Nova foto (opcional)", type=["jpg","jpeg","png"], key=f"foto_edit_{pet['id']}")
                            col_save, col_del, col_remove = st.columns(3)
                            with col_save:
                                if st.button("Salvar alterações", key=f"salvar_edit_{pet['id']}"):
                                    foto_b64 = pet['foto_base64']
                                    if edit_foto is not None:
                                        resized_bytes = resize_and_optimize_image(edit_foto)
                                        if resized_bytes:
                                            foto_b64 = base64.b64encode(resized_bytes).decode()
                                    conn = get_conn()
                                    conn.execute("""
                                        UPDATE pets SET nome=?, especie_raca=?, idade=?, porte=?, observacoes=?, foto_base64=?
                                        WHERE id=? AND criado_por=?
                                    """, (edit_nome, edit_raca, edit_idade if edit_idade > 0 else None, edit_porte or None, edit_obs or None, foto_b64, pet['id'], st.session_state.user))
                                    conn.commit()
                                    conn.close()
                                    st.success("Pet atualizado!")
                                    st.rerun()
                            with col_del:
                                confirm_key = f"confirm_delete_{pet['id']}"
                                if confirm_key not in st.session_state:
                                    st.session_state[confirm_key] = False
                                if st.button("Excluir pet", key=f"delete_btn_{pet['id']}"):
                                    st.session_state[confirm_key] = True
                                    st.rerun()
                                if st.session_state[confirm_key]:
                                    st.warning(f"Tem certeza que deseja excluir o pet **{pet['nome']}**?")
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("Sim, excluir definitivamente", key=f"yes_delete_{pet['id']}"):
                                            conn = get_conn()
                                            conn.execute("DELETE FROM pets WHERE id = ? AND criado_por = ?",
                                                        (pet['id'], st.session_state.user))
                                            conn.commit()
                                            conn.close()
                                            st.session_state[confirm_key] = False
                                            st.success(f"Pet **{pet['nome']}** excluído com sucesso!")
                                            st.rerun()
                                    with col_no:
                                        if st.button("Cancelar exclusão", key=f"no_delete_{pet['id']}"):
                                            st.session_state[confirm_key] = False
                                            st.rerun()
                            with col_remove:
                                if st.button("Remover foto", key=f"rem_foto_{pet['id']}"):
                                    conn = get_conn()
                                    conn.execute("UPDATE pets SET foto_base64 = NULL WHERE id = ? AND criado_por = ?", (pet['id'], st.session_state.user))
                                    conn.commit()
                                    conn.close()
                                    st.success("Foto removida!")
                                    st.rerun()
            st.subheader("Cadastrar novo pet")
            with st.form(key="form_novo_pet", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome *")
                    novo_raca = st.text_input("Espécie / Raça *")
                    novo_idade = st.number_input("Idade (anos)", min_value=0, value=0)
                with col2:
                    novo_porte = st.selectbox("Porte", ["", "Pequeno", "Médio", "Grande", "Gigante"])
                    novo_obs = st.text_area("Observações", height=100)
                    novo_foto = st.file_uploader("Foto (opcional)", type=["jpg","jpeg","png"])
                submitted = st.form_submit_button("Cadastrar pet", type="primary")
                if submitted:
                    if not novo_nome.strip() or not novo_raca.strip():
                        st.error("Nome e espécie/raça são obrigatórios")
                    else:
                        foto_b64 = None
                        if novo_foto is not None:
                            resized_bytes = resize_and_optimize_image(novo_foto)
                            if resized_bytes:
                                foto_b64 = base64.b64encode(resized_bytes).decode()
                        conn = get_conn()
                        try:
                            conn.execute("""
                                INSERT INTO pets (criado_por, nome, especie_raca, idade, porte, observacoes, foto_base64)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                st.session_state.user,
                                novo_nome.strip(),
                                novo_raca.strip(),
                                novo_idade if novo_idade > 0 else None,
                                novo_porte or None,
                                novo_obs.strip() or None,
                                foto_b64
                            ))
                            conn.commit()
                            st.success(f"Pet **{novo_nome.strip()}** cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao cadastrar pet: {str(e)}")
                        finally:
                            conn.close()

        elif st.session_state.menu == "Agendar Serviço":
            st.header(f"Agendar Serviço - {st.session_state.nome or st.session_state.user}")
            if 'agendamento_sucesso' not in st.session_state:
                st.session_state.agendamento_sucesso = False
            conn = get_conn()
            pets_df = pd.read_sql_query(
                "SELECT id, nome, especie_raca FROM pets WHERE criado_por = ? ORDER BY nome",
                conn, params=(st.session_state.user,)
            )
            profs_df = pd.read_sql_query("""
                SELECT id, nome_completo, funcao
                FROM profissionais
                WHERE ativo = 1
                ORDER BY nome_completo
            """, conn)
            endereco_cadastro_row = conn.execute(
                "SELECT endereco FROM usuarios WHERE username = ?",
                (st.session_state.user,)
            ).fetchone()
            endereco_cadastro = endereco_cadastro_row[0] if endereco_cadastro_row and endereco_cadastro_row[0] else ""
            conn.close()

            if pets_df.empty:
                st.warning("Você ainda não tem pets cadastrados. Vá em 'Meus Pets'.")
            else:
                pet_options = [f"{r['nome']} ({r['especie_raca']})" for _, r in pets_df.iterrows()]
                pet_selected = st.selectbox("Pet para o serviço", ["Selecione um pet..."] + pet_options, key="pet_select_agenda")
                if pet_selected != "Selecione um pet...":
                    pet_nome = pet_selected.split(" (")[0].strip()
                    pet_row = pets_df[pets_df['nome'] == pet_nome]
                    if pet_row.empty:
                        st.error("Pet não encontrado.")
                    else:
                        pet_id = int(pet_row.iloc[0]['id'])
                        col1, col2 = st.columns(2)
                        with col1:
                            data = st.date_input(
                                "Data desejada",
                                value=date.today() + timedelta(days=1),
                                min_value=date.today() + timedelta(days=1),
                                format="DD/MM/YYYY",
                                key="data_agenda"
                            )
                        with col2:
                            hora = st.time_input("Horário desejado", time(9, 0), step=1800, key="hora_agenda")

                        servico_map = {
                            "Banho Simples": "tosador",
                            "Tosa Higiênica": "tosador",
                            "Tosa Completa": "tosador",
                            "Banho + Tosa": "tosador",
                            "Consulta Veterinária": "veterinario",
                            "Consulta em Domicílio": "veterinario",
                            "Vacinação": "veterinario",
                            "Exames": "veterinario",
                            "Taxi Dog": "motorista",
                            "Outros": None
                        }

                        servico = st.selectbox("Serviço", list(servico_map.keys()), key="servico_agenda")

                        # Serviços que exigem endereço completo
                        SERVICOS_DOMICILIARES = {"Consulta em Domicílio", "Taxi Dog"}
                        exige_endereco = servico in SERVICOS_DOMICILIARES

                        obs = st.text_area("Observações / necessidades especiais", height=100, key="obs_agenda")

                        endereco_domiciliar = ""
                        if exige_endereco:
                            st.subheader(f"Endereço para {servico.lower()} *")
                            usar_mesmo_endereco = st.radio(
                                "O endereço é o mesmo do seu cadastro?",
                                options=["Sim (usar o endereço cadastrado)", "Não (informar outro endereço)"],
                                index=0,
                                horizontal=True,
                                key=f"usar_endereco_{servico.replace(' ', '_').replace('í', 'i')}"
                            )
                            if usar_mesmo_endereco == "Sim (usar o endereço cadastrado)":
                                if endereco_cadastro:
                                    endereco_domiciliar = st.text_area(
                                        "Endereço do cadastro (você pode editar se necessário)",
                                        value=endereco_cadastro,
                                        height=120,
                                        key=f"endereco_auto_{servico.replace(' ', '_').replace('í', 'i')}"
                                    )
                                else:
                                    st.warning("Você não possui endereço cadastrado. Por favor, informe abaixo ou atualize em 'Editar Cadastro'.")
                                    endereco_domiciliar = st.text_area(
                                        f"Endereço completo para {servico.lower()} *",
                                        height=120,
                                        placeholder="Rua Exemplo, 123 - Apto 45 - Bairro Centro - Campinas/SP - CEP 13000-000",
                                        key=f"endereco_manual_{servico.replace(' ', '_').replace('í', 'i')}"
                                    )
                            else:
                                endereco_domiciliar = st.text_area(
                                    f"Endereço completo para {servico.lower()} *",
                                    height=120,
                                    placeholder="Rua Exemplo, 123 - Apto 45 - Bairro Centro - Campinas/SP - CEP 13000-000",
                                    key=f"endereco_manual_{servico.replace(' ', '_').replace('í', 'i')}"
                                )
                            if not endereco_domiciliar.strip():
                                st.error(f"O endereço é obrigatório para {servico}.")
                                st.stop()

                        if st.button("Agendar", type="primary"):
                            show_paw_prints()
                            data_str = data.strftime('%d/%m/%Y')
                            hora_str = hora.strftime('%H:%M')
                            data_hora_str = f"{data_str} às {hora_str}"
                            data_hora_dt = datetime.combine(data, hora)

                            if data < date.today():
                                st.error("Não é possível agendar para datas passadas.")
                            elif not (HORARIO_ABERTURA <= hora <= HORARIO_FECHAMENTO):
                                st.error(f"Horário fora do expediente ({HORARIO_ABERTURA.strftime('%H:%M')} às {HORARIO_FECHAMENTO.strftime('%H:%M')}).")
                            else:
                                conn = get_conn()

                                def get_funcao_filter(serv):
                                    if serv in ["Consulta Veterinária", "Consulta em Domicílio", "Vacinação", "Exames"]:
                                        return lambda f: any(palavra in f.lower() for palavra in ["veterin", "vet", "veter"])
                                    elif serv in ["Banho Simples", "Tosa Higiênica", "Tosa Completa", "Banho + Tosa"]:
                                        return lambda f: "tos" in f.lower()
                                    elif serv == "Taxi Dog":
                                        return lambda f: any(palavra in f.lower() for palavra in ["motorista", "taxi", "taxidog", "taxi dog"])
                                    else:
                                        return lambda f: True

                                filtro_funcao = get_funcao_filter(servico)
                                profs_df['funcao_lower'] = profs_df['funcao'].fillna("").str.strip().str.lower()
                                profs_disponiveis = profs_df[profs_df['funcao_lower'].apply(filtro_funcao)]
                                profs_df.drop(columns=['funcao_lower'], inplace=True)

                                if profs_disponiveis.empty:
                                    st.error(f"Não há profissional disponível para o serviço '{servico}' no momento. Contate o PET CLUB.")
                                    conn.close()
                                    st.stop()

                                bloqueado = False
                                for _, prof in profs_disponiveis.iterrows():
                                    count = conn.execute("""
                                        SELECT COUNT(*) FROM bloqueios_horarios
                                        WHERE profissional_id = ?
                                          AND dia_semana = ?
                                          AND hora_inicio <= ?
                                          AND hora_fim >= ?
                                    """, (prof['id'], data.strftime('%A'), hora.strftime('%H:%M'), hora.strftime('%H:%M'))).fetchone()[0]
                                    if count > 0:
                                        bloqueado = True
                                        break

                                if bloqueado:
                                    st.error("Horário bloqueado para todos os profissionais disponíveis neste dia.")
                                    conn.close()
                                    st.stop()

                                escolhido = None
                                dia_str = data.strftime('%d/%m/%Y')
                                for _, prof in profs_disponiveis.iterrows():
                                    agendamentos = conn.execute("""
                                        SELECT data_hora_pref
                                        FROM atendimentos
                                        WHERE profissional_id = ?
                                          AND status NOT IN ('Cancelado', 'Não Compareceu')
                                          AND substr(data_hora_pref, 1, 10) = ?
                                    """, (prof['id'], dia_str)).fetchall()
                                    conflito = False
                                    for (dh,) in agendamentos:
                                        try:
                                            dh_dt = datetime.strptime(dh, "%d/%m/%Y às %H:%M")
                                            minutos_diff = abs((data_hora_dt - dh_dt).total_seconds() / 60)
                                            if minutos_diff < INTERVALO_MINIMO_MINUTOS:
                                                conflito = True
                                                break
                                        except ValueError:
                                            pass
                                    if not conflito:
                                        escolhido = {'id': prof['id'], 'nome': prof['nome_completo']}
                                        break

                                if escolhido is None:
                                    st.error("Todos os profissionais disponíveis já têm agendamento muito próximo neste horário. Tente outro slot.")
                                else:
                                    protocolo = uuid.uuid4().hex[:10].upper()
                                    descricao_final = obs.strip() if obs else ""
                                    if endereco_domiciliar.strip():
                                        if descricao_final:
                                            descricao_final += "\n\n"
                                        descricao_final += f"**Endereço para {servico}:**\n{endereco_domiciliar.strip()}"

                                    try:
                                        cur = conn.cursor()
                                        cur.execute("""
                                            INSERT INTO atendimentos
                                            (id, servico, pet_id, data_hora_pref, descricao, criado_por, profissional_id)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                        """, (protocolo, servico, pet_id, data_hora_str, descricao_final or None, st.session_state.user, escolhido['id']))
                                        conn.commit()
                                        st.success(f"**Agendamento confirmado!**\nProtocolo: **{protocolo}**\nProfissional: {escolhido['nome']}")
                                        if exige_endereco:
                                            st.info(f"Endereço registrado para {servico}:\n{endereco_domiciliar}")
                                        st.session_state.agendamento_sucesso = True
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao salvar agendamento: {str(e)}")

                                conn.close()

            if st.session_state.get('agendamento_sucesso', False):
                st.success("Agendamento realizado com sucesso! Formulário limpo para novo agendamento.")
                st.session_state.agendamento_sucesso = False

        elif st.session_state.menu == "Meus Agendamentos":
            st.header(f"Meus Agendamentos - {st.session_state.nome or st.session_state.user}")
            conn = get_conn()
            try:
                df = pd.read_sql_query("""
                    SELECT
                        a.id AS protocolo,
                        p.nome AS pet,
                        a.servico,
                        a.data_hora_pref,
                        a.status,
                        a.descricao,
                        pr.nome_completo AS profissional,
                        a.data_cancelamento
                    FROM atendimentos a
                    LEFT JOIN pets p ON a.pet_id = p.id
                    LEFT JOIN profissionais pr ON a.profissional_id = pr.id
                    WHERE a.criado_por = ?
                    ORDER BY a.data_agendamento DESC
                """, conn, params=(st.session_state.user,))
                if df.empty:
                    st.info("Você ainda não tem agendamentos.")
                else:
                    for _, row in df.iterrows():
                        with st.expander(f"{row['servico']} • {row['pet'] or '—'} • {row['data_hora_pref']}"):
                            st.markdown(f"**Protocolo:** {row['protocolo']}")
                            status_text = row['status']
                            if row['status'] == "Pendente":
                                status_display = f'<span style="background-color:#fff3cd; color:#856404; padding:4px 8px; border-radius:6px; font-weight:bold;">{status_text}</span>'
                            elif row['status'] == "Finalizado":
                                status_display = f'<span style="background-color:#d4edda; color:#155724; padding:4px 8px; border-radius:6px; font-weight:bold;">{status_text}</span>'
                            else:
                                status_display = status_text
                            if row['status'] == "Cancelado" and row['data_cancelamento']:
                                try:
                                    cancel_dt = datetime.strptime(row['data_cancelamento'], "%Y-%m-%d %H:%M:%S")
                                    formatted_cancel = cancel_dt.strftime("%d/%m/%Y às %H:%M")
                                    status_display += f" em {formatted_cancel}"
                                except:
                                    status_display += f" em {row['data_cancelamento']}"
                            st.markdown(f"**Status:** {status_display}", unsafe_allow_html=True)
                            st.markdown(f"**Profissional:** {row['profissional'] or '—'}")
                            st.markdown(f"**Observações:** {row['descricao'] or '—'}")
                            if row['status'] == "Pendente":
                                if st.button("Cancelar agendamento", key=f"cancel_{row['protocolo']}"):
                                    dt = datetime.strptime(row['data_hora_pref'], "%d/%m/%Y às %H:%M")
                                    if (dt - datetime.now()) < timedelta(hours=MIN_HORAS_ANTECEDENCIA_CANCEL):
                                        st.error(f"Cancelamento só permitido com {MIN_HORAS_ANTECEDENCIA_CANCEL}h de antecedência.")
                                    else:
                                        conn.execute("""
                                            UPDATE atendimentos
                                            SET status = 'Cancelado',
                                                data_cancelamento = datetime('now','localtime')
                                            WHERE id = ?
                                        """, (row['protocolo'],))
                                        conn.commit()
                                        st.success("Agendamento cancelado!")
                                        st.rerun()
            except Exception as e:
                st.error(f"Erro ao carregar agendamentos: {str(e)}")
            finally:
                conn.close()

# Rodapé
st.markdown("---")
st.caption(f"{APP_NAME} • Sistema de Agendamento • {YEAR}")