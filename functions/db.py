"""
Camada de banco unificada do GP Flow.

Suporta dois back-ends de forma transparente:

- **SQLite** (padrão, desenvolvimento local): usado quando não há configuração
  de Postgres. O arquivo fica em config.DATABASE.
- **PostgreSQL** (produção, ex.: Neon): usado quando existe uma URL de conexão
  em st.secrets["postgres"]["url"] ou na variável de ambiente DATABASE_URL.

O restante do código (functions/banco.py) usa sempre:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("... ? ...", (a, b))     # placeholders no estilo SQLite
    row["coluna"]                        # acesso por nome

Esta camada traduz os placeholders `?` -> `%s` e entrega linhas acessíveis por
nome nos dois bancos, então quase nada muda em banco.py.
"""
import os
import re


# ── Detecção do back-end ──────────────────────────────────────────────────────
def _postgres_url():
    """Retorna a URL do Postgres se configurada, senão None (usa SQLite)."""
    # 1) st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        url = st.secrets.get("postgres", {}).get("url")
        if url:
            return url
    except Exception:
        pass
    # 2) variável de ambiente (deploy fora do Streamlit)
    return os.environ.get("DATABASE_URL")


def usando_postgres() -> bool:
    return _postgres_url() is not None


# ── Adaptação de SQL entre os dois dialetos ───────────────────────────────────
def _traduzir_sql(sql: str) -> str:
    """
    Ajusta o SQL escrito no estilo SQLite para rodar no Postgres.
    - placeholders ? -> %s (respeitando literais entre aspas)
    - AUTOINCREMENT vira coluna serial
    - REAL -> DOUBLE PRECISION
    - INSERT OR REPLACE / OR IGNORE -> ON CONFLICT
    """
    if not usando_postgres():
        return sql

    # troca ? por %s, mas não dentro de strings entre aspas simples
    out = []
    in_str = False
    for ch in sql:
        if ch == "'":
            in_str = not in_str
            out.append(ch)
        elif ch == "?" and not in_str:
            out.append("%s")
        else:
            out.append(ch)
    sql = "".join(out)

    # tipos e chaves
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)
    # SQLite usa TEXT para datas; Postgres aceita TEXT também, então mantém.

    return sql


# ── Wrappers que imitam a API do sqlite3 sobre o psycopg ──────────────────────
class _CursorWrapper:
    """Cursor que traduz o SQL antes de executar (para Postgres)."""
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=None):
        sql = _traduzir_sql(sql)
        try:
            if params is None:
                self._cur.execute(sql)
            else:
                self._cur.execute(sql, params)
        except Exception:
            # numa conexão persistente, um erro aborta a transação inteira e
            # trava as próximas queries. Faz rollback para liberar a conexão.
            try:
                self._cur.connection.rollback()
            except Exception:
                pass
            raise
        return self  # sqlite3 permite cur.execute(...).fetchone(); imitamos isso

    def executemany(self, sql, seq):
        sql = _traduzir_sql(sql)
        self._cur.executemany(sql, seq)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _ConnWrapper:
    """Conexão que devolve cursores traduzidos e imita sqlite3.Connection."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _CursorWrapper(self._conn.cursor())

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


# ── Exceção de "coluna/tabela já existe" unificada ────────────────────────────
def erro_operacional():
    """
    Retorna a classe de exceção equivalente ao sqlite3.OperationalError,
    para os try/except de migração de colunas funcionarem nos dois bancos.
    """
    if usando_postgres():
        import psycopg2
        return psycopg2.errors.DatabaseError
    import sqlite3
    return sqlite3.OperationalError


def adicionar_coluna(conn, tabela, coluna, tipo):
    """
    Adiciona uma coluna se ela ainda não existir, de forma segura nos dois
    bancos. No Postgres usa IF NOT EXISTS (não aborta a transação); no SQLite
    tenta e ignora o erro de coluna duplicada.
    """
    cur = conn.cursor()
    if usando_postgres():
        # traduz REAL -> DOUBLE PRECISION etc. via _traduzir_sql
        cur.execute(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo}")
    else:
        import sqlite3
        try:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        except sqlite3.OperationalError:
            pass  # já existe


# ── Leitura para DataFrame (traduz placeholders) ──────────────────────────────
def ler_df(sql, conn, params=None):
    """
    Lê um SELECT para DataFrame funcionando nos dois bancos.
    No Postgres, usa um cursor de tuplas próprio (o RealDictCursor confunde o
    pandas), montando o DataFrame a partir das colunas retornadas.
    """
    import pandas as pd
    sql = _traduzir_sql(sql)

    if usando_postgres():
        import psycopg2.extras
        raw = getattr(conn, "_conn", conn)
        # cursor de tuplas explícito (evita o RealDictCursor herdado da conexão)
        cur = raw.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute(sql, params if params is not None else None)
            cols = [d[0] for d in cur.description] if cur.description else []
            linhas = [list(r) for r in cur.fetchall()]
        except Exception:
            try:
                raw.rollback()
            except Exception:
                pass
            raise
        finally:
            cur.close()
        return pd.DataFrame(linhas, columns=cols)

    # SQLite: pandas lê direto da conexão
    if params is None:
        return pd.read_sql_query(sql, conn)
    return pd.read_sql_query(sql, conn, params=params)


# ── Fábrica de conexão ────────────────────────────────────────────────────────
def get_connection():
    """
    Devolve uma conexão pronta para uso.

    Abre uma conexão por chamada. Tentamos reaproveitar uma conexão única
    (cache_resource), mas isso trava sob concorrência no Streamlit Cloud
    (várias sessões dividindo a mesma conexão), então voltamos ao modelo
    seguro: conexão nova por operação, fechada logo em seguida.
    """
    url = _postgres_url()
    if url:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            url,
            cursor_factory=psycopg2.extras.DictCursor,
            connect_timeout=10,
        )
        conn.autocommit = False
        return _ConnWrapper(conn)

    # fallback SQLite
    import sqlite3
    from config import DATABASE
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
