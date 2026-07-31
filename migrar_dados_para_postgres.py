"""
migrar_dados_para_postgres.py — GP Flow

Script AVULSO para copiar os dados do SQLite local (data/gpflow.db) para o
PostgreSQL (Neon/Supabase) configurado em DATABASE_URL. Rode UMA VEZ, antes
do primeiro deploy — depois disso o app passa a gravar direto no Postgres.

Como usar (dentro da pasta do projeto, com o .venv ativado):

    export DATABASE_URL="postgresql://usuario:senha@host/banco"   # Linux/Mac
    set DATABASE_URL=postgresql://usuario:senha@host/banco         # Windows (cmd)

    python3 migrar_dados_para_postgres.py

O script:
  1. Garante que as tabelas existem no Postgres (roda criar_tabelas()).
  2. Copia demandas, importações, sprints, atividades internas, histórico
     e itens de fechamento — nessa ordem (respeita as dependências).
  3. Ignora colunas que existem no SQLite antigo mas não são mais usadas
     pelo app (schema evoluiu); nunca ignora uma coluna que o app usa.
  4. NÃO apaga nada no SQLite. É seguro rodar de novo (ON CONFLICT DO
     NOTHING pelo id) caso precise repetir.
"""
import os
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

TABELAS_EM_ORDEM = [
    "demandas",
    "importacoes",
    "sprints",
    "atividades_internas",
    "demanda_historico",
    "sprint_fechamento_itens",
]


def main():
    if not os.environ.get("DATABASE_URL"):
        print("ERRO: defina a variável de ambiente DATABASE_URL antes de rodar este script.")
        print('Exemplo: export DATABASE_URL="postgresql://usuario:senha@host/banco"')
        sys.exit(1)

    from config import DATABASE
    from functions.db import get_connection, eh_postgres
    from functions.banco import criar_tabelas

    if not eh_postgres():
        print("ERRO: DATABASE_URL foi definida mas a conexão não foi reconhecida como Postgres.")
        sys.exit(1)

    if not Path(DATABASE).exists():
        print(f"ERRO: banco SQLite não encontrado em {DATABASE}.")
        sys.exit(1)

    print(f"Origem (SQLite):  {DATABASE}")
    print("Destino (Postgres): DATABASE_URL configurada\n")

    print("1. Garantindo que as tabelas existem no Postgres...")
    criar_tabelas()

    origem = sqlite3.connect(DATABASE)
    origem.row_factory = sqlite3.Row
    destino = get_connection()
    cur_destino = destino.cursor()

    total_geral = 0
    for tabela in TABELAS_EM_ORDEM:
        cur_origem = origem.cursor()
        cur_origem.execute(f"SELECT * FROM {tabela}")
        linhas = cur_origem.fetchall()
        if not linhas:
            print(f"  {tabela}: 0 linhas (nada a copiar)")
            continue

        colunas_origem = linhas[0].keys()

        # Colunas que o Postgres realmente tem (schema atual do app)
        cur_destino.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (tabela,),
        )
        colunas_destino = {r[0] for r in cur_destino.fetchall()}

        colunas_validas = [c for c in colunas_origem if c in colunas_destino]
        ignoradas = [c for c in colunas_origem if c not in colunas_destino]
        if ignoradas:
            print(f"  {tabela}: ignorando colunas obsoletas {ignoradas} (não usadas pelo app atual)")

        placeholders = ", ".join(["%s"] * len(colunas_validas))
        colunas_sql = ", ".join(colunas_validas)
        comando = (
            f"INSERT INTO {tabela} ({colunas_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT (id) DO NOTHING"
        )

        copiadas = 0
        for linha in linhas:
            valores = [linha[c] for c in colunas_validas]
            cur_destino.execute(comando, valores)
            copiadas += 1

        destino.commit()
        total_geral += copiadas
        print(f"  {tabela}: {copiadas} linhas copiadas")

    # Ajusta as sequences (SERIAL) do Postgres para continuar depois do maior id
    # copiado — senão o próximo INSERT tentaria reusar um id já existente.
    print("\n2. Ajustando sequências (auto-incremento) do Postgres...")
    for tabela in ["importacoes", "sprints", "atividades_internas",
                    "demanda_historico", "sprint_fechamento_itens"]:
        cur_destino.execute(f"SELECT COALESCE(MAX(id), 0) FROM {tabela}")
        maior_id = cur_destino.fetchone()[0]
        cur_destino.execute(
            f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), %s)",
            (maior_id if maior_id else 1,),
        )
    destino.commit()

    origem.close()
    destino.close()
    print(f"\nConcluído: {total_geral} linhas copiadas no total.")
    print("Confira o app apontando para o Postgres antes de considerar a migração definitiva.")


if __name__ == "__main__":
    main()
