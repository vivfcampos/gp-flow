"""
Migra os dados de um banco Postgres (Neon origem) para outro (Neon destino).
Usado para mover o banco de região (ex.: Brasil -> EUA).

Uso (na pasta do projeto, com o venv ativo):

    # URL do banco ATUAL (origem, Brasil)
    set NEON_ORIGEM=postgresql://usuario:senha@ep-xxxx-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require
    # URL do banco NOVO (destino, EUA)
    set NEON_DESTINO=postgresql://usuario:senha@ep-yyyy-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require

    python migrar_neon_para_neon.py

(No Linux/Mac use `export` em vez de `set`.)

O script cria as tabelas no destino e copia todas as linhas. Pode rodar de novo:
ele limpa as tabelas do destino antes de copiar (--append para não limpar).
"""
import os
import sys

import psycopg2
import psycopg2.extras

TABELAS = [
    "demandas", "importacoes", "sprints", "atividades_internas",
    "demanda_historico", "sprint_fechamento_itens",
]


def conectar(url):
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor)


def colunas_do_destino(cur_dst, tabela):
    cur_dst.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (tabela,),
    )
    return {r[0] for r in cur_dst.fetchall()}


def main(append=False):
    origem = os.environ.get("NEON_ORIGEM")
    destino = os.environ.get("NEON_DESTINO")
    if not origem or not destino:
        print("ERRO: defina NEON_ORIGEM e NEON_DESTINO com as connection strings.")
        sys.exit(1)

    # cria as tabelas no destino usando a própria camada do app
    os.environ["DATABASE_URL"] = destino
    from functions.banco import criar_tabelas
    criar_tabelas()
    print("Tabelas garantidas no banco de destino (EUA).")

    src = conectar(origem)
    dst = conectar(destino)
    scur = src.cursor()
    dcur = dst.cursor()

    total = 0
    for tabela in TABELAS:
        # lê tudo da origem
        try:
            scur.execute(f"SELECT * FROM {tabela}")
            linhas = scur.fetchall()
        except Exception as e:
            print(f"  {tabela}: erro ao ler origem ({e}); pulando.")
            src.rollback()
            continue

        cols_destino = colunas_do_destino(dcur, tabela)

        if not append:
            dcur.execute(f"DELETE FROM {tabela}")

        if not linhas:
            print(f"  {tabela}: 0 linhas.")
            continue

        # só copia colunas que existem nos dois
        colunas = [c for c in linhas[0].keys() if c in cols_destino]
        col_sql = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(colunas))
        insert = f"INSERT INTO {tabela} ({col_sql}) VALUES ({placeholders})"

        for row in linhas:
            dcur.execute(insert, tuple(row[c] for c in colunas))

        # ajusta a sequência do id (para próximos inserts não colidirem)
        if "id" in colunas:
            dcur.execute(
                f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {tabela}), 1))"
            )

        print(f"  {tabela}: {len(linhas)} linha(s) copiada(s).")
        total += len(linhas)

    dst.commit()
    src.close()
    dst.close()
    print(f"\nMigração concluída. Total de linhas copiadas: {total}")
    print("Confira os números e, se bater, troque a URL nos secrets do Streamlit.")


if __name__ == "__main__":
    main(append="--append" in sys.argv)