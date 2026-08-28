"""Ações de demanda comuns a todas as telas (Backlog/Sprint/Kanban/Histórico):
encerrar (marcar Concluído) e excluir (apagar de vez, com a trava de
histórico já existente em functions.banco.excluir_demandas)."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from functions.banco import concluir_demanda, excluir_demandas
from server.routes_auth import exigir_login

router = APIRouter(prefix="/api/demandas")


@router.post("/{demanda_id}/concluir")
def concluir(demanda_id: int, request: Request):
    if erro := exigir_login(request):
        return erro
    concluir_demanda(demanda_id)
    return {"ok": True}


@router.delete("/{demanda_id}")
def excluir(demanda_id: int, request: Request):
    if erro := exigir_login(request):
        return erro
    resultado = excluir_demandas([demanda_id])
    if resultado["apagadas"]:
        return {"ok": True}
    if resultado["bloqueadas"]:
        return JSONResponse(
            {"erro": "Essa demanda já passou por sprint — não pode ser apagada, protege o histórico."},
            status_code=400,
        )
    return JSONResponse({"erro": "Demanda não encontrada."}, status_code=404)
