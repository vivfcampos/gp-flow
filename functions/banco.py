"""
Camada de acesso ao banco de dados SQLite do GP Flow (v0.5.0).

Arquitetura (conforme especificação v0.5):
- Cada demanda existe UMA vez em `demandas`. Não há tabela separada de
  "itens de sprint" — a própria demanda carrega sprint_id, status_kanban,
  tipo_entrada, responsável da sprint e impedimento. Isso garante que
  Backlog, Planning, Sprint, Daily, Kanban e Histórico leem sempre o
  mesmo registro (sem duplicidade, sem inconsistência entre telas).
- `demanda_historico` guarda cada período que uma demanda passou em um
  status/sprint — é a base das métricas (tempo por estado, lead time,
  recorrência) e do que aparece no Histórico/Relatórios.
- `atividades_internas` guarda itens da sprint sem Id do Trace (cerimônias,
  feriados, reuniões) — não existem no Backlog, então não têm "para onde
  voltar" quando a sprint encerra.
- Existe no máximo UMA sprint com status "Em andamento" por vez.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE
from functions.util import agora_br
from functions.db import get_connection, erro_operacional, usando_postgres, ler_df, adicionar_coluna

import pandas as pd

ESTADOS_KANBAN = ["Sprint", "Em andamento", "Pendente Solic./Forn.", "Homologação", "Concluído"]
TIPOS_ENTRADA = ["Planejada", "Paraquedas", "Interna"]


# get_connection é fornecido por functions.db (SQLite local ou Postgres/Neon)


# ===========================================================================
# CRIAÇÃO / MIGRAÇÃO DE TABELAS
# ===========================================================================
def criar_tabelas():
    """Cria as tabelas do banco caso ainda não existam. Seguro de rodar várias vezes.

    Otimização: roda só uma vez por sessão do Streamlit (as tabelas não mudam
    durante o uso). Isso evita repetir CREATE/ALTER a cada carregamento de página,
    que era lento com o banco remoto.
    """
    try:
        import streamlit as st
        if st.session_state.get("_tabelas_ok"):
            return
    except Exception:
        st = None

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS demandas (
            id INTEGER PRIMARY KEY,
            titulo TEXT NOT NULL,
            solicitante TEXT,
            tipo TEXT,
            data_criacao TEXT,
            estado TEXT,                       -- Estado vindo do Trace (não confundir com status_kanban)
            destino TEXT,
            prioridade TEXT,
            prioridade_atendimento TEXT,
            aging_trace INTEGER,
            responsavel_atendimento TEXT,
            urgencia_importancia INTEGER,

            -- Curadoria (preenchidos manualmente, a importação NUNCA sobrescreve)
            macroprocesso TEXT,
            sistema TEXT,
            score REAL,
            score_sugerido REAL,
            score_ajustado_manualmente INTEGER DEFAULT 0,
            observacoes TEXT,

            -- Sprint (preenchidos manualmente, a importação NUNCA sobrescreve)
            sprint_id INTEGER,                 -- NULL = está no Backlog
            status_kanban TEXT,                -- Sprint / Em andamento / Homologação / Concluído
            tipo_entrada TEXT,                 -- Planejada / Paraquedas
            responsavel_sprint TEXT,
            impedimento TEXT,
            data_entrada_sprint TEXT,

            data_importacao TEXT,
            data_atualizacao TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS importacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo TEXT,
            total_linhas INTEGER,
            novas INTEGER,
            atualizadas INTEGER,
            ignoradas INTEGER DEFAULT 0,
            data_hora TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_inicio TEXT,
            data_fim TEXT,
            status TEXT DEFAULT 'Planejamento',   -- 'Planejamento' -> 'Em andamento' -> 'Encerrada'
            criada_em TEXT,
            encerrada_em TEXT,
            meta TEXT,
            retro_bem TEXT,
            retro_dificultou TEXT,
            retro_acoes TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS atividades_internas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sprint_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            responsavel_sprint TEXT,
            horas_minutos INTEGER DEFAULT 0,
            status_kanban TEXT DEFAULT 'Sprint',
            tipo_entrada TEXT DEFAULT 'Planejada',
            impedimento TEXT,
            ordem INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS demanda_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demanda_id INTEGER NOT NULL,
            sprint_id INTEGER,
            status_kanban TEXT,
            data_inicio TEXT,
            data_fim TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sprint_fechamento_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sprint_id INTEGER NOT NULL,
            demanda_id INTEGER,
            titulo TEXT,
            tipo_entrada TEXT,
            status_final TEXT
        )
    """)

    conn.commit()
    conn.close()
    _migrar_colunas()

    try:
        import streamlit as st
        st.session_state["_tabelas_ok"] = True
    except Exception:
        pass


def _migrar_colunas():
    """Migração leve para bancos de versões anteriores (adiciona colunas novas sem apagar dados)."""
    conn = get_connection()
    cur = conn.cursor()
    colunas_novas = [
        ("score_sugerido", "REAL"),
        ("score_ajustado_manualmente", "INTEGER DEFAULT 0"),
        ("sprint_id", "INTEGER"),
        ("status_kanban", "TEXT"),
        ("tipo_entrada", "TEXT"),
        ("responsavel_sprint", "TEXT"),
        ("impedimento", "TEXT"),
        ("data_entrada_sprint", "TEXT"),
        ("prioridade_atendimento", "TEXT"),
        ("aging_trace", "INTEGER"),
        ("horas_trabalhadas", "REAL DEFAULT 0"),
        ("descricao_interna", "TEXT"),
    ]
    for coluna, tipo in colunas_novas:
        adicionar_coluna(conn, "demandas", coluna, tipo)

    adicionar_coluna(conn, "importacoes", "ignoradas", "INTEGER DEFAULT 0")
    adicionar_coluna(conn, "sprints", "status", "TEXT DEFAULT 'Em andamento'")
    for coluna in ("encerrada_em", "retro_bem", "retro_dificultou", "retro_acoes", "meta"):
        adicionar_coluna(conn, "sprints", coluna, "TEXT")

    conn.commit()
    conn.close()


def _valor_sqlite(valor):
    """Converte NaN/pd.NA/numpy para tipos aceitos pelo sqlite3."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(valor, "item"):
        return valor.item()
    return valor


# ===========================================================================
# IMPORTAÇÃO (nunca sobrescreve campos gerenciados no GP Flow)
# ===========================================================================
CAMPOS_TRACE = [
    "titulo", "solicitante", "tipo", "data_criacao", "estado",
    "destino", "prioridade", "prioridade_atendimento", "aging_trace",
    "responsavel_atendimento", "urgencia_importancia",
]


def upsert_demandas(df: pd.DataFrame):
    """
    Sincroniza demandas vindas do Trace.
    - Demanda existente: atualiza SOMENTE os campos do Trace. Nunca toca em
      macroprocesso/sistema/score/observações/sprint/status/tipo de
      entrada/impedimento/responsável da sprint (curadoria e gestão da
      sprint são exclusivas do GP Flow).
    - Demanda nova: cria e entra no Backlog (sprint_id NULL). Nunca é
      adicionada à sprint automaticamente.
    - "Ignorada": demanda já existia e nenhum campo do Trace mudou.
    Retorna (novas, atualizadas, ignoradas).
    """
    conn = get_connection()
    cur = conn.cursor()

    existentes = {row["id"]: dict(row) for row in cur.execute("SELECT * FROM demandas")}

    novas = atualizadas = ignoradas = 0
    agora = agora_br()

    for _, row in df.iterrows():
        demanda_id = int(row["id"])
        valores_trace = {campo: _valor_sqlite(row[campo]) for campo in CAMPOS_TRACE}

        if demanda_id in existentes:
            atual = existentes[demanda_id]
            mudou = any(valores_trace[c] != atual.get(c) for c in CAMPOS_TRACE)
            if not mudou:
                ignoradas += 1
                continue

            cur.execute("""
                UPDATE demandas SET
                    titulo = ?, solicitante = ?, tipo = ?, data_criacao = ?,
                    estado = ?, destino = ?, prioridade = ?, prioridade_atendimento = ?,
                    aging_trace = ?, responsavel_atendimento = ?, urgencia_importancia = ?,
                    data_atualizacao = ?
                WHERE id = ?
            """, (*valores_trace.values(), agora, demanda_id))
            atualizadas += 1
        else:
            cur.execute("""
                INSERT INTO demandas (
                    id, titulo, solicitante, tipo, data_criacao, estado,
                    destino, prioridade, prioridade_atendimento, aging_trace,
                    responsavel_atendimento, urgencia_importancia,
                    data_importacao, data_atualizacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (demanda_id, *valores_trace.values(), agora, agora))
            novas += 1

    conn.commit()
    conn.close()
    return novas, atualizadas, ignoradas


def registrar_importacao(arquivo: str, total: int, novas: int, atualizadas: int, ignoradas: int = 0):
    conn = get_connection()
    conn.execute("""
        INSERT INTO importacoes (arquivo, total_linhas, novas, atualizadas, ignoradas, data_hora)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (arquivo, total, novas, atualizadas, ignoradas, agora_br()))
    conn.commit()
    conn.close()


def ultima_importacao():
    conn = get_connection()
    row = conn.execute("SELECT * FROM importacoes ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


# ===========================================================================
# CONSULTAS GERAIS DE DEMANDAS
# ===========================================================================
def listar_demandas() -> pd.DataFrame:
    conn = get_connection()
    df = ler_df("SELECT * FROM demandas", conn)
    conn.close()
    return df


def listar_backlog() -> pd.DataFrame:
    """
    Demandas que não estão em nenhuma sprint (sprint_id nulo) e que não
    foram concluídas avulsas (concluídas direto da Curadoria/Backlog, sem
    passar por sprint — ex.: resolvidas no próprio Trace).
    """
    conn = get_connection()
    df = ler_df(
        "SELECT * FROM demandas WHERE sprint_id IS NULL "
        "AND (status_kanban IS NULL OR status_kanban != 'Concluído')",
        conn,
    )
    conn.close()
    return df


def contar_backlog() -> int:
    """Quantidade de demandas atualmente no Backlog (mesmo critério de listar_backlog)."""
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) FROM demandas WHERE sprint_id IS NULL "
        "AND (status_kanban IS NULL OR status_kanban != 'Concluído')"
    ).fetchone()[0]
    conn.close()
    return int(n)


def limpar_backlog() -> int:
    """
    Apaga APENAS as demandas que estão no Backlog — mesmo critério de
    listar_backlog(): sprint_id nulo e não concluídas avulsas.

    NÃO toca em demandas que estão em sprint, congeladas em sprints
    encerradas ou concluídas avulsas. Remove também os históricos e itens
    de fechamento ligados exclusivamente a essas demandas, para não deixar
    registros órfãos. Retorna quantas demandas foram removidas.
    """
    conn = get_connection()
    cur = conn.cursor()
    if not usando_postgres():
        cur.execute("PRAGMA foreign_keys = ON")

    ids = [
        r[0]
        for r in cur.execute(
            "SELECT id FROM demandas WHERE sprint_id IS NULL "
            "AND (status_kanban IS NULL OR status_kanban != 'Concluído')"
        ).fetchall()
    ]

    if ids:
        marcadores = ",".join("?" * len(ids))
        cur.execute(
            f"DELETE FROM demanda_historico WHERE demanda_id IN ({marcadores})", ids
        )
        cur.execute(
            f"DELETE FROM sprint_fechamento_itens WHERE demanda_id IN ({marcadores})", ids
        )
        cur.execute(f"DELETE FROM demandas WHERE id IN ({marcadores})", ids)
        conn.commit()

    conn.close()
    return len(ids)


def excluir_demandas(ids: list) -> dict:
    """
    Apaga do banco as demandas cujos Ids forem passados, mas SOMENTE as que
    não têm NENHUM vínculo. Uma demanda é considerada sem vínculo quando:
      - sprint_id IS NULL (não está em nenhuma sprint), E
      - não tem registro em demanda_historico (nunca passou por sprint), E
      - não tem registro em sprint_fechamento_itens (não foi congelada em
        sprint encerrada).

    Qualquer demanda com vínculo é BLOQUEADA (não é apagada). Isso protege o
    histórico: nada que já participou de uma sprint pode ser deletado pela
    tela de Backlog.

    Retorna um dict:
      {"apagadas": int, "bloqueadas": [ids...], "inexistentes": [ids...]}
    """
    ids = [int(i) for i in ids if i is not None]
    resultado = {"apagadas": 0, "bloqueadas": [], "inexistentes": []}
    if not ids:
        return resultado

    conn = get_connection()
    cur = conn.cursor()
    if not usando_postgres():
        cur.execute("PRAGMA foreign_keys = ON")

    marcadores = ",".join("?" * len(ids))
    existentes = {r[0] for r in cur.execute(
        f"SELECT id FROM demandas WHERE id IN ({marcadores})", ids
    ).fetchall()}
    resultado["inexistentes"] = [i for i in ids if i not in existentes]

    # sem vínculo: sprint_id nulo, e sem linhas em historico/fechamento
    sem_vinculo = {r[0] for r in cur.execute(
        f"""
        SELECT d.id FROM demandas d
        WHERE d.id IN ({marcadores})
          AND d.sprint_id IS NULL
          AND NOT EXISTS (SELECT 1 FROM demanda_historico h WHERE h.demanda_id = d.id)
          AND NOT EXISTS (SELECT 1 FROM sprint_fechamento_itens f WHERE f.demanda_id = d.id)
        """,
        ids,
    ).fetchall()}

    resultado["bloqueadas"] = [i for i in existentes if i not in sem_vinculo]

    if sem_vinculo:
        elegiveis = list(sem_vinculo)
        m2 = ",".join("?" * len(elegiveis))
        cur.execute(f"DELETE FROM demandas WHERE id IN ({m2})", elegiveis)
        conn.commit()
        resultado["apagadas"] = len(elegiveis)

    conn.close()
    return resultado


def listar_concluidas_avulsas() -> pd.DataFrame:
    """Demandas concluídas fora de qualquer sprint (usadas no painel de consistência)."""
    conn = get_connection()
    df = ler_df(
        "SELECT * FROM demandas WHERE sprint_id IS NULL AND status_kanban = 'Concluído'",
        conn,
    )
    conn.close()
    return df


def concluir_demanda(demanda_id: int):
    """
    Conclui a demanda de onde quer que ela esteja — como todas as telas leem
    o mesmo registro, a conclusão reflete em Backlog, Curadoria, Sprint,
    Daily e Kanban ao mesmo tempo.
    - Na sprint ativa: vira 'Concluído' no Kanban normalmente.
    - Fora de sprint: vira uma conclusão avulsa (sai do Backlog).
    """
    atualizar_status_kanban(demanda_id, "Concluído")


def buscar_demanda(demanda_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM demandas WHERE id = ?", (int(demanda_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def atualizar_curadoria(demanda_id: int, macroprocesso: str, sistema: str,
                        score_final, score_sugerido, observacoes: str = None):
    """Curadoria: só classifica (macroprocesso/sistema/score/observações). Não mexe em sprint/status."""
    ajustado = 1 if (score_final is not None and score_sugerido is not None
                    and round(float(score_final), 1) != round(float(score_sugerido), 1)) else 0
    conn = get_connection()
    conn.execute("""
        UPDATE demandas SET
            macroprocesso = ?, sistema = ?, score = ?, score_sugerido = ?,
            score_ajustado_manualmente = ?, observacoes = ?, data_atualizacao = ?
        WHERE id = ?
    """, (macroprocesso, sistema, score_final, score_sugerido, ajustado,
          observacoes, agora_br(), demanda_id))
    conn.commit()
    conn.close()


# ===========================================================================
# HISTÓRICO DE STATUS (base das métricas + relatórios)
# ===========================================================================
def _abrir_historico(cur, demanda_id: int, sprint_id, status_kanban: str, agora: str):
    cur.execute(
        "UPDATE demanda_historico SET data_fim = ? "
        "WHERE demanda_id = ? AND data_fim IS NULL",
        (agora, demanda_id),
    )
    cur.execute(
        "INSERT INTO demanda_historico (demanda_id, sprint_id, status_kanban, data_inicio) "
        "VALUES (?, ?, ?, ?)",
        (demanda_id, sprint_id, status_kanban, agora),
    )


# ===========================================================================
# SPRINT — estados: 'Planejamento' -> 'Em andamento' -> 'Encerrada'
# (só uma sprint "ativa" por vez, ou seja, não-encerrada)
# ===========================================================================
def sprint_ativa():
    """Retorna a sprint atual (em Planejamento OU Em andamento). Só há uma por vez."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sprints WHERE status != 'Encerrada' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def sprint_em_andamento(sprint: dict = None) -> bool:
    """True se a sprint já foi iniciada (status 'Em andamento'). Em 'Planejamento' retorna False."""
    if sprint is None:
        sprint = sprint_ativa()
    return bool(sprint) and sprint.get("status") == "Em andamento"


def listar_sprints() -> pd.DataFrame:
    conn = get_connection()
    df = ler_df("SELECT * FROM sprints ORDER BY id DESC", conn)
    conn.close()
    return df


def criar_sprint(nome: str, data_inicio: str = None, data_fim: str = None, meta: str = None) -> int:
    """
    Cria uma sprint nova em estado 'Planejamento' (ainda não iniciada).
    Bloqueia se já existir uma sprint ativa (em Planejamento ou Em andamento).
    """
    if sprint_ativa():
        raise ValueError("Já existe uma sprint ativa. Encerre-a antes de criar uma nova.")
    conn = get_connection()
    if usando_postgres():
        cur = conn.execute(
            "INSERT INTO sprints (nome, data_inicio, data_fim, status, criada_em, meta) "
            "VALUES (?, ?, ?, 'Planejamento', ?, ?) RETURNING id",
            (nome, data_inicio, data_fim, agora_br(), (meta or None)),
        )
        sprint_id = cur.fetchone()["id"]
    else:
        cur = conn.execute(
            "INSERT INTO sprints (nome, data_inicio, data_fim, status, criada_em, meta) "
            "VALUES (?, ?, ?, 'Planejamento', ?, ?)",
            (nome, data_inicio, data_fim, agora_br(), (meta or None)),
        )
        sprint_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sprint_id


def atualizar_meta_sprint(sprint_id: int, meta: str):
    """Atualiza a meta (objetivo) da sprint."""
    conn = get_connection()
    conn.execute("UPDATE sprints SET meta = ? WHERE id = ?", ((meta or None), sprint_id))
    conn.commit()
    conn.close()


def velocidade_media(ultimas: int = 3) -> float:
    """
    Velocidade histórica: média de demandas CONCLUÍDAS por sprint encerrada,
    considerando as `ultimas` sprints encerradas. Retorna 0.0 se não houver
    histórico suficiente. Serve para orientar quantas demandas puxar.
    """
    conn = get_connection()
    encerradas = ler_df(
        "SELECT id FROM sprints WHERE status = 'Encerrada' ORDER BY id DESC LIMIT ?",
        conn, params=(ultimas,),
    )
    if encerradas.empty:
        conn.close()
        return 0.0
    ids = tuple(int(i) for i in encerradas["id"])
    marcadores = ",".join("?" * len(ids))
    fech = ler_df(
        f"SELECT sprint_id, status_final FROM sprint_fechamento_itens "
        f"WHERE sprint_id IN ({marcadores})",
        conn, params=ids,
    )
    conn.close()
    if fech.empty:
        return 0.0
    concluidas = fech[fech["status_final"] == "Concluído"]
    return round(len(concluidas) / len(ids), 1)


def iniciar_sprint(sprint_id: int):
    """
    Marca a sprint como 'Em andamento'. A partir daqui, demandas adicionadas
    entram como Paraquedas por padrão (furaram o planejamento).
    """
    conn = get_connection()
    conn.execute(
        "UPDATE sprints SET status = 'Em andamento' WHERE id = ?", (sprint_id,)
    )
    conn.commit()
    conn.close()


def encerrar_sprint(sprint_id: int, retro_bem: str, retro_dificultou: str, retro_acoes: str) -> dict:
    """
    Encerra a sprint: fica somente leitura. Demandas concluídas ficam
    associadas para sempre a essa sprint (histórico). Demandas pendentes
    voltam ao Backlog (sprint_id limpo) para serem replanejadas.
    Retorna um resumo com as contagens finais.
    """
    conn = get_connection()
    cur = conn.cursor()
    agora = agora_br()

    itens = ler_df(
        "SELECT * FROM demandas WHERE sprint_id = ?", conn, params=(sprint_id,)
    )
    resumo = {
        "planejadas": int((itens["tipo_entrada"] == "Planejada").sum()),
        "paraquedas": int((itens["tipo_entrada"] == "Paraquedas").sum()),
        "internas": int((itens["tipo_entrada"] == "Interna").sum()),
        "concluidas": int((itens["status_kanban"] == "Concluído").sum()),
        "pendentes": int((itens["status_kanban"] != "Concluído").sum()),
    }

    for _, item in itens.iterrows():
        cur.execute("""
            INSERT INTO sprint_fechamento_itens (sprint_id, demanda_id, titulo, tipo_entrada, status_final)
            VALUES (?, ?, ?, ?, ?)
        """, (sprint_id, int(item["id"]), item["titulo"], item["tipo_entrada"], item["status_kanban"]))

        if item["status_kanban"] != "Concluído":
            # pendente: volta pro backlog
            cur.execute("""
                UPDATE demandas SET
                    sprint_id = NULL, status_kanban = NULL, tipo_entrada = NULL,
                    responsavel_sprint = NULL, impedimento = NULL, data_entrada_sprint = NULL
                WHERE id = ?
            """, (int(item["id"]),))
            cur.execute(
                "UPDATE demanda_historico SET data_fim = ? WHERE demanda_id = ? AND data_fim IS NULL",
                (agora, int(item["id"])),
            )
        # concluída: fica congelada, associada a esta sprint (não mexe)

    cur.execute("""
        UPDATE sprints SET
            status = 'Encerrada', encerrada_em = ?,
            retro_bem = ?, retro_dificultou = ?, retro_acoes = ?
        WHERE id = ?
    """, (agora, retro_bem, retro_dificultou, retro_acoes, sprint_id))

    conn.commit()
    conn.close()
    return resumo


# ---------------------------------------------------------------------------
# Planning: adicionar/remover demandas da sprint ativa
# ---------------------------------------------------------------------------
def adicionar_demanda_a_sprint(demanda_id: int, sprint_id: int, tipo_entrada: str,
                               responsavel_sprint: str = ""):
    agora = agora_br()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE demandas SET
            sprint_id = ?, status_kanban = 'Sprint', tipo_entrada = ?,
            responsavel_sprint = ?, data_entrada_sprint = ?
        WHERE id = ?
    """, (sprint_id, tipo_entrada, responsavel_sprint, agora, demanda_id))
    _abrir_historico(cur, demanda_id, sprint_id, "Sprint", agora)
    conn.commit()
    conn.close()


def remover_demanda_da_sprint(demanda_id: int):
    """Remove da sprint — a demanda NUNCA é excluída, apenas volta pro Backlog."""
    agora = agora_br()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE demandas SET
            sprint_id = NULL, status_kanban = NULL, tipo_entrada = NULL,
            responsavel_sprint = NULL, impedimento = NULL, data_entrada_sprint = NULL
        WHERE id = ?
    """, (demanda_id,))
    cur.execute(
        "UPDATE demanda_historico SET data_fim = ? WHERE demanda_id = ? AND data_fim IS NULL",
        (agora, demanda_id),
    )
    conn.commit()
    conn.close()


def atualizar_status_kanban(demanda_id: int, novo_status: str):
    agora = agora_br()
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT sprint_id FROM demandas WHERE id = ?", (demanda_id,)).fetchone()
    sprint_id = row["sprint_id"] if row else None
    cur.execute("UPDATE demandas SET status_kanban = ? WHERE id = ?", (novo_status, demanda_id))
    _abrir_historico(cur, demanda_id, sprint_id, novo_status, agora)
    conn.commit()
    conn.close()


def atualizar_tipo_entrada(demanda_id: int, tipo_entrada: str):
    conn = get_connection()
    conn.execute("UPDATE demandas SET tipo_entrada = ? WHERE id = ?", (tipo_entrada, demanda_id))
    conn.commit()
    conn.close()


def atualizar_responsavel_sprint(demanda_id: int, responsavel: str):
    conn = get_connection()
    conn.execute("UPDATE demandas SET responsavel_sprint = ? WHERE id = ?", (responsavel, demanda_id))
    conn.commit()
    conn.close()


def atualizar_impedimento(demanda_id: int, impedimento: str):
    conn = get_connection()
    conn.execute("UPDATE demandas SET impedimento = ? WHERE id = ?", (impedimento, demanda_id))
    conn.commit()
    conn.close()


def atualizar_card_kanban(demanda_id: int, *, responsavel_sprint: str = None,
                          status_kanban: str = None, tipo_entrada: str = None,
                          impedimento: str = None, observacoes: str = None,
                          horas_trabalhadas: float = None, descricao_interna: str = None):
    """Atualiza os campos editáveis do card do Kanban."""
    conn = get_connection()
    campos = []
    valores = []
    mapa = {
        "responsavel_sprint":  responsavel_sprint,
        "status_kanban":       status_kanban,
        "tipo_entrada":        tipo_entrada,
        "impedimento":         impedimento,
        "observacoes":         observacoes,
        "horas_trabalhadas":   horas_trabalhadas,
        "descricao_interna":   descricao_interna,
    }
    for campo, valor in mapa.items():
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)
    if not campos:
        conn.close()
        return
    campos.append("data_atualizacao = ?")
    valores.append(str(agora_br()))
    valores.append(demanda_id)
    conn.execute(f"UPDATE demandas SET {', '.join(campos)} WHERE id = ?", valores)
    conn.commit()
    conn.close()


def listar_demandas_sprint(sprint_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = ler_df(
        "SELECT * FROM demandas WHERE sprint_id = ? ORDER BY responsavel_sprint, id", conn, params=(sprint_id,)
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Atividades internas (sem Id do Trace: cerimônias, feriados, reuniões...)
# ---------------------------------------------------------------------------
def adicionar_atividade_interna(sprint_id: int, titulo: str, responsavel_sprint: str = "",
                                horas_minutos: int = 0, tipo_entrada: str = "Planejada"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO atividades_internas
            (sprint_id, titulo, responsavel_sprint, horas_minutos, status_kanban, tipo_entrada)
        VALUES (?, ?, ?, ?, 'Sprint', ?)
    """, (sprint_id, titulo, responsavel_sprint, horas_minutos, tipo_entrada))
    conn.commit()
    conn.close()


def listar_atividades_sprint(sprint_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = ler_df(
        "SELECT * FROM atividades_internas WHERE sprint_id = ? ORDER BY responsavel_sprint, id",
        conn, params=(sprint_id,),
    )
    conn.close()
    return df


def atualizar_atividade_interna(atividade_id: int, **campos):
    if not campos:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{c} = ?" for c in campos)
    conn.execute(
        f"UPDATE atividades_internas SET {set_clause} WHERE id = ?",
        (*campos.values(), atividade_id),
    )
    conn.commit()
    conn.close()


def remover_atividade_interna(atividade_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM atividades_internas WHERE id = ?", (atividade_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Recorrência (quantas sprints diferentes essa demanda já passou)
# ---------------------------------------------------------------------------
def contagem_sprints_por_demanda(demanda_id: int) -> int:
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(DISTINCT sprint_id) FROM demanda_historico "
        "WHERE demanda_id = ? AND sprint_id IS NOT NULL",
        (demanda_id,),
    ).fetchone()[0]
    conn.close()
    return n


def itens_fechamento_sprint(sprint_id: int) -> pd.DataFrame:
    """Foto dos itens da sprint no momento do encerramento (usada no Histórico/Relatórios)."""
    conn = get_connection()
    df = ler_df(
        "SELECT * FROM sprint_fechamento_itens WHERE sprint_id = ?", conn, params=(sprint_id,)
    )
    conn.close()
    return df


def listar_sprints_encerradas() -> pd.DataFrame:
    conn = get_connection()
    df = ler_df(
        "SELECT * FROM sprints WHERE status = 'Encerrada' ORDER BY id DESC", conn
    )
    conn.close()
    return df


def excluir_sprint(sprint_id: int):
    """
    Exclui o "bloco" da sprint (ativa ou já encerrada) sem gerar
    inconsistência: as demandas NUNCA são excluídas — voltam para o
    Backlog com a curadoria intacta (macroprocesso/sistema/score/
    observações preservados). Atividades internas dessa sprint são
    removidas (não têm Id do Trace, não têm "para onde voltar"). O
    histórico e o snapshot de fechamento dessa sprint também são
    removidos, já que a sprint deixa de existir por completo.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandas SET
            sprint_id = NULL, status_kanban = NULL, tipo_entrada = NULL,
            responsavel_sprint = NULL, impedimento = NULL, data_entrada_sprint = NULL
        WHERE sprint_id = ?
    """, (sprint_id,))

    cur.execute("DELETE FROM atividades_internas WHERE sprint_id = ?", (sprint_id,))
    cur.execute("DELETE FROM demanda_historico WHERE sprint_id = ?", (sprint_id,))
    cur.execute("DELETE FROM sprint_fechamento_itens WHERE sprint_id = ?", (sprint_id,))
    cur.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))

    conn.commit()
    conn.close()
