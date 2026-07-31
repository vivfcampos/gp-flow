"""
Componente customizado Kanban.

A declaração fica aqui — num módulo importado normalmente — em vez de no
top-level de views/kanban.py. Páginas do st.navigation são executadas via
exec() sem __name__ no namespace, e components.declare_component() depende
de __name__ para nomear o componente, causando o erro:
    RuntimeError: module is None. This should never happen.
"""
from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "kanban_board",
    path=str(Path(__file__).parent),
)


def kanban_board(*, data, height=600, key=None):
    """Renderiza o quadro Kanban e devolve o evento emitido pelo front-end."""
    return _component(data=data, height=height, key=key, default=None)
