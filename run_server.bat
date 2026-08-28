@echo off
REM GP Flow — inicia o servidor web (FastAPI)
REM Kanban roda em http://localhost:8000/kanban
REM Acesso pela rede local (colegas na mesma rede/VPN): http://SEU-IP:8000
REM   (rode "ipconfig" pra ver o IP; precisa liberar a porta 8000 no firewall)

set GPFLOW_SECRET_KEY=troque-esta-chave-em-producao

REM Login via Active Directory (opcional) — descomente e preencha quando o
REM TI passar os dados do dominio. Sem isso, o login usa so usuarios locais
REM (tela Usuarios / secrets.toml), como hoje.
REM set LDAP_SERVER=ldap://dc01.empresa.local
REM set LDAP_DOMAIN=empresa.local

uvicorn server.main:app --reload --port 8000 --host 0.0.0.0
