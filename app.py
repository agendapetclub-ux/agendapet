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

# Animação estilo pegadas
def show_paw_prints():
    st.markdown("""
        <style>
        @keyframes pawStep {
            0%   { opacity: 0; transform: translate(0vw, 100vh) scale(0.7) rotate(0deg); }
            40%  { opacity: 1; transform: translate(5vw, 70vh) scale(1.0) rotate(5deg); }
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

# Inicialização do banco
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        role TEXT NOT NULL, nome_completo TEXT NOT NULL, telefone TEXT, email TEXT UNIQUE,
        funcao TEXT, data_cadastro TEXT DEFAULT (datetime('now','localtime')), ativo INTEGER DEFAULT 1
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

    cur.execute("""CREATE TABLE IF NOT EXISTS bloqueios_agenda (
        id INTEGER PRIMARY KEY AUTOINCREMENT, profissional_id INTEGER NOT NULL,
        data_inicio TEXT NOT NULL, data_fim TEXT NOT NULL, motivo TEXT,
        data_criacao TEXT DEFAULT (datetime('now','localtime')), criado_por TEXT NOT NULL,
        FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
        FOREIGN KEY (criado_por) REFERENCES usuarios(username)
    )""")

    cur.execute("PRAGMA table_info(atendimentos)")
    columns = [col[1] for col in cur.fetchall()]
    if 'data_cancelamento' not in columns:
        cur.execute("ALTER TABLE atendimentos ADD COLUMN data_cancelamento TEXT")
        conn.commit()

    if not cur.execute("SELECT 1 FROM profissionais LIMIT 1").fetchone():
        cur.executemany("INSERT OR IGNORE INTO profissionais (nome_completo, funcao, telefone, email, ativo) VALUES (?, ?, ?, ?, ?)",
                        [("Ana Silva", "Tosadora", "(19) 99999-9999", "ana@petclub.com", 1),
                         ("Carlos Souza", "Tosador", "(19) 88888-8888", "carlos@petclub.com", 1)])

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

for key in ["user", "nome", "email", "role", "menu"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.user and st.session_state.menu is None:
    st.session_state.menu = "Serviços Agendados" if st.session_state.role == "admin" else "Meus Pets"

# SIDEBAR
st.sidebar.title(f"🐾 {APP_NAME}")
if st.session_state.user:
    st.sidebar.write(f"Olá, **{st.session_state.nome or st.session_state.user}**")

    menu_options = (
        ["Serviços Agendados", "Clientes Cadastrados", "Pets Cadastrados", "Profissionais", "Bloqueios de Agenda", "Sair"]
        if st.session_state.role == "admin" else
        ["Agendar Serviço", "Meus Pets", "Meus Agendamentos", "Sair"]
    )

    selected = st.sidebar.radio("Menu", menu_options,
                                index=menu_options.index(st.session_state.menu) if st.session_state.menu in menu_options else 0)
    st.session_state.menu = selected

    if st.session_state.menu == "Sair":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.sidebar.caption(f"{APP_NAME} • Sistema de Agendamento • {YEAR}")

# CONSULTA PÚBLICA (com profissional visível)
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
                    a.id, 
                    a.servico, 
                    a.data_hora_pref, 
                    a.status, 
                    a.descricao,
                    p.nome as pet_nome, 
                    p.especie_raca, 
                    u.nome_completo as dono,
                    a.data_cancelamento,
                    pr.nome_completo as profissional
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
                SELECT username, password_hash, salt, role, nome_completo, email, ativo
                FROM usuarios WHERE (username = ? OR email = ?) AND ativo = 1
            """, (usr.strip(), usr.strip())).fetchone()
            conn.close()
            if row and verify_password(pwd, row[1], row[2]):
                st.session_state.user = normalize_username(row[0])
                st.session_state.nome = row[4]
                st.session_state.email = row[5]
                st.session_state.role = row[3]
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
                try:
                    conn = get_conn()
                    conn.execute("""
                        INSERT INTO usuarios (username, password_hash, salt, role, nome_completo, email, telefone)
                        VALUES (?, ?, ?, 'cliente', ?, ?, ?)
                    """, (username_norm, hash_pw, salt, nome.strip(), email_cad.strip(), tel.strip() or None))
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
    if st.session_state.role == "admin":
        if st.session_state.menu == "Serviços Agendados":
            st.header("Serviços Agendados - Painel Administrativo")

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

                # Exibe tabela com ações (apenas admin)
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
                                    conn.execute("""
                                        UPDATE atendimentos 
                                        SET status = 'Finalizado'
                                        WHERE id = ?
                                    """, (row['protocolo'],))
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

                    # Confirmação de exclusão
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

        elif st.session_state.menu == "Clientes Cadastrados":
            st.header("Clientes Cadastrados")

            conn = get_conn()
            df = pd.read_sql_query("""
                SELECT username, nome_completo, email, telefone, data_cadastro, ativo
                FROM usuarios 
                WHERE role = 'cliente' AND ativo = 1
                ORDER BY data_cadastro DESC
            """, conn)
            conn.close()

            if df.empty:
                st.info("Nenhum cliente cadastrado ainda.")
            else:
                df['data_cadastro_formatted'] = df['data_cadastro'].apply(
                    lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") if pd.notna(x) else "—"
                )

                st.dataframe(
                    df[['nome_completo', 'email', 'telefone', 'data_cadastro_formatted', 'ativo']],
                    column_config={
                        "nome_completo": "Nome",
                        "email": "E-mail",
                        "telefone": "Telefone",
                        "data_cadastro_formatted": "Cadastrado em",
                        "ativo": "Ativo"
                    },
                    use_container_width=True,
                    hide_index=True
                )

        elif st.session_state.menu == "Pets Cadastrados":
            st.header("Pets Cadastrados")

            conn = get_conn()
            df = pd.read_sql_query("""
                SELECT 
                    p.id, p.nome, p.especie_raca, p.idade, p.porte, 
                    p.observacoes, u.nome_completo AS dono, p.data_cadastro
                FROM pets p
                JOIN usuarios u ON p.criado_por = u.username
                ORDER BY p.data_cadastro DESC
            """, conn)
            conn.close()

            if df.empty:
                st.info("Nenhum pet cadastrado ainda.")
            else:
                df['data_cadastro_formatted'] = df['data_cadastro'].apply(
                    lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") if pd.notna(x) else "—"
                )

                st.dataframe(
                    df[['nome', 'especie_raca', 'idade', 'porte', 'dono', 'data_cadastro_formatted']],
                    column_config={
                        "nome": "Nome",
                        "especie_raca": "Espécie/Raça",
                        "idade": "Idade",
                        "porte": "Porte",
                        "dono": "Dono",
                        "data_cadastro_formatted": "Cadastrado em"
                    },
                    use_container_width=True,
                    hide_index=True
                )

        elif st.session_state.menu == "Profissionais":
            st.header("Profissionais")

            st.subheader("Adicionar Novo Profissional")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                novo_nome = st.text_input("Nome completo *", key="novo_prof_nome")
            with col2:
                novo_telefone = st.text_input("Telefone", key="novo_prof_tel")
            with col3:
                novo_email = st.text_input("E-mail", key="novo_prof_email")
            with col4:
                nova_funcao = st.selectbox("Função", ["Tosador(a)", "Veterinário(a)", "Auxiliar", "Balconista", "Recepcionista", "Estagiário"], key="novo_prof_funcao")

            col_foto, col_ativo = st.columns(2)
            with col_foto:
                nova_foto = st.file_uploader("Foto (opcional)", type=["jpg","jpeg","png"], key="novo_prof_foto")
            with col_ativo:
                ativo = st.checkbox("Ativo", value=True, key="novo_prof_ativo")

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
                    try:
                        conn.execute("""
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
                        conn.commit()
                        st.success(f"Profissional **{novo_nome.strip()}** adicionado!")
                        st.rerun()
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
            conn.close()

            if df.empty:
                st.info("Nenhum profissional cadastrado ainda.")
            else:
                for _, row in df.iterrows():
                    cols = st.columns([1, 3, 2, 2, 1, 1])
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
                        if st.button("Excluir", key=f"del_prof_{row['id']}"):
                            conn = get_conn()
                            try:
                                conn.execute("DELETE FROM profissionais WHERE id = ?", (row['id'],))
                                conn.commit()
                                st.success("Profissional excluído!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {str(e)}")
                            finally:
                                conn.close()

        elif st.session_state.menu == "Bloqueios de Agenda":
            st.header("Bloqueios de Agenda")
            st.info("Funcionalidade de bloqueios em desenvolvimento. Em breve você poderá adicionar períodos bloqueados para profissionais.")

    else:  # Área do cliente
        if st.session_state.menu == "Meus Pets":
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

            conn = get_conn()
            pets_df = pd.read_sql_query(
                "SELECT id, nome, especie_raca FROM pets WHERE criado_por = ? ORDER BY nome",
                conn, params=(st.session_state.user,)
            )
            profs = pd.read_sql_query("SELECT id, nome_completo FROM profissionais WHERE ativo = 1 ORDER BY nome_completo", conn)
            conn.close()

            if pets_df.empty:
                st.warning("Você ainda não tem pets cadastrados. Vá em 'Meus Pets'.")
            else:
                pet_options = [f"{r['nome']} ({r['especie_raca']})" for _, r in pets_df.iterrows()]
                pet_selected = st.selectbox("Pet para o serviço", ["Selecione um pet..."] + pet_options)

                if pet_selected != "Selecione um pet...":
                    pet_nome = pet_selected.split(" (")[0].strip()
                    pet_row = pets_df[pets_df['nome'] == pet_nome]
                    if pet_row.empty:
                        st.error("Pet não encontrado.")
                    else:
                        pet_id = int(pet_row.iloc[0]['id'])

                        col1, col2 = st.columns(2)
                        with col1:
                            data = st.date_input("Data desejada", date.today() + timedelta(days=1), min_value=date.today() + timedelta(days=1))
                        with col2:
                            hora = st.time_input("Horário desejado", time(9, 0), step=1800)

                        servico = st.selectbox("Serviço", ["Banho Simples", "Tosa Higiênica", "Tosa Completa", "Banho + Tosa", "Consulta Veterinária", "Vacinação", "Exames", "Outros"])

                        obs = st.text_area("Observações / necessidades especiais", height=100)

                        if st.button("Agendar", type="primary"):
                            show_paw_prints()

                            data_hora_str = f"{data.strftime('%d/%m/%Y')} às {hora.strftime('%H:%M')}"
                            data_hora_dt = datetime.combine(data, hora)

                            if data < date.today():
                                st.error("Não é possível agendar para datas passadas.")
                            elif not (HORARIO_ABERTURA <= hora <= HORARIO_FECHAMENTO):
                                st.error(f"Horário fora do expediente ({HORARIO_ABERTURA.strftime('%H:%M')} às {HORARIO_FECHAMENTO.strftime('%H:%M')}).")
                            else:
                                conn = get_conn()

                                bloqueado = False
                                for _, prof in profs.iterrows():
                                    bloqueio = conn.execute("""
                                        SELECT COUNT(*) FROM bloqueios_agenda 
                                        WHERE profissional_id = ? 
                                        AND data_inicio <= ? 
                                        AND data_fim >= ?
                                    """, (int(prof['id']), data.strftime('%Y-%m-%d'), data.strftime('%Y-%m-%d'))).fetchone()[0]

                                    if bloqueio > 0:
                                        bloqueado = True
                                        break

                                if bloqueado:
                                    st.error("Este período está bloqueado para todos os profissionais disponíveis.")
                                else:
                                    escolhido = None
                                    for _, prof in profs.iterrows():
                                        conflito = conn.execute("""
                                            SELECT COUNT(*) FROM atendimentos 
                                            WHERE profissional_id = ? 
                                            AND status NOT IN ('Cancelado', 'Não Compareceu')
                                            AND data_hora_pref LIKE ?
                                        """, (int(prof['id']), f"{data.strftime('%d/%m/%Y')} %")).fetchone()[0]

                                        if conflito == 0:
                                            ultimo_raw = conn.execute("""
                                                SELECT MAX(strftime('%s', substr(data_hora_pref, 7,4)||'-'||substr(data_hora_pref, 4,2)||'-'||substr(data_hora_pref, 1,2)||' '||substr(data_hora_pref, -5))) 
                                                FROM atendimentos 
                                                WHERE profissional_id = ? AND status NOT IN ('Cancelado', 'Não Compareceu')
                                            """, (int(prof['id']),)).fetchone()[0]

                                            ultimo = float(ultimo_raw) if ultimo_raw is not None else None

                                            if ultimo is None or (data_hora_dt.timestamp() - ultimo) >= (INTERVALO_MINIMO_MINUTOS * 60):
                                                escolhido = {'id': int(prof['id']), 'nome': prof['nome_completo']}
                                                break

                                    if escolhido is None:
                                        st.error("Não há profissional disponível neste horário.")
                                    else:
                                        protocolo = uuid.uuid4().hex[:10].upper()
                                        try:
                                            cur = conn.cursor()
                                            cur.execute("""
                                                INSERT INTO atendimentos 
                                                (id, servico, pet_id, data_hora_pref, descricao, criado_por, profissional_id)
                                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                            """, (protocolo, servico, pet_id, data_hora_str, obs or None, st.session_state.user, escolhido['id']))
                                            conn.commit()
                                            st.success(f"Agendamento confirmado! Protocolo: **{protocolo}**")
                                        except Exception as e:
                                            st.error(f"Erro ao agendar: {str(e)}")
                                conn.close()

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
                            if row['status'] == "Cancelado" and row['data_cancelamento']:
                                try:
                                    cancel_dt = datetime.strptime(row['data_cancelamento'], "%Y-%m-%d %H:%M:%S")
                                    formatted_cancel = cancel_dt.strftime("%d/%m/%Y às %H:%M")
                                    status_text += f" em {formatted_cancel}"
                                except:
                                    status_text += f" em {row['data_cancelamento']}"
                            st.markdown(f"**Status:** {status_text}")
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