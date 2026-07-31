"""
Autenticação multiusuário do GP Flow.

Os usuários ficam em st.secrets (persistente no Streamlit Cloud), no formato:

    [auth]
    # nome_de_usuario = "hash_gerado"
    lucas = "pbkdf2_sha256$260000$<salt_hex>$<hash_hex>"
    cadu  = "pbkdf2_sha256$260000$<salt_hex>$<hash_hex>"

Para gerar o hash de uma senha, rode localmente:
    python -m functions.auth "minha-senha"
e cole a linha impressa dentro de [auth] no secrets.

As senhas NUNCA são guardadas em texto puro — apenas o hash PBKDF2-SHA256.
"""
import hashlib
import hmac
import os
import sys

_ALGO = "pbkdf2_sha256"
_ITERS = 260_000


def gerar_hash(senha: str, iteracoes: int = _ITERS) -> str:
    """Gera um hash seguro (salt aleatório + PBKDF2-SHA256) para armazenar."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)
    return f"{_ALGO}${iteracoes}${salt.hex()}${dk.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Compara a senha digitada com o hash guardado, de forma segura."""
    try:
        algo, iters, salt_hex, hash_hex = hash_armazenado.split("$")
        if algo != _ALGO:
            return False
        salt = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(dk, esperado)
    except (ValueError, AttributeError):
        return False


def _tabela_usuarios():
    """Lê os usuários de st.secrets['auth']. Retorna dict {usuario: hash}."""
    import streamlit as st
    try:
        return dict(st.secrets["auth"])
    except (KeyError, FileNotFoundError):
        return {}


def autenticar(usuario: str, senha: str) -> bool:
    """True se o par usuário/senha confere com o que está em secrets."""
    usuarios = _tabela_usuarios()
    h = usuarios.get((usuario or "").strip().lower())
    if not h:
        # roda a verificação mesmo sem usuário, para não vazar tempo de resposta
        verificar_senha(senha, "x$1$00$00")
        return False
    return verificar_senha(senha, h)


def exigir_login():
    """
    Bloqueia o app até o usuário logar. Chame no topo do app.py, antes de
    montar a navegação. Retorna o nome do usuário logado.
    """
    import streamlit as st

    if st.session_state.get("_auth_user"):
        return st.session_state["_auth_user"]

    usuarios = _tabela_usuarios()

    st.markdown(
        "<h1 style='text-align:center;margin-top:8vh;'>🔐 GP Flow</h1>",
        unsafe_allow_html=True,
    )

    if not usuarios:
        st.warning(
            "Nenhum usuário configurado. Adicione usuários em **Settings → Secrets** "
            "no Streamlit Cloud (seção `[auth]`). Veja `functions/auth.py` para gerar os hashes."
        )
        st.stop()

    _, meio, _ = st.columns([1, 1.4, 1])
    with meio:
        with st.form("login_form"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if entrar:
            if autenticar(usuario, senha):
                st.session_state["_auth_user"] = usuario.strip().lower()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    st.stop()


def logout_button():
    """Renderiza um botão de sair na sidebar."""
    import streamlit as st
    user = st.session_state.get("_auth_user")
    if not user:
        return
    with st.sidebar:
        st.caption(f"👤 Logado como **{user}**")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.pop("_auth_user", None)
            st.rerun()


# ── Utilitário de linha de comando: gerar hash de uma senha ───────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m functions.auth \"a-senha-desejada\"")
        print("     (rode dentro da pasta do projeto, com o venv ativo)")
        sys.exit(1)
    senha = sys.argv[1]
    usuario = sys.argv[2] if len(sys.argv) > 2 else "usuario"
    print()
    print("Cole esta linha dentro de [auth] no secrets do Streamlit Cloud:")
    print(f'    {usuario} = "{gerar_hash(senha)}"')
    print()
