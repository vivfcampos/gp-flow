# Changelog — GP Flow

## v0.8.0 — Suporte a PostgreSQL (deploy na nuvem)

- Nova camada `functions/db.py`: o app continua usando SQLite local por
  padrão, mas passa a usar PostgreSQL automaticamente quando há uma
  connection string em `st.secrets["postgres"]["url"]` ou na variável de
  ambiente `DATABASE_URL`. Necessário porque o Streamlit Community Cloud
  não garante persistência de arquivos locais entre reinícios/redeploys.
- `functions/banco.py` e `functions/metricas.py` adaptados para usar a
  camada nova (sem mudança de comportamento em SQLite).
- Novo script `migrar_dados_para_postgres.py` para copiar os dados
  existentes do SQLite local para o Postgres na primeira publicação.
- `requirements.txt`: adicionado `psycopg2-binary`.


## v0.7.42 — Selecionar tudo em todos os grids

- Checkbox "Selecionar tudo" no header de todos os grids AgGrid:
  Classificar, Planejar sprint, Demandas da sprint, Atividades internas.
  Clicar no checkbox do header seleciona/deseleciona todas as linhas
  visíveis (filtradas) de uma vez — sem botão extra.
- Parâmetro correto para aggrid 1.2.1: header_checkbox=True.


## v0.7.40 — AgGrid em todas as páginas e abas

- Todos os grids migrados para streamlit-aggrid com visual unificado:
  fonte Segoe UI 13px, header cinza uppercase 11px, row hover #f8f9fa,
  selecionado #e7f3ff, borda #e9ecef.
- Sprint: demandas e atividades internas com badges de Status (azul/amarelo/
  laranja/verde) e Tipo entrada (azul/laranja/cinza). Excluir via seleção +
  botão; salvar via botão após edição inline.
- Histórico: tabelas de planejadas/paraquedas/internas com badge de Status.
- Backlog aba Importar: preview das primeiras 5 linhas com AgGrid.
- Backlog aba Planejar: grid de envio com seleção por checkbox e badge de
  Tipo entrada.
- Módulo functions/aggrid_helper.py com estilos e JsCode reutilizáveis.


## v0.7.37 — Kanban visual igual ao mockup

- CSS dos cartões e colunas reescrito para ficar igual ao mockup:
  - Colunas com largura fixa 25% cada (sem esticar por quantidade de itens)
  - Headers: azul (Sprint), laranja (Em andamento), verde (Homologação),
    cinza (Concluído) — tipografia uppercase 12px/600
  - Cartões: fundo branco, borda esquerda azul 3px, sombra sutil,
    hover com fundo levemente cinza
  - Texto do cartão: ID + título na linha 1, responsável · tipo · score na 2
- Título do cartão trunca em 48 chars (era 52).


## v0.7.30 — config.toml corrigido (headingFontWeights como inteiros)

- headingFontWeights deve ser array de inteiros, não strings.
  Corrigido: [700, 600, 500, 500, 400, 400].
- borderRadius removido (não existe no 1.60).


## v0.7.29 — Tema nativo do Streamlit 1.44+ (sem CSS)

- **Sidebar escura via [theme.sidebar]** no config.toml — o Streamlit 1.44
  introduziu suporte nativo a tema separado para o sidebar, incluindo
  backgroundColor, textColor e primaryColor. Isso funciona de forma garantida
  em qualquer versão 1.44+ sem depender de CSS que pode ser bloqueado.
- **Títulos via headingFontSizes e headingFontWeights** no config.toml.
- **borderRadius = "6px"** para cantos arredondados nos componentes.
- **server.enableStaticServing = true** para servir static/gpflow.css.
- CSS reduzido ao mínimo absoluto: apenas o item ativo do nav (que o
  config.toml não controla diretamente) e o separador do menu.


## v0.7.28 — CSS testado e confirmado funcionando

- CSS confirmado via inspeção automatizada: encontrado no DOM, sidebar bg
  #1d2125, h1 22px — todos aplicados corretamente no Streamlit 1.49.
- Ordem corrigida: st.markdown + st.html(Path) ambos ANTES do st.navigation().
- static/gpflow.css incluído no zip (verificado).
- Se ainda não aplicar no 1.60: testar se F5 resolve (timing de cache),
  e verificar se a pasta static/ está presente em C:\gp-flow\static\.


## v0.7.27 — CSS via st.html(Path) + fallback (compatível com 1.49 e 1.60)

- **Causa raiz identificada via DevTools:** o CSS não estava sendo injetado no
  DOM no Streamlit 1.60 — confirmado por inspeção automatizada com Playwright.
- **Dupla injeção:** st.html(Path("static/gpflow.css")) para 1.60 (nova API
  que insere o arquivo CSS como <style> diretamente); st.markdown com
  <style> inline como fallback para 1.49 e versões anteriores.
- CSS movido para static/gpflow.css (arquivo separado, mais fácil de editar).
- config.toml com primaryColor seguro (#3B82F6, luminância > 0.18) para
  não causar header escuro.


## v0.7.26 — CSS via st.html com especificidade alta

- Troca de st.markdown para st.html para injeção do CSS — o st.html injeta
  diretamente no documento principal.
- Especificidade elevada: "html body" e "html body [seletor]" vencem os
  estilos base do Streamlit que usam apenas "body".
- Fonte: Segoe UI / system font (sem CDN externo).
- Sidebar: section[data-testid="stSidebar"] com todos os filhos (div, links,
  spans) cobertos explicitamente.


## v0.7.25 — Visual limpo e estável

- CSS reduzido ao mínimo absoluto: apenas a sidebar escura, que o config.toml
  não controla. Tudo o mais (cores, texto, botões, inputs) via config.toml,
  que é estável entre versões do Streamlit.
- primaryColor alterado para #3B82F6 (azul seguro com luminância > 0.18) para
  evitar que o Streamlit inverta o header para escuro no 1.60.
- Seletor de sidebar trocado para section[data-testid="stSidebar"] + a + a span,
  o mais estável documentado para 1.46–1.60.
- Sem sobreposições de ícones (nenhum seletor genérico que afete pseudo-elementos).


## v0.7.24 — Fix seletores CSS (sem sobreposição de ícones)

- Removido o seletor `[class^="st-"]` que causava sobreposição de ícones
  (arrow_right sobreposto aos títulos dos expanders).
- Sidebar: adicionado `a span` nos seletores de cor para garantir que o
  texto dos links fique visível (#c9d1d9) sobre o fundo escuro.
- Fonte aplicada só em p/h1-h6, nunca em seletores amplos que afetam
  pseudo-elementos.
- config.toml sem primaryColor (causava header preto no 1.60).


## v0.7.23 — CSS correto para Streamlit 1.60

- CSS reescrito com os seletores confirmados para Streamlit 1.60:
  `section[data-testid="stSidebar"]` para o fundo escuro;
  `[data-testid="stSidebarNavItems"]` para os links do nav (seletor novo do
  1.60, antes era `stSidebarNav`); `header[data-testid="stHeader"]` e
  `.stAppHeader` para o header branco.
- `config.toml` com `primaryColor`, `backgroundColor`, `secondaryBackgroundColor`
  e `textColor` — o framework aplica essas cores nativamente em todos os
  componentes sem precisar de CSS.
- Segmented control (abas) com seletor duplo para cobrir 1.49 e 1.60.
- Botão primário com seletor duplo (`baseButton-primary` e
  `stBaseButton-primary`).


## v0.7.22 — Header e conteúdo brancos (fix Streamlit 1.60)

- **Corrigido header/topbar preto.** No Streamlit 1.60, `primaryColor` no
  config.toml causava o header ficar completamente preto. Removido do
  config.toml; o azul #0055cc agora é aplicado só via CSS nos botões primários
  e item ativo do menu.
- **Header explicitamente branco** via CSS `[data-testid="stHeader"]`.
- **Fundo do conteúdo explicitamente branco** via CSS nos data-testids
  principais do Streamlit 1.60 (stAppViewContainer, stMain,
  stMainBlockContainer).
- **Sidebar escura** com seletores mais precisos para não vazar para o header.


## v0.7.21 — Compatibilidade com Streamlit 1.60 + Pandas 3.0

- **Corrigido erro crítico:** `StreamlitAPIException: st.session_state.aba_backlog
  cannot be modified after widget is instantiated` — ocorria no Streamlit 1.60
  que ficou mais restrito com session_state de widgets. Corrigido usando o
  parâmetro `default=` do `st.segmented_control` em vez de pré-popular o
  session_state.
- **Removido `use_container_width`** de todos os botões e popovers (22
  ocorrências) — deprecated no Streamlit 1.60 nesses componentes.
- **Removido `pd.set_option("future.no_silent_downcasting")`** e
  `infer_objects(copy=False)` — deprecated no Pandas 3.0.
- requirements.txt atualizado para `streamlit>=1.55.0`.


## v0.7.20 — Visual estabilizado (sidebar escura + conteúdo limpo)

- Sidebar escura (#1d2125) restaurada com seletores mais abrangentes
  (section[data-testid="stSidebar"] e filhos) para garantir que o fundo
  escuro vença o padrão do Streamlit em todas as versões.
- config.toml simplificado: apenas base="light" e primaryColor="#0055CC" —
  sem textColor/backgroundColor customizados que causavam inversão em
  checkboxes e campos de busca.
- Filtro do Kanban por multiselect direto (sem botão Aplicar): selecionar
  filtra imediatamente.


## v0.7.19 — Sidebar visível + filtro Kanban funcionando

- **Sidebar:** texto visível. O fundo escuro (#1d2125) conflitava com o
  config.toml (#F4F5F7 para secundário), deixando texto claro sobre fundo
  claro. Ajustado para usar o fundo claro nativo com texto escuro (#42526e) e
  item ativo em azul Jira (#deebff + #0055cc) — sem conflito de cor.
- **Filtro do Kanban:** o botão "Aplicar" foi removido. Era a causa do
  problema: o multiselect e o botão tinham estados diferentes no session_state
  e o filtro nunca chegava ao quadro. Agora o multiselect filtra diretamente
  ao selecionar, como o Jira faz — sem intermediário.


## v0.7.18 — Correção de sobreposição de elementos visuais

- **Corrigido:** ícones e textos sobrepostos no menu e nos componentes
  (file_uploader mostrando "uploadpload", expanders com ícones duplicados).
  Causa: seletor CSS `[class*="css"] *` muito amplo afetava pseudo-elementos
  e ícones internos do Streamlit. Substituído por seletores cirúrgicos que
  miram só elementos de texto (p, h1, label, .stMarkdown), sem tocar em
  ícones, SVGs ou pseudo-elementos do framework.


## v0.7.17 — Sistema visual unificado (estilo Jira 2025)

- **Tema nativo via `.streamlit/config.toml`**: cores Jira aplicadas em toda a
  interface pelo próprio Streamlit. Texto #172B4D, fundo #FFFFFF, secundário
  #F4F5F7, primário #0055CC. Antes só o sidebar tinha o novo visual.
- **CSS refinado no app.py**: tipografia Inter, títulos sem emoji (mais
  limpos), botões primários em azul #0055CC, inputs com foco azul, abas do
  Backlog ativa em branco+azul, métricas com label maiúscula + valor grande.
- **Títulos das páginas limpos**: emoji removido do st.title() em todas as
  views — o ícone fica só no menu lateral.
- Visual coerente entre sidebar, Backlog, Sprint, Kanban, Histórico e Resumo.


## v0.7.16 — Visual redesenhado (estilo Jira 2025)

- **Sidebar escura** (#1d2125) com texto em cinza-azulado (#9fadbc), igual ao
  Jira/Linear — cria separação visual clara entre navegação e conteúdo.
- **Item ativo em azul Jira** (#0055cc) com texto branco; hover em cinza
  discreto (#282e33).
- **Tipografia Inter** em toda a interface — mais legível e moderna que a
  fonte padrão do Streamlit.
- **Botões primários em azul #0055cc** (coerente com o item ativo do menu).
- **Abas do Backlog** (segmented control) com aba ativa em branco + texto azul,
  muito mais legível.
- **Métricas** com label em maiúsculas pequenas (11px) e valor em 26px/600,
  mais impactantes.
- **Separador** entre as seções de trabalho e consulta no menu.
- Fonte Inter importada do Google Fonts (requer conexão na primeira carga).


## v0.7.15 — Navegação redesenhada

- Ícones do menu trocados por emojis mais limpos e semanticamente coerentes:
  📥 Backlog, ▶️ Sprint, 📊 Kanban, 🕐 Histórico, 📈 Resumo.
- Item ativo no menu com destaque em azul (tint), seguindo o padrão Linear/Jira.
- Itens inativos com contraste melhorado e hover sutil.
- Separador visual entre as telas de trabalho (Backlog/Sprint/Kanban) e as de
  consulta (Histórico/Resumo).


## v0.7.14 — WIP por responsável + default Sistema TOTVS

- **WIP por responsável.** O limite de trabalho em progresso agora é **por
  pessoa**, não por coluna. Um único número (ex.: 3) define o máximo que cada
  membro do time pode ter simultâneamente nas colunas "Em andamento" e
  "Homologação" somadas. Quando alguém estoura, aparece aviso com o nome e a
  contagem (ex.: ⚠️ Cadu (4/3)). Configurável no expander acima do quadro.
- **Default Sistema = TOTVS.** Na aba Classificar e na janelinha de detalhes,
  o Sistema já vem preenchido como TOTVS para demandas sem sistema definido —
  basta mudar quando não for o caso.


## v0.7.13 — Filtro do Kanban com botão e time fixo

- **Corrigido:** o filtro por responsável não aplicava e não havia como
  acionar. Agora há botões **"🔍 Aplicar filtro"** e **"✖️ Limpar"** — o
  filtro só entra em vigor quando você clica em aplicar, e uma legenda mostra
  o que está ativo.
- Os responsáveis do filtro são os **4 fixos do time: Cadu, Davi, Gi, Vivi**,
  independente de como o nome está gravado no banco (nome completo ou apelido).
  O mapeamento cobre todas as variações encontradas nas planilhas.
- A seleção de filtro é preservada no session_state entre reruns do quadro.


## v0.7.12 — Filtro por responsável no Kanban funcionando

- **Corrigido:** o filtro de responsável no Kanban não filtrava. A causa era
  que o campo `responsavel_sprint` pode conter o nome completo vindo do Trace
  (ex.: "CARLOS EDUARDO FERREIRA PINTO") enquanto o filtro mostrava o apelido
  ("Cadu"). A comparação nunca casava.
- Agora o filtro normaliza o responsável pelo apelido antes de comparar —
  tanto o que aparece no multiselect quanto o que é verificado nos cartões.
- Adicionados aliases no mapeamento de responsáveis para cobrir variações de
  nome das planilhas (ex.: "GISELE PERINI" além de "GISELE MARIA PERINI").


## v0.7.11 — Janelinha de detalhes com edição

- Voltou a janelinha (modal) ao clicar na lupa 🔍. Abre sobre a tela com os
  dados do chamado e permite alterar **Macroprocesso, Sistema, Score e
  Observações** e salvar, sem precisar voltar para a tabela.
- Clicar em "💾 Salvar" ou "✖️ Fechar" fecha a janela e retorna para a
  classificação. Recarregar ao abrir/fechar é esperado — o que não recarrega
  mais é a edição célula a célula na tabela (resolvido na v0.7.9).


## v0.7.10 — Ver detalhes sem recarregar a tabela

- **Corrigido:** clicar na lupa 🔍 (ver detalhes de um chamado) recarregava a
  página inteira e fazia a tabela voltar ao topo — o mesmo incômodo da edição.
  Isso acontecia porque os detalhes abriam numa janela modal, que obriga o
  Streamlit a reprocessar a página toda.
- Agora os detalhes aparecem **inline, logo abaixo da tabela**, dentro do mesmo
  bloco isolado (fragment) da classificação. Ver um chamado é instantâneo e
  não mexe na rolagem: você abre, lê, fecha e continua de onde estava.
- Os detalhes mostram solicitante, responsável, data de criação, aging,
  prioridade, tipo, estado do Trace, sistema, macroprocesso e observações.


## v0.7.9 — Classificação: a tabela não volta mais para o topo

- **Causa identificada pela sua gravação de tela:** o dado sempre era salvo
  corretamente — o problema é que a tabela **rolava de volta para o topo** a
  cada edição, obrigando você a descer de novo. É um bug conhecido do próprio
  Streamlit (a tabela perde a posição de rolagem quando reprocessa a página).
- **Correção:** a tabela de classificação agora roda dentro de um *fragment*
  isolado. Ao editar uma célula, só a tabela é reprocessada — não a página
  inteira — então a rolagem fica no lugar e você segue para a próxima demanda
  logo abaixo, sem o "pulo".
- O aviso de gravação virou um toast discreto (canto da tela), que não desloca
  a tabela. Ver detalhes (🔍) e excluir (🗑️) continuam funcionando.


## v0.7.8 — Classificação: gravação por callback (nova tentativa)

- Mudança de abordagem para o problema da classificação que "voltava ao
  início" a cada duas edições. Agora a gravação usa um **callback do próprio
  editor** (`on_change`), o padrão recomendado do Streamlit: quando você muda
  uma célula, o app grava só aquela demanda e o Streamlit mantém a tabela
  sincronizada, sem recriar nada.
- Além disso, as **opções dos menus** (Macroprocesso/Sistema) agora são
  estáveis entre atualizações — antes elas mudavam ao incorporar o valor
  recém-salvo, o que podia bagunçar o estado do editor.
- A ordem da lista continua fixa (empate por Id), então cada linha sempre
  aponta para a mesma demanda.


## v0.7.7 — Classificação estável (fim do "volta à condição inicial")

- **Corrigido de vez** o comportamento em que uma classificação salvava certo
  e a seguinte "voltava ao início" / recarregava tudo (alternando a cada
  edição). A causa era técnica: o app comparava a tabela inteira a cada
  alteração e trocava a identidade do editor, o que dessincronizava as edições
  quando a lista era reprocessada.
- Agora o app **lê apenas a célula que você acabou de editar** (o "delta" do
  editor) e grava só aquela demanda, sem recriar a tabela. A ordem da lista
  ficou **fixa** durante a classificação (empate resolvido pelo Id), então
  cada linha sempre aponta para a mesma demanda.
- Resultado: dá para classificar uma demanda atrás da outra, na mesma posição,
  sem a lista pular nem reverter. Um aviso curto (toast) confirma cada gravação.


## v0.7.6 — Classificar sem perder o lugar

- **Corrigido:** ao classificar uma demanda (macroprocesso, sistema, score…),
  o app voltava para a primeira aba e o grid "pulava" para um ponto aleatório.
  Eram duas causas: (1) o `st.tabs` não lembrava a aba ativa depois de salvar,
  e (2) o salvamento recriava a tabela do zero.
- **Agora a aba fica fixa.** As três seções (Importar / Classificar / Planejar)
  passaram a usar um seletor que **lembra onde você está** — depois de salvar,
  você continua em Classificar. O app abre direto em Classificar.
- **A classificação salva sem recriar a tabela:** você edita a célula, o valor
  é gravado no banco na hora e um aviso curto (toast) confirma, sem a lista
  "saltar". Assim dá para ir de uma demanda para a próxima de forma fluida.


## v0.7.5 — Atividades internas no fluxo (botão "+", estilo Jira)

- **Novo botão "➕ Nova atividade interna" no Kanban.** Cria uma atividade
  (cerimônia, feriado, reunião…) direto no quadro — ela nasce na coluna
  **Sprint** e já pode ser arrastada como qualquer cartão. Funciona mesmo com
  a sprint ainda vazia.
- **Mesmo "➕" na aba Planejar do Backlog**, para criar a atividade junto com
  o planejamento da sprint, sem precisar abrir a página Sprint.
- **Feedback de salvamento na página Sprint.** A seção de atividades internas
  continua lá, mas agora avisa claramente quando você adiciona ("aparece na
  seção abaixo e no Kanban") e quando salva ("as mudanças já valem no Kanban").
  Antes o salvamento era silencioso, o que passava a impressão de não ter
  funcionado.
- Confirmado ponta a ponta: criar pelo "+" faz a atividade aparecer no Kanban
  e mover entre colunas normalmente. O tipo padrão da atividade já vem como
  **Interna**.


## v0.7.4 — Kanban: reforço no layout das colunas

- Encontrada a causa de fundo: a biblioteca de arrastar-e-soltar só traz CSS
  de `display:flex` para o modo **vertical** — no modo **horizontal** que o
  quadro usa, não há regra padrão, então tudo depende do nosso CSS. Se algo no
  ambiente sobrepõe esse CSS, as colunas caem uma embaixo da outra.
- Reforçado o CSS das colunas com `!important` nas propriedades de layout
  (display flex, direção, largura, min-width), para vencer qualquer regra
  concorrente. Validado em navegador headless (com o CSS real da biblioteca
  carregado junto) em telas de 500px a 1250px: as quatro colunas ficam lado a
  lado em todos os casos.


## v0.7.3 — Correção do layout do Kanban (colunas sumindo)

- **Corrigido:** o quadro do Kanban mostrava só a primeira coluna (Sprint);
  as outras três (Em andamento, Homologação, Concluído) sumiam. A causa foi
  uma regressão de CSS introduzida junto com o WIP limit: as colunas passaram
  a usar `min-width: 0; width: 25%`, o que fazia as colunas vazias colapsarem
  para largura zero. Voltamos para `min-width: 180px` com `flex: 1 1 0` e sem
  `overflow-x`, garantindo que as quatro colunas sempre apareçam lado a lado.
- Validado num navegador headless: as 4 colunas renderizam lado a lado em
  telas de 900px a 1250px, com os cartões empilhados verticalmente dentro de
  cada coluna e os cabeçalhos coloridos (incluindo o indicador de WIP).


## v0.7.2 — Importação do Trace corrigida e enriquecida (qualidade do dado)

Foco: se o dado chega limpo do Trace, o "antes" já fica pronto e a daily é
consequência. Baseado na análise da planilha real do Trace (23 colunas).

- **Corrigido o bug que quebrava a importação.** O importador não pulava a
  linha de título "Demandas" do topo do export e exigia uma coluna
  (Urgência/Importância) que **não existe** no Trace — então falhava por
  completo. Agora ele **detecta a linha de cabeçalho automaticamente** e só
  exige o essencial (Id + Título).
- **Aproveita o que o Trace já traz preenchido**, reduzindo digitação:
  Responsável (vem em ~90% das demandas), Estado (situação real), Prioridade
  e Prioridade de Atendimento, e o **aging já calculado** pelo Trace (Tempo da
  Demanda em dias) — em vez de recalcular pela data.
- **Urgência/Importância virou opcional.** Como o Trace não exporta esse
  campo, o score passa a **redistribuir o peso dele** entre os outros três
  fatores (prioridade, aging, tipo), em vez de aplicar uma nota neutra que
  distorcia a priorização.
- **Coluna "Estado (Trace)"** agora aparece na aba Classificar, para você ver
  a situação de cada demanda sem abrir os detalhes.
- Robustez: tratamento de valores nulos (`pd.NA`) no cálculo de score e aging,
  que antes podia gerar erro em demandas sem data. Migração automática
  adiciona as colunas `prioridade_atendimento` e `aging_trace`.


## v0.7.1 — Usabilidade: menos telas, menos rolagem

Foco no que você apontou como maior atrito: navegação e fluxo. Inspirado em
como o Jira concentra o planejamento numa tela só.

- **Backlog agora é a tela inicial** (o trabalho começa nele). A antiga Home
  virou **Resumo**, enxuta, no fim do menu — estado da sprint, tamanho do
  backlog e a checagem de consistência. Uma parada a menos no caminho.
- **Backlog organizado em 3 abas**, sem página quilométrica para rolar:
  - **📥 Importar** — sobe o export do Trace, exporta e limpa o backlog.
  - **🏷️ Classificar** — lista + curadoria inline (macroprocesso, sistema,
    score, observações), com a lupa 🔍 de detalhes e a exclusão 🗑️.
  - **🏃 Planejar sprint** — envia demandas à sprint ativa ou cria uma nova,
    com "selecionar todas" e as validações de higiene.
- Os dados do backlog são carregados uma vez e compartilhados entre as abas.
- Sem mudança de dados nem de regras — foi tudo reorganização de interface.


## v0.7.0 — Melhorias de experiência (inspiradas em Jira/Azure/Trello)

Quatro práticas consolidadas de plataformas de gestão de demandas, adaptadas
ao porte da equipe (3–6 pessoas) — sem inflar o app com recursos de time
grande (burndown, capacity por hora, etc.).

- **WIP limit no Kanban.** Defina o máximo de itens em "Em andamento" e
  "Homologação" (0 = sem limite). Ao exceder, a coluna sinaliza com ⚠️ e um
  aviso aparece acima do quadro — ajuda o time a terminar antes de puxar
  novos. O status ao arrastar passou a ser derivado pela posição da coluna
  (mais robusto que ler o texto do cabeçalho).
- **Meta da sprint.** Novo campo de objetivo, definível na criação (pela
  telinha do Backlog e pela página Sprint) e editável a qualquer momento no
  cabeçalho da Sprint. Aparece também no Histórico de cada sprint encerrada.
- **Velocidade + alerta de capacidade.** O app calcula a média de demandas
  concluídas nas últimas sprints encerradas e mostra como referência ao criar
  a sprint; se a sprint ativa tiver bem mais demandas que a média, exibe um
  alerta de risco de sobrecarga.
- **Validações de higiene do backlog.** Ao marcar demandas para enviar à
  sprint, o app avisa (sem bloquear) quantas estão sem responsável ou sem
  curadoria (macroprocesso/sistema), incentivando classificar antes.
- Correção secundária: os cartões do Kanban agora rotulam corretamente o tipo
  **Interna** (antes qualquer tipo ≠ Paraquedas virava "Planejada" no cartão).

- Banco: coluna `meta` em `sprints` (com migração automática), funções
  `atualizar_meta_sprint` e `velocidade_media`, e `internas` no resumo de
  encerramento.


## v0.6.8 — Criar sprint pelo Backlog + tipo de entrada "Interna"

- **Criar sprint direto do Backlog.** Na seção *Enviar para a sprint*, quando
  não há sprint ativa, o botão **➕ Criar sprint e enviar** abre uma telinha
  (modal) com nome + início + fim; ao confirmar, a sprint é criada já com as
  demandas marcadas dentro. Quando há sprint ativa, o botão envia as marcadas
  direto para ela — ou seja, no mesmo lugar você escolhe a sprint existente
  ou cria uma nova, sem ir à página Sprint.
- **"Selecionar todas"** continua disponível para marcar todo o Backlog de
  uma vez antes de enviar/criar.
- **Novo tipo de entrada: "Interna"**, ao lado de Planejada e Paraquedas.
  Serve para itens internos (cerimônias, feriados, reuniões) que você queira
  tratar junto das demandas, com uma classificação própria — sem uma coluna
  extra poluindo o grid. As contagens de Planejadas/Paraquedas **não mudam**;
  as Internas aparecem à parte no cabeçalho da Sprint, no resumo de
  encerramento e no Histórico.
- A seção de **atividades internas** da página Sprint (itens sem Id do Trace)
  continua existindo — agora você tem as duas formas: classificar uma demanda
  do Backlog como Interna, ou cadastrar uma atividade interna avulsa na Sprint.


## v0.6.7 — Exclusão só de demandas sem vínculo

- A remoção de demandas do Backlog agora **bloqueia qualquer demanda que
  tenha vínculo**. Só é apagada a demanda que, ao mesmo tempo:
  não está em nenhuma sprint (`sprint_id` nulo), não tem histórico em
  `demanda_historico` e não aparece em `sprint_fechamento_itens`.
- Consequência importante: uma demanda que **voltou de uma sprint encerrada**
  para o Backlog (pendente) fica visível, mas **não pode ser excluída** —
  ela tem histórico, e o histórico é preservado.
- Tanto a remoção em massa (coluna 🗑️) quanto a do modal informam quais Ids
  foram **bloqueados por vínculo**, em vez de apagá-los silenciosamente.
- `excluir_demandas(ids)` passou a retornar
  `{"apagadas", "bloqueadas", "inexistentes"}` e **não remove mais** históricos
  ou itens de fechamento (já que só apaga demandas que não têm nenhum).


## v0.6.6 — Remover demandas do Backlog + Selecionar todas

- **Remoção definitiva de demandas do Backlog** (apaga do banco, irreversível),
  de duas formas:
  - **Em massa:** nova coluna **🗑️ (Excluir)** no grid. Marque as linhas,
    confirme no checkbox de segurança e clique em **Remover selecionadas**.
  - **Uma a uma:** dentro do modal de detalhes (lupa 🔍), no expander
    **🗑️ Excluir esta demanda do banco**.
  - Trava de segurança: a exclusão só atinge demandas que estão no Backlog.
    Ids em sprint, congelados ou concluídos avulsos são ignorados. Históricos
    e itens de fechamento ligados às demandas apagadas também são removidos
    (sem órfãos).
- **Selecionar todas** na seção *Enviar para a sprint*: um checkbox marca
  todas as demandas de uma vez para envio (dá para desmarcar linhas
  individuais depois). O tipo de entrada continua automático conforme o
  estado da sprint.
- Nova função `excluir_demandas(ids)` em `functions/banco.py`.


## v0.6.5 — Lupa de detalhes dentro da própria grid

- Os detalhes da demanda (Solicitante/quem abriu, Responsável, Data de
  criação, Aging) agora abrem a partir de uma coluna **🔍 (Ver)** na esquerda
  do **próprio grid editável** — sem tabela separada. Marque o checkbox da
  linha e o modal abre; ao fechar, o checkbox é desmarcado para permitir
  reabrir a mesma demanda.
- Removidos a tabela de consulta e o expander "Ver detalhes" que ficavam
  acima do grid.
- Nota técnica: o grid editável (`st.data_editor`) não expõe clique em célula
  (`on_select`/`selection_mode`) — por isso a abertura é por checkbox e não
  por clique direto no ícone. É a forma de manter uma única grid com edição
  inline e detalhamento juntos.


## v0.6.4 — Correção: macroprocesso no grid só gravava na 2ª vez

- **Corrigido.** Ao escolher Macroprocesso (ou Sistema/Score/Observações) na
  célula do grid do Backlog, o valor era gravado no banco na primeira vez,
  mas a tela não recarregava — então o grid continuava exibindo o estado
  anterior e parecia que "não salvou". Só na interação seguinte, quando o
  script rodava de novo e relia o banco, o valor aparecia.
- Agora, após salvar, a página faz `st.rerun()` e o grid é remontado a partir
  do banco, refletindo o valor **na primeira vez**. A `key` do grid passou a
  ser versionada para descartar o estado residual do `data_editor` quando os
  dados mudam por fora dele. Mantido o padrão de flash (mensagem sobrevive ao
  rerun) em vez de `st.toast`.


## v0.6.3 — Detalhes da demanda no Backlog (lupa 🔍)

- Retomado o **detalhamento da demanda** que existia na Curadoria, agora no
  **Backlog**. Um expander "🔍 Ver detalhes de uma demanda" traz uma tabela
  de consulta com a lupa clicável na primeira coluna; clicar na lupa abre um
  modal (`st.dialog`) com **Solicitante (quem abriu)**, **Responsável pelo
  atendimento**, **Data de criação** e **Aging**, além de Prioridade, Tipo,
  Urg./Imp., Sistema e Macroprocesso quando preenchidos.
- Mesmo padrão da antiga Curadoria: a seleção da tabela é resetada a cada
  abertura, então dá para reabrir a mesma linha quantas vezes quiser.
- A classificação (Macroprocesso, Sistema, Score, Observações) e o envio à
  sprint continuam na tabela editável e na seção "Enviar para a sprint" logo
  abaixo — o modal é só de consulta, para não competir com a edição inline.


## v0.6.2 — Correção de compatibilidade (SelectboxColumn)

- **Corrige o `TypeError` ao abrir o Backlog.** A coluna Macroprocesso/Sistema
  usava `SelectboxColumn(accept_new_options=True)`, parâmetro que a API do
  `st.column_config.SelectboxColumn` não aceita (só o widget standalone
  `st.selectbox` tem). Removido. Para cadastrar um Macroprocesso ou Sistema
  novo, use o expander **⚙️ Macroprocessos e sistemas cadastrados** no topo
  da tabela — ao cadastrar, o valor passa a aparecer na lista da célula.
- `requirements.txt`: piso do Streamlit ajustado para `>=1.40.0` (o app usa
  apenas APIs disponíveis nessa faixa; o piso anterior `>=1.59.0` era
  desnecessário e não resolvia o erro).
- Silenciado um `FutureWarning` do pandas no cálculo do score
  (`fillna(...).infer_objects(copy=False)`).
- Observação: os avisos de `use_container_width` (deprecado, remoção prevista
  após 2025-12-31) foram **mantidos de propósito** — a alternativa
  `width='stretch'` só existe em versões recentes do Streamlit, e trocar agora
  reduziria a compatibilidade. Fica para uma versão futura, quando o piso for
  elevado.

## v0.6.1 — Correção da navegação (pasta reservada `pages/`)

- Telas movidas de `pages/` para `views/` para evitar a auto-detecção do
  Streamlit, que duplicava rotas e disparava `StreamlitAPIException`.
- README com aviso de migração: apagar a pasta `pages/` antiga ao atualizar.


## v0.6.0 — Simplificação do fluxo: de 8 para 4 telas

Objetivo: menos cliques e menos telas para a mesma capacidade. Nenhuma
função de banco mudou — a fusão foi toda na camada de interface, então os
dados e regras (single source of truth, reconciliação, Paraquedas pelo
botão Iniciar) continuam idênticos.

- **Backlog** agora inclui a **Curadoria** (classificar Macroprocesso,
  Sistema, Score e Observações direto na tabela, com salvamento automático)
  e o **envio para a sprint** (antes no Planning). Importar → classificar →
  enviar acontece sem trocar de página.
- **Planning eliminado como página.** Criar a sprint passou para a tela
  **Sprint**; o envio de demandas do Backlog virou uma seção do **Backlog**.
  O tipo Planejada/Paraquedas continua sendo definido pelo botão
  ▶️ Iniciar sprint (antes de iniciar = Planejada; depois = Paraquedas).
- **Daily virou um Modo dentro do Kanban.** Um toggle "⏱️ Modo Daily" troca
  o quadro arrasta-e-solta pela tabela mínima (Demanda, Responsável, Status,
  Impedimento) da reunião diária. Mesmos registros, uma página a menos.
- **Navegação** reduzida para: Home · 📋 Backlog · 🏃 Sprint · 🗂️ Kanban ·
  📚 Histórico.
- Mantidas as ações de **Limpar Backlog**, exportações (Excel), atividades
  internas, métricas, encerramento com retrospectiva e exclusão de sprint.

# Changelog — GP Flow

## v0.5.0 (build 15) — Limpar Backlog

- **Backlog**: nova ação "⚠️ Limpar demandas do Backlog" na área de
  importação. Apaga **apenas** as demandas que estão no Backlog (mesmo
  critério da listagem: `sprint_id` nulo e não concluídas avulsas), para
  recomeçar a importação do zero. Demandas em sprint, congeladas em sprints
  encerradas e concluídas avulsas **não são afetadas** e não podem ser
  limpas por esta tela. Remove também os históricos e itens de fechamento
  ligados exclusivamente às demandas apagadas (sem deixar órfãos); as
  sprints em si são preservadas. Confirmação obrigatória por checkbox,
  contador do que será removido e mensagem flash após a limpeza.

## v0.5.0 — Reformulação completa conforme especificação funcional

> Esta versão implementa a especificação funcional v0.5 recebida da equipe.
> É a maior mudança até aqui: reorganiza o fluxo inteiro do sistema.

### Arquitetura (mudança de fundo)
- Cada demanda agora existe **uma única vez** no banco. Não há mais uma
  tabela separada de "itens de sprint" — a própria demanda carrega
  `sprint_id`, `status_kanban`, `tipo_entrada`, `responsável da sprint` e
  `impedimento`. Backlog, Curadoria, Planning, Sprint, Daily, Kanban e
  Histórico leem sempre o mesmo registro — sem duplicidade.
- Passa a existir **no máximo uma sprint "Em andamento"** por vez.

### Fluxo novo: Importação → Curadoria → Backlog → Planning → Sprint → Daily/Kanban → Encerramento → Histórico

- **Importação**: agora nunca sobrescreve o que foi gerenciado no GP Flow.
  Ao reimportar, só os campos vindos do Trace são atualizados; Macroprocesso,
  Sistema, Score, Observações, Sprint, Status, Tipo de entrada e Impedimento
  são sempre preservados. Mensagem final mostra Total no arquivo / Novas /
  Atualizadas / **Ignoradas** (sem nenhuma mudança). Demanda nova sempre cai
  no Backlog — nunca entra na sprint sozinha.
- **Backlog**: numeração sequencial visual (não substitui o Id), "Exibindo X
  de Y demandas", pesquisa única em qualquer coluna, ordenação nativa por
  clique no cabeçalho, exportação em Excel (além do CSV).
- **Curadoria**: agora só classifica (Macroprocesso, Sistema, Score,
  Observações) — não mexe mais em sprint ou status. Adicionado "Exportar
  Curadoria".
- **Planning** (tela nova): usada só na reunião de planejamento. Seleciona
  demandas do Backlog e define o Tipo de entrada (Planejada/Paraquedas) antes
  de confirmar. Se a sprint já estiver em andamento e a demanda tiver sido
  importada depois do início dela, o padrão sugerido é Paraquedas.
- **Sprint**: painel único da sprint ativa, com cabeçalho permanente (nome,
  período, dias restantes, quantidade de demandas/planejadas/paraquedas) em
  colunas simples (sem campos escondidos atrás de outros componentes).
  Botão de lixeira remove da sprint e devolve ao Backlog — a demanda nunca é
  excluída.
- **Daily** (tela nova): só Demanda, Responsável, Status, Impedimento. Nada
  além disso, pra caber em 30 minutos.
- **Kanban** (tela nova): colunas fixas Sprint → Em andamento → Homologação
  → Concluído, com **arrastar-e-soltar de verdade**. Move o cartão, grava
  status/data/histórico e salva na hora. Mesmos registros da tela Sprint —
  mudar num lugar reflete no outro.
- **Encerramento da Sprint**: pede a retrospectiva (o que funcionou bem, o
  que dificultou, ações pra próxima sprint), salva os números finais
  (planejadas, paraquedas, concluídas, pendentes) e a sprint vira somente
  leitura. Pendentes voltam pro Backlog; concluídas ficam para sempre
  associadas à sprint encerrada.
- **Histórico** (tela nova): lista as sprints encerradas com resumo,
  lições aprendidas e a relação de demandas planejadas x paraquedas —
  deixando claro o impacto de itens que entraram no meio da sprint.

### Exibição
- Campos com código (ex.: "3.20 - Serviço Suporte", "1 - Baixa") agora
  aparecem sem o código na tela ("Serviço Suporte", "Baixa"). O banco
  continua guardando o valor original.

### Mensagens e erros
- Toda operação que salva mostra confirmação. Erros usam mensagens
  amigáveis — nunca o traceback do Python.

### Removido
- A "Situação da triagem" saiu da Curadoria (não fazia parte do fluxo
  especificado). O rastreamento de horas/capacidade por responsável também
  saiu do escopo desta versão, para manter a tela simples conforme o
  princípio de simplicidade da especificação.

## v0.4.0 — Curadoria e Score de Priorização

### Adicionado
- **Página Curadoria**: classifique cada demanda com Macroprocesso e Sistema
  (listas editáveis em `config/macroprocessos.json` / `config/sistemas.json`,
  ou direto pela própria tela), defina a **Situação da triagem** (Não
  triada, Em análise, Aprovada para sprint, Aguardando mais informações,
  Rejeitada) e o **Score de priorização**.
- **Score sugerido automaticamente**, combinando 4 fatores com pesos
  configuráveis em `config/score.json`:
  - Prioridade do Trace (35%)
  - Urgência/Importância — escala de Eisenhower (25%): 1=faça na hora,
    2=se programe, 3=delegue, 4=melhoria/eliminar
  - Aging — dias parado sem avançar (20%)
  - Tipo — Incidente > Melhoria > Serviço Suporte (20%)
- **Modelo híbrido**: o score sugerido vem pré-preenchido, mas pode ser
  ajustado manualmente na tela. O sistema registra se o valor final foi
  igual ao sugerido ou ajustado (`score_ajustado_manualmente`), para no
  futuro avaliarmos se a régua automática bate com o julgamento da equipe.
- **Backlog**: nova coluna Score + opção de ordenar por ele.
- **Sprint → aba "Demanda do backlog"**: lista de demandas disponíveis
  agora vem ordenada por Score (maior primeiro), com o valor visível
  (⭐7.5 — Id — Título), facilitando montar a sprint pelas mais prioritárias.

## v0.3.0 — Cópia de sprint + Métricas

> Curadoria (macroprocesso/sistema/score) foi novamente adiada, agora para
> v0.4.0, para priorizar as métricas de fluxo que vocês precisam agora.

### Adicionado
- **Copiar itens de uma sprint anterior**: nova aba "📋 Copiar sprint
  anterior" na tela de Sprint. Escolha a sprint de origem, opte por trazer
  só os itens não concluídos (ou todos) e copie com um clique. Cada item
  copiado guarda de qual sprint veio.
- **Histórico de mudança de estado**: toda vez que um item muda de estado
  (Planejado → Em atendimento → Pendente Fornecedor → Concluído, etc.),
  o sistema grava quando entrou e quando saiu daquele estado. É a base das
  métricas de tempo abaixo.
- **Métricas da sprint** (seção "📊 Métricas da sprint"):
  - **Demandas recorrentes**: quantas demandas da sprint atual já apareceram
    em alguma sprint anterior (seja por cópia, seja por terem sido
    adicionadas de novo manualmente) — com detalhe de quais sprints.
  - **Tempo médio por estado**: quantas horas as demandas ficam paradas em
    cada estado (ex.: quanto tempo em média fica "Pendente Fornecedor"),
    considerando todo o histórico conhecido da demanda.
  - **Lead time médio**: dias entre a demanda entrar no GP Flow e ser
    concluída.
  - **Taxa de conclusão**: % de itens da sprint já concluídos.

### Corrigido
- `substituir_itens_sprint` não apaga e recria mais todos os itens ao
  salvar a edição — agora atualiza pelo id, preservando o histórico de
  estado de cada item.

## v0.2.1 — Correções

### Corrigido
- **Data/hora de importação incorreta**: o SQLite grava `CURRENT_TIMESTAMP`
  sempre em UTC, o que deixava a hora exibida 3h adiantada em relação ao
  horário de Brasília. Agora todas as datas gravadas pelo sistema (última
  importação, criação de sprint, atualização de demanda) usam o horário
  local (`America/Sao_Paulo`).

### Adicionado
- **Exclusão de itens da sprint**, individual ou em lote: marque um ou
  vários itens na coluna 🗑️ da tabela e clique em **Excluir marcados**.
  A exclusão é imediata (não depende de clicar em Salvar).

## v0.2.0 — Planejamento de Sprint

> Obs.: invertemos a ordem do roadmap original (a curadoria passou para a
> v0.3.0) porque a planilha de sprint era a necessidade mais imediata da equipe.

### Novidades
- **Página Sprint** (`pages/02_Sprint.py`):
  - Criar, selecionar, encerrar e reabrir sprints.
  - Adicionar **demandas do backlog** — título, responsável (já convertido
    para apelido: Cadu, Davi, Gi, Vivian) e estado vêm preenchidos do Trace.
  - Adicionar **atividades internas** sem Id (Cerimônia Ágil, feriados,
    reuniões, médico...), igual à planilha atual.
  - Edição direto na tabela: horas (H:MM), responsável, estado, observações;
    incluir e excluir linhas.
  - **Capacidade por responsável**: total de horas e itens de cada um.
  - **Exportação Excel** no formato exato da planilha da equipe
    (Id | Título | Horas | Responsável Atendimento | Estado | Observações),
    agrupada por responsável, com subtotais somáveis ([h]:mm) e total geral.
- Novas tabelas no banco: `sprints` e `sprint_itens` (criação automática,
  nenhuma migração manual necessária).
- `config/responsaveis.json`: mapa nome completo → apelido, editável.
- Novos módulos: `functions/sprint.py` e `functions/exportar.py`.

### Formato de horas
- Aceita `H:MM` (0:15, 8:40), decimal (`1.5` ou `1,5` = 1:30) e inteiro
  (`2` = 2:00). Internamente tudo é armazenado em minutos.

## v0.1.0 — Importação e Backlog
- Importação do export Excel do Trace com upsert por Id (nada duplica).
- Banco SQLite local (`data/gpflow.db`).
- Página Backlog: busca, filtros (estado, prioridade, responsável),
  ordenação e download em CSV.
- Aging automático (dias desde a criação) com classificação
  🟢 / 🟡 / 🔴.
