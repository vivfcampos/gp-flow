"""
importar_sprint_antiga.py — GP Flow

Script AVULSO para carregar uma sprint já concluída direto no histórico,
sem mexer em nenhuma tela do programa. Rode uma vez por sprint antiga.

O que ele faz:
  1. Lê a planilha da sprint (modelo Id | Título | Horas | Responsável | Estado | Observações).
  2. Cria a sprint já ENCERRADA no banco (aparece no Histórico).
  3. As linhas COM Id viram demandas: se o Id já existe no banco, reaproveita
     o registro (não duplica); se não existe, cria a demanda.
  4. As linhas SEM Id viram atividades internas da sprint (Cerimônia, feriados...).
  5. Grava o histórico de status e o snapshot de fechamento, para as demandas
     contarem nas métricas de recorrência da sprint atual e nos relatórios.
  6. NÃO altera curadoria, nem a sprint ativa, nem nada que já esteja no banco.

Como usar (dentro da pasta do projeto, com o .venv ativado):

    python3 importar_sprint_antiga.py "Sprint_22_a_03.xlsx" --nome "Sprint 22/06 a 03/07" --inicio 2026-06-22 --fim 2026-07-03

Se você não passar --nome/--inicio/--fim, o script pergunta interativamente.
Use --simular para ver o que aconteceria SEM gravar nada.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

# Garante que o script acha os módulos do projeto, rode de onde rodar
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from functions.banco import get_connection, criar_tabelas, _valor_sqlite, buscar_demanda
from functions.util import agora_br
from functions.sprint import apelido


# Estados da planilha antiga -> status do Kanban do GP Flow.
# "Concluído"/"Concluido" contam como concluído; o resto é considerado pendente.
def _status_kanban(estado_planilha: str) -> str:
    if not estado_planilha:
        return "Sprint"
    e = str(estado_planilha).strip().lower()
    if "conclu" in e:            # concluído / concluido / concluída
        return "Concluído"
    if "homolog" in e:
        return "Homologação"
    if "pendente" in e:         # pendente fornecedor / pendente solicitante
        return "Pendente Solic./Forn."
    if "andamento" in e or "atendimento" in e:
        return "Em andamento"
    return "Sprint"              # planejado etc.


def ler_planilha_sprint(caminho: str, aba: str = None) -> pd.DataFrame:
    """
    Lê a aba de demandas da planilha da sprint. Detecta a linha de cabeçalho
    (a que contém 'Id' e 'Título') automaticamente, ignorando as linhas de
    título/lembrete no topo.
    """
    xl = pd.ExcelFile(caminho)
    aba = aba or xl.sheet_names[0]  # por padrão a primeira aba (as demandas)

    bruto = pd.read_excel(caminho, sheet_name=aba, header=None)

    # acha a linha de cabeçalho procurando 'Id' + 'Título' (com ou sem acento)
    linha_cab = None
    for i in range(min(15, len(bruto))):
        valores = [str(v).strip().lower() for v in bruto.iloc[i].tolist()]
        if "id" in valores and any("tulo" in v for v in valores):
            linha_cab = i
            break
    if linha_cab is None:
        raise ValueError("Não encontrei o cabeçalho (linha com 'Id' e 'Título') na planilha.")

    df = pd.read_excel(caminho, sheet_name=aba, header=linha_cab)
    df.columns = [str(c).strip() for c in df.columns]

    # normaliza nomes de coluna esperados
    mapa = {}
    for c in df.columns:
        cl = c.lower()
        if cl == "id":
            mapa[c] = "id"
        elif "tulo" in cl:
            mapa[c] = "titulo"
        elif "hora" in cl:
            mapa[c] = "horas"
        elif "respons" in cl:
            mapa[c] = "responsavel"
        elif "estado" in cl or "status" in cl:
            mapa[c] = "estado"
        elif "observ" in cl:
            mapa[c] = "observacoes"
    df = df.rename(columns=mapa)

    # descarta linhas totalmente vazias
    df = df.dropna(how="all")
    # descarta linhas sem título (não são itens)
    df = df[df["titulo"].notna()]
    return df.reset_index(drop=True)


def importar(caminho, nome, inicio, fim, aba=None, simular=False):
    df = ler_planilha_sprint(caminho, aba)

    com_id = df[df["id"].notna()]
    sem_id = df[df["id"].isna()]

    print(f"\nPlanilha lida: {len(df)} itens ({len(com_id)} demandas com Id, {len(sem_id)} atividades internas)")
    print(f"Sprint: '{nome}'  período {inicio} a {fim}")

    agora = agora_br()
    resumo = {"demandas_reaproveitadas": 0, "demandas_criadas": 0, "atividades": 0,
              "concluidas": 0, "pendentes": 0}

    if simular:
        print("\n[SIMULAÇÃO] Nada será gravado. Prévia do que aconteceria:\n")

    conn = None if simular else get_connection()
    try:
        if not simular:
            criar_tabelas()  # garante o schema (idempotente)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sprints (nome, data_inicio, data_fim, status, criada_em, encerrada_em, "
                "retro_bem, retro_dificultou, retro_acoes) "
                "VALUES (?, ?, ?, 'Encerrada', ?, ?, ?, ?, ?)",
                (nome, str(inicio), str(fim), agora, agora,
                 "Importada de planilha antiga.", "", ""),
            )
            sprint_id = cur.lastrowid
        else:
            sprint_id = "(novo)"

        # ids que já existiam no banco ANTES do import (consulta única)
        if not simular:
            ids_no_banco = {r[0] for r in cur.execute("SELECT id FROM demandas")}
        else:
            ids_no_banco = set()
        ids_criados_agora = set()  # evita recriar quando o mesmo Id aparece 2x na planilha

        # ---- demandas com Id ----
        for _, row in com_id.iterrows():
            demanda_id = int(row["id"])
            titulo = str(row["titulo"]).strip()
            estado = row.get("estado")
            status_k = _status_kanban(estado)
            resp = apelido(str(row.get("responsavel") or "").strip())
            tipo_entrada = "Planejada"  # sprint antiga: tudo tratado como planejado
            if status_k == "Concluído":
                resumo["concluidas"] += 1
            else:
                resumo["pendentes"] += 1

            ja_existe = demanda_id in ids_no_banco or demanda_id in ids_criados_agora

            if not simular:
                if not ja_existe:
                    # cria demanda mínima (só os campos que temos da planilha antiga)
                    cur.execute(
                        "INSERT INTO demandas (id, titulo, responsavel_atendimento, "
                        "data_importacao, data_atualizacao) VALUES (?, ?, ?, ?, ?)",
                        (demanda_id, titulo, _valor_sqlite(row.get("responsavel")), agora, agora),
                    )
                    ids_criados_agora.add(demanda_id)
                    resumo["demandas_criadas"] += 1
                else:
                    resumo["demandas_reaproveitadas"] += 1

                # histórico + snapshot de fechamento (base das métricas e do relatório)
                cur.execute(
                    "INSERT INTO demanda_historico (demanda_id, sprint_id, status_kanban, "
                    "data_inicio, data_fim) VALUES (?, ?, ?, ?, ?)",
                    (demanda_id, sprint_id, status_k, str(inicio), agora),
                )
                cur.execute(
                    "INSERT INTO sprint_fechamento_itens (sprint_id, demanda_id, titulo, "
                    "tipo_entrada, status_final) VALUES (?, ?, ?, ?, ?)",
                    (sprint_id, demanda_id, titulo, tipo_entrada, status_k),
                )
            else:
                marca = "reaproveita" if buscar_demanda(demanda_id) else "cria nova"
                print(f"  [demanda] {demanda_id} — {titulo[:50]:50} | {status_k:12} | {marca}")

        # ---- atividades internas (sem Id) ----
        for _, row in sem_id.iterrows():
            titulo = str(row["titulo"]).strip()
            status_k = _status_kanban(row.get("estado"))
            resp = apelido(str(row.get("responsavel") or "").strip())
            resumo["atividades"] += 1
            if not simular:
                cur.execute(
                    "INSERT INTO atividades_internas (sprint_id, titulo, responsavel_sprint, "
                    "horas_minutos, status_kanban, tipo_entrada) VALUES (?, ?, ?, 0, ?, 'Planejada')",
                    (sprint_id, titulo, resp, status_k),
                )
                # snapshot de fechamento também para as atividades (sem demanda_id)
                cur.execute(
                    "INSERT INTO sprint_fechamento_itens (sprint_id, demanda_id, titulo, "
                    "tipo_entrada, status_final) VALUES (?, NULL, ?, 'Planejada', ?)",
                    (sprint_id, titulo, status_k),
                )
            else:
                print(f"  [atividade] {titulo[:50]:50} | {status_k:12} | {resp}")

        if not simular:
            conn.commit()
    finally:
        if conn is not None:
            conn.close()

    print("\nResumo:")
    print(f"  Demandas reaproveitadas (já existiam no banco): {resumo['demandas_reaproveitadas']}")
    print(f"  Demandas criadas (não existiam):                {resumo['demandas_criadas']}")
    print(f"  Atividades internas:                            {resumo['atividades']}")
    print(f"  Concluídas: {resumo['concluidas']}  |  Pendentes: {resumo['pendentes']}")
    if simular:
        print("\n[SIMULAÇÃO] Nada foi gravado. Rode de novo sem --simular para gravar de verdade.")
    else:
        print(f"\n✅ Sprint '{nome}' importada para o histórico (id interno {sprint_id}).")
        print("   Abra a página Histórico no GP Flow para conferir.")


def main():
    p = argparse.ArgumentParser(description="Importa uma sprint antiga para o histórico do GP Flow.")
    p.add_argument("planilha", help="Caminho do arquivo .xlsx da sprint antiga")
    p.add_argument("--nome", help="Nome da sprint (ex.: 'Sprint 22/06 a 03/07')")
    p.add_argument("--inicio", help="Data de início (AAAA-MM-DD)")
    p.add_argument("--fim", help="Data de fim (AAAA-MM-DD)")
    p.add_argument("--aba", help="Nome da aba de demandas (padrão: a primeira)")
    p.add_argument("--simular", action="store_true", help="Só mostra o que faria, sem gravar")
    args = p.parse_args()

    if not Path(args.planilha).exists():
        print(f"Arquivo não encontrado: {args.planilha}")
        sys.exit(1)

    nome = args.nome or input("Nome da sprint: ").strip()
    inicio = args.inicio or input("Data de início (AAAA-MM-DD): ").strip()
    fim = args.fim or input("Data de fim (AAAA-MM-DD): ").strip()

    importar(args.planilha, nome, inicio, fim, aba=args.aba, simular=args.simular)


if __name__ == "__main__":
    main()
