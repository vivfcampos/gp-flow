"""
Camada unificada de acesso ao banco — GP Flow.

Objetivo: o resto do código (banco.py, metricas.py, etc.) continua escrito
como se estivesse falando com SQLite (placeholders "?", sqlite3.Row,
pd.read_sql_query). Esta camada detecta se há um PostgreSQL configurado
(Neon, Supabase, etc.) e, se houver, traduz tudo por baixo dos panos —
sem precisar reescrever cada query do projeto.

Como escolhe o banco:
- Se existir st.secrets["postgres"]["url"] (Streamlit Cloud) OU a variável
  de ambiente DATABASE_URL, usa PostgreSQL.
- Caso contrário, usa o SQLite local em data/gpflow.db (comportamento
  original, sem nenhuma mudança).
"""
import os
import re
import sqlite3

import pandas as pd

try:
    import streamlit as st
except ImportError:
    st = None

_PG_DISPONIVEL = True
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
except ImportError:
    _PG_DISPONIVEL = False


# ===========================================================================
# Detecção de qual banco usar
# ===========================================================================
def _url_postgres():
    """Procura a connection string do Postgres nos secrets do Streamlit ou em variável de ambiente."""
    if st is not None:
        try:
            if "postgres" in st.secrets and st.secrets["postgres"].get("url"):
                return st.secrets["postgres"]["url"]
        except Exception:
            pass
    return os.environ.get("DATABASE_URL")


def eh_postgres() -> bool:
    """True se há um PostgreSQL configurado e a biblioteca psycopg2 disponível."""
    return _PG_DISPONIVEL and bool(_url_postgres())


# ===========================================================================
# Tradução de SQL: SQLite -> PostgreSQL
# ===========================================================================
_RE_AUTOINCREMENT = re.compile(r"\bINTEGER PRIMARY KEY AUTOINCREMENT\b", re.IGNORECASE)
_RE_REAL = re.compile(r"\bREAL\b", re.IGNORECASE)
_RE_INSERT = re.compile(r"^\s*INSERT INTO", re.IGNORECASE)


def _traduzir_sql(sql: str) -> str:
    """Traduz uma query escrita para SQLite para a sintaxe equivalente em PostgreSQL."""
    s = sql
    if s.strip().upper().startswith("PRAGMA"):
        # PRAGMA (ex.: foreign_keys = ON) não existe no Postgres e não é necessário lá
        # (chaves estrangeiras já são sempre aplicadas). Vira um no-op inofensivo.
        return "SELECT 1"
    s = _RE_AUTOINCREMENT.sub("SERIAL PRIMARY KEY", s)
    s = _RE_REAL.sub("DOUBLE PRECISION", s)
    s = s.replace("?", "%s")
    return s


# ===========================================================================
# Wrappers: fazem uma conexão/cursor psycopg2 se comportar como sqlite3
# ===========================================================================
class _CursorWrapper:
    """Encapsula um cursor psycopg2 para aceitar SQL/placeholders no estilo SQLite."""

    def __init__(self, cursor):
        self._cur = cursor
        self.lastrowid = None

    def execute(self, sql, params=()):
        traduzido = _traduzir_sql(sql)
        self.lastrowid = None
        # Toda tabela do GP Flow tem coluna "id". Para INSERTs, pedimos o id
        # de volta automaticamente — assim cur.lastrowid funciona igual ao
        # SQLite, sem precisar mudar cada ponto do código que insere linhas.
        if _RE_INSERT.match(traduzido) and "RETURNING" not in traduzido.upper():
            comando = traduzido.rstrip().rstrip(";") + " RETURNING id"
            self._cur.execute(comando, params)
            try:
                linha = self._cur.fetchone()
                if linha is not None:
                    self.lastrowid = linha[0]
            except Exception:
                pass
        else:
            self._cur.execute(traduzido, params)
        return self

    def executemany(self, sql, seq_params):
        self._cur.executemany(_traduzir_sql(sql), seq_params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)

    def __getattr__(self, nome):
        return getattr(self._cur, nome)


class _ConnWrapper:
    """Encapsula uma conexão psycopg2 para se comportar como uma conexão sqlite3."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _CursorWrapper(self._conn.cursor())

    def execute(self, sql, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __getattr__(self, nome):
        return getattr(self._conn, nome)


# ===========================================================================
# Conexão
# ===========================================================================
def get_connection():
    """Retorna uma conexão: PostgreSQL (produção) se configurado, senão SQLite local (padrão)."""
    if eh_postgres():
        conn = psycopg2.connect(_url_postgres(), cursor_factory=psycopg2.extras.DictCursor)
        return _ConnWrapper(conn)
    from config import DATABASE
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
# Migração de colunas segura nos dois bancos
# ===========================================================================
def adicionar_coluna_segura(conn, tabela: str, coluna: str, tipo: str):
    """
    Adiciona uma coluna à tabela se ela ainda não existir.
    No Postgres usa ADD COLUMN IF NOT EXISTS (atômico — não aborta a transação
    caso a coluna já exista). No SQLite (que não suporta IF NOT EXISTS em
    ADD COLUMN) usa try/except, como antes.
    """
    cur = conn.cursor()
    if eh_postgres():
        tipo_pg = _RE_REAL.sub("DOUBLE PRECISION", tipo)
        cur.execute(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo_pg}")
    else:
        try:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        except sqlite3.OperationalError:
            pass


# ===========================================================================
# Leitura de DataFrame (substitui pd.read_sql_query nos dois bancos)
# ===========================================================================
def ler_df(sql: str, conn, params=None) -> pd.DataFrame:
    """Equivalente a pd.read_sql_query, funcionando igual em SQLite e em Postgres."""
    if not eh_postgres():
        return pd.read_sql_query(sql, conn, params=params)

    traduzido = _traduzir_sql(sql)
    # Cursor "cru" (tuplas), não o DictCursor da conexão — combinar DictCursor
    # com pandas faz cada linha virar {"coluna": "coluna"} em vez do valor real.
    cur = conn._conn.cursor(cursor_factory=psycopg2.extensions.cursor)
    try:
        cur.execute(traduzido, params or ())
        colunas = [d[0] for d in cur.description]
        linhas = cur.fetchall()
        return pd.DataFrame(linhas, columns=colunas)
    finally:
        cur.close()
