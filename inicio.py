"""
Resumo — GP Flow v0.7.1

Painel enxuto: estado da sprint, tamanho do backlog e a checagem de
consistência. O trabalho do dia a dia acontece nas abas do Backlog.
"""
import streamlit as st

from functions.banco import (
    criar_tabelas, sprint_ativa, listar_demandas,
    listar_demandas_sprint, listar_concluidas_avulsas,
    contar_backlog, contar_total,
)

st.set_page_config(page_title="Resumo — GP Flow", page_icon="📈", layout="wide")
criar_tabelas()

st.title("Resumo")

sprint = sprint_ativa()
# cards principais: conta direto no banco (não traz os registros inteiros)
qtd_backlog = contar_backlog()
qtd_total = contar_total()

c1, c2, c3 = st.columns(3)
with c1:
    if sprint:
        st.success(f"Sprint ativa: **{sprint['nome']}**")
        if sprint.get("meta"):
            st.caption(f"🎯 {sprint['meta']}")
    else:
        st.info("Nenhuma sprint ativa.")
c2.metric("Demandas no Backlog", qtd_backlog)
c3.metric("Total de demandas", qtd_total)

with st.expander("🔎 Conferir consistência (Backlog + Sprint + Concluídas = Total)"):
    # o DataFrame completo só é carregado quando o usuário abre este expander
    total_demandas = listar_demandas()
    qtd_sprint_ativa = len(listar_demandas_sprint(sprint["id"])) if sprint else 0
    qtd_congeladas_encerradas = len(
        total_demandas[total_demandas["sprint_id"].notna() & (total_demandas["status_kanban"] == "Concluído")]
    ) - (
        int((listar_demandas_sprint(sprint["id"])["status_kanban"] == "Concluído").sum()) if sprint else 0
    )
    qtd_concluidas_avulsas = len(listar_concluidas_avulsas())

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Total", qtd_total)
    d2.metric("No Backlog", qtd_backlog)
    d3.metric("Na sprint ativa", qtd_sprint_ativa)
    d4.metric("Congeladas (encerradas)", qtd_congeladas_encerradas)
    d5.metric("Concluídas avulsas", qtd_concluidas_avulsas)

    soma = qtd_backlog + qtd_sprint_ativa + qtd_congeladas_encerradas + qtd_concluidas_avulsas
    if soma == qtd_total:
        st.success(f"✅ Consistente: {soma} = total.")
    else:
        st.error(f"⚠️ Inconsistência: soma das partes ({soma}) ≠ total ({qtd_total}).")

st.divider()
st.caption(
    "Fluxo: **📋 Backlog** (importar · classificar · planejar) → **🏃 Sprint** → "
    "**🗂️ Kanban** → **📚 Histórico**. O trabalho começa nas abas do Backlog."
)
