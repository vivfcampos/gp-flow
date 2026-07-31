"""
Histórico — GP Flow v0.5.0

Cada sprint encerrada fica disponível aqui, somente leitura: resumo
(planejadas, concluídas, pendentes, paraquedas), lições aprendidas e a
relação detalhada das demandas — deixando claro Planejado x Executado e
Planejado x Paraquedas (impacto de demandas que entraram no meio da sprint).
"""
import streamlit as st

from functions.banco import criar_tabelas, listar_sprints_encerradas, itens_fechamento_sprint, excluir_sprint

st.set_page_config(page_title="Histórico — GP Flow", page_icon="🕐", layout="wide")
criar_tabelas()

st.title("Histórico")

if flash := st.session_state.pop("flash_hist", None):
    st.success(flash)

sprints = listar_sprints_encerradas()
if sprints.empty:
    st.info("Nenhuma sprint encerrada ainda.")
    st.stop()

for _, sprint in sprints.iterrows():
    with st.expander(f"🏁 {sprint['nome']} — encerrada em {sprint['encerrada_em']}"):
        if sprint.get("meta"):
            st.info(f"🎯 **Meta:** {sprint['meta']}")
        itens = itens_fechamento_sprint(sprint["id"])

        total = len(itens)
        planejadas = int((itens["tipo_entrada"] == "Planejada").sum())
        paraquedas = int((itens["tipo_entrada"] == "Paraquedas").sum())
        internas = int((itens["tipo_entrada"] == "Interna").sum())
        concluidas = int((itens["status_final"] == "Concluído").sum())
        pendentes = total - concluidas
        pct_conclusao = round(concluidas / total * 100, 1) if total else 0.0

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total de demandas", total)
        c2.metric("Planejadas", planejadas)
        c3.metric("Paraquedas", paraquedas)
        c4.metric("Internas", internas)
        c5.metric("Concluídas", concluidas)
        c6.metric("% Conclusão", f"{pct_conclusao}%")

        st.caption(
            f"Planejado x Executado: {planejadas} planejadas, {concluidas} concluídas ao todo "
            f"({pct_conclusao}% da sprint). "
            f"Planejado x Paraquedas: de {total} itens, {paraquedas} entraram depois do início "
            f"({round(paraquedas/total*100, 1) if total else 0}% de impacto sobre o planejamento original)."
        )

        st.markdown("**Lições aprendidas**")
        lc1, lc2, lc3 = st.columns(3)
        lc1.markdown(f"✅ **O que funcionou bem**\n\n{sprint['retro_bem'] or '_não preenchido_'}")
        lc2.markdown(f"⚠️ **O que dificultou**\n\n{sprint['retro_dificultou'] or '_não preenchido_'}")
        lc3.markdown(f"🎯 **Ações p/ próxima sprint**\n\n{sprint['retro_acoes'] or '_não preenchido_'}")

        from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
        from functions.aggrid_helper import AG_CSS

        status_style = JsCode("""
        function(params) {
            var v = (params.value || '').toLowerCase();
            var s = {borderRadius:'4px',padding:'1px 7px',fontWeight:'500',fontSize:'12px',display:'inline-block'};
            if (v.includes('conclu')) return Object.assign({},s,{background:'#d3f9d8',color:'#2b8a3e'});
            if (v.includes('and'))    return Object.assign({},s,{background:'#fff3bf',color:'#e67700'});
            if (v.includes('sprint')) return Object.assign({},s,{background:'#d0ebff',color:'#1864ab'});
            return Object.assign({},s,{background:'#f1f3f5',color:'#495057'});
        }""")

        def _ag_itens(df_itens, key):
            if df_itens.empty:
                st.caption("_Nenhum item_")
                return
            gb = GridOptionsBuilder.from_dataframe(df_itens)
            gb.configure_default_column(resizable=True, sortable=True, editable=False)
            gb.configure_column("Id",           width=80)
            gb.configure_column("Título",       width=400, tooltipField="Título")
            gb.configure_column("Status final", width=130, cellStyle=status_style)
            gb.configure_grid_options(rowHeight=36, headerHeight=38)
            AgGrid(df_itens, gridOptions=gb.build(),
                   height=min(len(df_itens)*44+60, 280),
                   update_mode=GridUpdateMode.NO_UPDATE,
                   data_return_mode=DataReturnMode.AS_INPUT,
                   allow_unsafe_jscode=True, theme="streamlit",
                   custom_css=AG_CSS, key=key)

        st.markdown("**Demandas planejadas**")
        _ag_itens(
            itens[itens["tipo_entrada"]=="Planejada"][["demanda_id","titulo","status_final"]]
            .rename(columns={"demanda_id":"Id","titulo":"Título","status_final":"Status final"}),
            key=f"ag_hist_plan_{sprint['id']}"
        )

        st.markdown("**Demandas Paraquedas** (adicionadas após o início da sprint)")
        _ag_itens(
            itens[itens["tipo_entrada"]=="Paraquedas"][["demanda_id","titulo","status_final"]]
            .rename(columns={"demanda_id":"Id","titulo":"Título","status_final":"Status final"}),
            key=f"ag_hist_para_{sprint['id']}"
        )

        if internas:
            st.markdown("**Demandas internas** (cerimônias, feriados, reuniões…)")
            _ag_itens(
                itens[itens["tipo_entrada"]=="Interna"][["demanda_id","titulo","status_final"]]
                .rename(columns={"demanda_id":"Id","titulo":"Título","status_final":"Status final"}),
                key=f"ag_hist_int_{sprint['id']}"
            )

        st.divider()
        confirmar = st.checkbox("Sim, quero excluir esta sprint do histórico", key=f"confirma_exclusao_{sprint['id']}")
        if st.button(
            "🗑️ Excluir esta sprint do histórico", key=f"excluir_{sprint['id']}",
            disabled=not confirmar,
        ):
            try:
                excluir_sprint(sprint["id"])
                st.session_state.flash_hist = "🗑️ Sprint excluída do histórico."
                st.rerun()
            except Exception:
                st.error("Não foi possível excluir. Tente novamente.")
