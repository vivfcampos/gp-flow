@echo off
REM GP Flow — inicia o app com as configurações de tema garantidas
REM Execute este arquivo em vez de "streamlit run app.py" diretamente

set STREAMLIT_THEME_BASE=light
set STREAMLIT_THEME_PRIMARY_COLOR=#3B82F6
set STREAMLIT_THEME_BACKGROUND_COLOR=#FFFFFF
set STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR=#F7F8F9
set STREAMLIT_THEME_TEXT_COLOR=#172B4D

streamlit run app.py
