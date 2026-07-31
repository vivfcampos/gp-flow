"""
Resumo — GP Flow v0.7.1

Painel enxuto: estado da sprint, tamanho do backlog e a checagem de
consistência. O trabalho do dia a dia acontece nas abas do Backlog.
"""
import streamlit as st

from functions.banco import (
    criar_tabelas, sprint_ativa, listar_backlog, listar_demandas,
    listar_demandas_sprint, listar_concluidas_avulsas,
)

st.set_page_config(page_title="Resumo — GP Flow", page_icon="📈", layout="wide")
criar_tabelas()

st.title("Resumo")

sprint = sprint_ativa()
backlog = listar_backlog()
total_demandas = listar_demandas()

c1, c2, c3 = st.columns(3)
with c1:
    if sprint:
        st.success(f"Sprint ativa: **{sprint['nome']}**")
        if sprint.get("meta"):
            st.caption(f"🎯 {sprint['meta']}")
    else:
        st.info("Nenhuma sprint ativa.")
c2.metric("Demandas no Backlog", len(backlog))
c3.metric("Total de demandas", len(total_demandas))

with st.expander("🔎 Conferir consistência (Backlog + Sprint + Concluídas = Total)"):
    qtd_sprint_ativa = len(listar_demandas_sprint(sprint["id"])) if sprint else 0
    qtd_congeladas_encerradas = len(
        total_demandas[total_demandas["sprint_id"].notna() & (total_demandas["status_kanban"] == "Concluído")]
    ) - (
        int((listar_demandas_sprint(sprint["id"])["status_kanban"] == "Concluído").sum()) if sprint else 0
    )
    qtd_concluidas_avulsas = len(listar_concluidas_avulsas())

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Total", len(total_demandas))
    d2.metric("No Backlog", len(backlog))
    d3.metric("Na sprint ativa", qtd_sprint_ativa)
    d4.metric("Congeladas (encerradas)", qtd_congeladas_encerradas)
    d5.metric("Concluídas avulsas", qtd_concluidas_avulsas)

    soma = len(backlog) + qtd_sprint_ativa + qtd_congeladas_encerradas + qtd_concluidas_avulsas
    if soma == len(total_demandas):
        st.success(f"✅ Consistente: {soma} = total.")
    else:
        st.error(f"⚠️ Inconsistência: soma das partes ({soma}) ≠ total ({len(total_demandas)}).")

st.divider()
st.caption(
    "Fluxo: **📋 Backlog** (importar · classificar · planejar) → **🏃 Sprint** → "
    "**🗂️ Kanban** → **📚 Histórico**. O trabalho começa nas abas do Backlog."
)
