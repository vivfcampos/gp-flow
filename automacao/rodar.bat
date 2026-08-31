@echo off
REM GP Flow — roda a importacao automatica (mesma coisa que o Agendador de
REM Tarefas dispara as 8h e 14h). Pode dar 2 cliques nesse arquivo a
REM qualquer momento pra importar na hora.
cd /d "%~dp0.."
".venv\Scripts\python.exe" "automacao\importar_automatico.py"
