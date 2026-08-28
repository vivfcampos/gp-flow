"""
Autenticação multiusuário do GP Flow.

Duas formas de autenticar, tentadas nesta ordem:

1. **Active Directory (LDAP)** — se LDAP_SERVER e LDAP_DOMAIN estiverem
   configurados (variáveis de ambiente), tenta um bind direto no AD com o
   usuário/senha digitados. Não guarda nem precisa de conta de serviço.
   Ver `_ldap_config()` para o formato das variáveis.

2. **Local** (banco de dados / .streamlit/secrets.toml) — usuários com
   senha em hash PBKDF2-SHA256, cadastrados pela tela Usuários (server/)
   ou manualmente em .streamlit/secrets.toml (fonte legada, opcional),
   no formato:

    [auth]
    # nome_de_usuario = "hash_gerado"
    lucas = "pbkdf2_sha256$260000$<salt_hex>$<hash_hex>"
    cadu  = "pbkdf2_sha256$260000$<salt_hex>$<hash_hex>"

Para gerar o hash de uma senha local, rode:
    python -m functions.auth "minha-senha"
e cole a linha impressa dentro de [auth] no secrets.

As senhas locais NUNCA são guardadas em texto puro — apenas o hash
PBKDF2-SHA256. Senhas de AD não são guardadas em lugar nenhum: o bind LDAP
usa a senha só na hora da tentativa de login.
"""
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

_ALGO = "pbkdf2_sha256"
_ITERS = 260_000

ARQUIVO_CONFIG_AUTH = Path(__file__).parent.parent / "config" / "auth.json"
_CONFIG_AUTH_PADRAO = {"modo": "local", "ldap_server": "", "ldap_domain": ""}
_MODOS_VALIDOS = ("local", "ldap", "ldap_fallback")


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
    """
    Lê os usuários no formato {usuario: hash}, juntando duas fontes:

    - Banco de dados (tabela `usuarios`) — onde entram os usuários criados
      pela tela de administração (server/ + web/).
    - .streamlit/secrets.toml — usuários legados configurados manualmente
      (fonte opcional, arquivo pode nem existir).

    Em caso de mesmo nome nos dois lugares, o banco tem prioridade.
    """
    usuarios = {}

    try:
        from functions.banco import criar_tabelas, usuarios_hash
        criar_tabelas()
        usuarios.update(usuarios_hash())
    except Exception:
        pass

    for nome, h in _tabela_usuarios_toml().items():
        usuarios.setdefault(nome, h)

    return usuarios


def _tabela_usuarios_toml():
    """Lê usuarios/hashes direto de .streamlit/secrets.toml, se existir."""
    import tomllib
    caminho = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if not caminho.exists():
        return {}
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)
    return dict(dados.get("auth", {}))


def carregar_config_auth() -> dict:
    """
    Lê o modo de autenticação e os dados do AD de config/auth.json —
    editável pela tela Configurações (server/ + web/). Se o arquivo não
    existir ainda, devolve o padrão (modo "local", sem LDAP).
    """
    if ARQUIVO_CONFIG_AUTH.exists():
        with open(ARQUIVO_CONFIG_AUTH, encoding="utf-8") as f:
            dados = json.load(f)
        return {**_CONFIG_AUTH_PADRAO, **dados}
    return dict(_CONFIG_AUTH_PADRAO)


def salvar_config_auth(modo: str, ldap_server: str = "", ldap_domain: str = ""):
    """Salva o modo de autenticação (local / ldap / ldap_fallback) e os dados do AD."""
    if modo not in _MODOS_VALIDOS:
        raise ValueError(f"Modo de autenticação inválido: {modo!r}.")
    ARQUIVO_CONFIG_AUTH.parent.mkdir(exist_ok=True)
    with open(ARQUIVO_CONFIG_AUTH, "w", encoding="utf-8") as f:
        json.dump(
            {"modo": modo, "ldap_server": (ldap_server or "").strip(), "ldap_domain": (ldap_domain or "").strip()},
            f, ensure_ascii=False, indent=4,
        )


def _ldap_config():
    """
    Lê o servidor/domínio do AD: primeiro de config/auth.json (tela
    Configurações), depois de LDAP_SERVER/LDAP_DOMAIN (variáveis de
    ambiente — útil pra travar isso via deploy/infra sem passar pela tela).
    Retorna None se não tiver os dois definidos em nenhuma das duas fontes.
    """
    config = carregar_config_auth()
    servidor = config.get("ldap_server") or os.environ.get("LDAP_SERVER")
    dominio = config.get("ldap_domain") or os.environ.get("LDAP_DOMAIN")
    if not servidor or not dominio:
        return None
    return {"servidor": servidor, "dominio": dominio}


def ldap_configurado() -> bool:
    return _ldap_config() is not None


def autenticar_ldap(usuario: str, senha: str) -> bool:
    """
    Autentica contra o AD via bind direto (LDAP simple bind) — conecta como
    o próprio usuário, com a senha que ele digitou; se o bind funcionar, a
    senha está correta. Não precisa de conta de serviço nem guarda nada.

    Qualquer erro (LDAP não configurado, servidor fora do ar, credenciais
    erradas) vira False silenciosamente — nunca derruba o processo, pra
    login local continuar funcionando como alternativa.
    """
    config = _ldap_config()
    if not config or not usuario or not senha:
        return False
    try:
        from ldap3 import Server, Connection, SIMPLE
        conn = Connection(
            Server(config["servidor"]),
            user=f"{usuario}@{config['dominio']}",
            password=senha,
            authentication=SIMPLE,
        )
        if conn.bind():
            conn.unbind()
            return True
        return False
    except Exception:
        return False


def autenticar(usuario: str, senha: str) -> bool:
    """
    True se o usuário/senha confere, respeitando o modo escolhido na tela
    Configurações (config/auth.json):

    - "local": só usuários locais (banco + secrets) — AD nem é tentado.
    - "ldap": só Active Directory — usuários locais não funcionam mais.
    - "ldap_fallback": tenta o AD primeiro, cai pros usuários locais se o
      AD não validar (inclusive se o AD estiver fora do ar).
    """
    usuario_norm = (usuario or "").strip().lower()
    if not usuario_norm:
        verificar_senha(senha, "x$1$00$00")
        return False

    modo = carregar_config_auth().get("modo", "local")

    if modo in ("ldap", "ldap_fallback"):
        if autenticar_ldap(usuario_norm, senha):
            return True
        if modo == "ldap":
            verificar_senha(senha, "x$1$00$00")
            return False

    usuarios = _tabela_usuarios()
    h = usuarios.get(usuario_norm)
    if not h:
        # roda a verificação mesmo sem usuário, para não vazar tempo de resposta
        verificar_senha(senha, "x$1$00$00")
        return False
    return verificar_senha(senha, h)


# ── Utilitário de linha de comando: gerar hash de uma senha ───────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m functions.auth \"a-senha-desejada\"")
        print("     (rode dentro da pasta do projeto, com o venv ativo)")
        sys.exit(1)
    senha = sys.argv[1]
    usuario = sys.argv[2] if len(sys.argv) > 2 else "usuario"
    print()
    print("Cole esta linha dentro de [auth] em .streamlit/secrets.toml:")
    print(f'    {usuario} = "{gerar_hash(senha)}"')
    print()
