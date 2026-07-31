"""
Helper: AgGrid com visual padrão GP Flow.
Importar em qualquer view: from functions.aggrid_helper import ag, AG_CSS, ag_opts
"""
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode

AG_CSS = {
    ".ag-theme-streamlit": {
        "--ag-font-size": "13px",
        "--ag-font-family": "'Segoe UI', -apple-system, sans-serif",
        "--ag-row-hover-color": "#f8f9fa",
        "--ag-selected-row-background-color": "#e7f3ff",
        "--ag-header-background-color": "#f8f9fa",
        "--ag-header-foreground-color": "#6c757d",
        "--ag-border-color": "#e9ecef",
        "--ag-cell-horizontal-border": "none",
        "--ag-odd-row-background-color": "#ffffff",
        "--ag-row-border-color": "#f1f3f5",
    },
    ".ag-header-cell-label": {
        "font-size": "11px",
        "font-weight": "600",
        "text-transform": "uppercase",
        "letter-spacing": "0.04em",
        "color": "#6c757d",
    },
    ".ag-cell": {
        "line-height": "36px",
    },
}

# JsCode reutilizável para badges de status_kanban / status_final
STATUS_KANBAN_STYLE = JsCode("""
function(params) {
    var v = (params.value || '').toLowerCase();
    var s = {borderRadius:'4px', padding:'1px 7px', fontWeight:'500', fontSize:'12px', display:'inline-block'};
    if (v.includes('sprint'))        return Object.assign({}, s, {background:'#d0ebff', color:'#1864ab'});
    if (v.includes('em and'))        return Object.assign({}, s, {background:'#fff3bf', color:'#e67700'});
    if (v.includes('pendente'))      return Object.assign({}, s, {background:'#ffe3e3', color:'#c92a2a'});
    if (v.includes('homolog'))       return Object.assign({}, s, {background:'#ffe8cc', color:'#d9480f'});
    if (v.includes('conclu'))        return Object.assign({}, s, {background:'#d3f9d8', color:'#2b8a3e'});
    return {};
}""")

TIPO_ENTRADA_STYLE = JsCode("""
function(params) {
    var v = (params.value || '');
    var s = {borderRadius:'4px', padding:'1px 7px', fontWeight:'500', fontSize:'12px', display:'inline-block'};
    if (v === 'Planejada')   return Object.assign({}, s, {background:'#d0ebff', color:'#1864ab'});
    if (v === 'Paraquedas')  return Object.assign({}, s, {background:'#ffe8cc', color:'#d9480f'});
    if (v === 'Interna')     return Object.assign({}, s, {background:'#f1f3f5', color:'#495057'});
    return {};
}""")

def ag(df, gb_config_fn, height=400, editable=True, key="ag_grid",
       selection="multiple", checkbox=True,
       update_mode=GridUpdateMode.MODEL_CHANGED):
    """
    Renderiza um AgGrid com visual padrão GP Flow.
    gb_config_fn: função que recebe um GridOptionsBuilder e o configura.
    Retorna o objeto AgGridReturn.
    """
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        resizable=True, sortable=True, filterable=True,
        editable=False, wrapText=False,
    )
    gb_config_fn(gb)
    if checkbox:
        gb.configure_selection(selection_mode=selection, use_checkbox=checkbox)
    gb.configure_grid_options(rowHeight=36, headerHeight=38,
                              stopEditingWhenCellsLoseFocus=True)
    return AgGrid(
        df,
        gridOptions=gb.build(),
        height=height,
        update_mode=update_mode,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
        theme="streamlit",
        custom_css=AG_CSS,
        key=key,
    )
