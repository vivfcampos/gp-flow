(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  document.getElementById("btn-logout").addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });

  function escapeHTML(s) {
    const d = document.createElement("div");
    d.textContent = String(s ?? "");
    return d.innerHTML;
  }
  function flash(msg) {
    $("flash").textContent = msg; $("flash").hidden = false;
    setTimeout(() => { $("flash").hidden = true; }, 3500);
  }
  function flashErro(msg) {
    $("flash-erro").textContent = msg; $("flash-erro").hidden = false;
    setTimeout(() => { $("flash-erro").hidden = true; }, 4500);
  }
  function opcoes(lista, atual) {
    return lista.map((v) => `<option value="${escapeHTML(v)}" ${v === atual ? "selected" : ""}>${escapeHTML(v)}</option>`).join("");
  }

  const state = { backlog: [], config: null, token: null, detId: null };
  gpMakeSortable(document.getElementById("tabela-classificar"));
  gpMakeSortable(document.getElementById("tabela-planejar"));
  gpMakeSortable(document.getElementById("tabela-preview"));

  // ── Abas ─────────────────────────────────────────────────────────────────
  document.querySelectorAll(".aba-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".aba-btn").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      ["importar", "classificar", "planejar"].forEach((a) => { $("aba-" + a).hidden = a !== btn.dataset.aba; });
    });
  });

  // ── ABA IMPORTAR ─────────────────────────────────────────────────────────
  $("importar-arquivo").addEventListener("change", async (e) => {
    const arquivo = e.target.files[0];
    if (!arquivo) return;
    const fd = new FormData();
    fd.append("arquivo", arquivo);
    const resp = await fetch("/api/backlog/importar/preview", { method: "POST", body: fd });
    const dados = await resp.json();
    if (!resp.ok) {
      flashErro(dados.erro || "Não foi possível ler esse arquivo.");
      e.target.value = "";
      return;
    }
    state.token = dados.token;
    flash(`Arquivo lido: ${dados.total} demandas encontradas.`);
    $("importar-total").textContent = `${dados.total} demandas no arquivo — prévia das 5 primeiras:`;
    document.querySelector("#tabela-preview tbody").innerHTML = dados.preview.map((r) => `
      <tr><td>${r.id}</td><td>${escapeHTML(r.titulo)}</td><td>${escapeHTML(r.prioridade || "")}</td>
          <td>${escapeHTML(r.estado || "")}</td><td>${escapeHTML(r.responsavel || "")}</td></tr>`).join("");
    $("importar-preview").hidden = false;
  });

  $("btn-confirmar-importacao").addEventListener("click", async () => {
    if (!state.token) return;
    const resp = await fetch("/api/backlog/importar/confirmar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: state.token }),
    });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      flash(`Importação concluída — Total: ${dados.total} · Novas: ${dados.novas} · Atualizadas: ${dados.atualizadas} · Ignoradas: ${dados.ignoradas}`);
      resetImportar();
      carregarUltimaImportacao();
      carregarBacklog();
    } else {
      flashErro(dados.erro || "Não foi possível concluir a importação.");
    }
  });

  $("btn-cancelar-importacao").addEventListener("click", async () => {
    if (state.token) {
      await fetch("/api/backlog/importar/cancelar", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: state.token }),
      });
    }
    resetImportar();
  });

  function resetImportar() {
    state.token = null;
    $("importar-arquivo").value = "";
    $("importar-preview").hidden = true;
  }

  async function carregarUltimaImportacao() {
    const resp = await fetch("/api/backlog/ultima-importacao");
    const dados = await resp.json();
    $("ultima-importacao").textContent = dados
      ? `📥 Última importação: ${dados.arquivo} em ${dados.data_hora} — ${dados.novas} novas, ${dados.atualizadas} atualizadas, ${dados.ignoradas || 0} ignoradas.`
      : "";
  }

  $("conf-limpar").addEventListener("change", (e) => { $("btn-limpar").disabled = !e.target.checked; });
  $("btn-limpar").addEventListener("click", async () => {
    const resp = await fetch("/api/backlog/limpar", { method: "POST" });
    const dados = await resp.json();
    if (resp.ok) {
      flash(`Backlog limpo: ${dados.removidas} demanda(s) removida(s). Você pode importar do zero.`);
      $("conf-limpar").checked = false;
      $("btn-limpar").disabled = true;
      carregarBacklog();
    }
  });

  // ── Carrega config + backlog ─────────────────────────────────────────────
  async function carregarConfig() {
    const resp = await fetch("/api/backlog/config");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    state.config = await resp.json();
    const c = state.config;

    const leg = c.legenda_urgencia_importancia;
    $("legenda-score").innerHTML = `
      <p>Score sugerido = média ponderada de 4 fatores (pesos em config/score.json):</p>
      <ul>
        <li><b>Prioridade do Trace</b> (35%)</li>
        <li><b>Urgência/Importância</b> (25%) — escala de Eisenhower:
          <ul><li>1 = ${escapeHTML(leg["1"] || "")}</li><li>2 = ${escapeHTML(leg["2"] || "")}</li>
              <li>3 = ${escapeHTML(leg["3"] || "")}</li><li>4 = ${escapeHTML(leg["4"] || "")}</li></ul></li>
        <li><b>Aging</b> (20%) — quanto mais dias parado, maior a nota</li>
        <li><b>Tipo</b> (20%) — Incidente > Melhoria > Serviço Suporte</li>
      </ul>
      <p>O Score final pode ser diferente do sugerido — é só digitar outro valor.</p>`;

    $("lista-macroprocessos").textContent = c.macroprocessos.join(", ") || "nenhum cadastrado";
    $("lista-sistemas").textContent = c.sistemas.join(", ") || "nenhum cadastrado";

    if (c.sprint_ativa) {
      const tipoPadrao = c.sprint_ativa.em_andamento ? "Paraquedas" : "Planejada";
      $("planejar-caption").textContent =
        `Sprint ativa: ${c.sprint_ativa.nome} (${c.sprint_ativa.em_andamento ? "🏃 em andamento" : "🗓️ em planejamento"}). Marque as demandas e envie — entram como ${tipoPadrao}.`;
      $("planejar-nova-atividade").hidden = false;
      $("pj-ativ-resp").innerHTML = ['<option value=""></option>'].concat(opcoes(c.apelidos, "")).join("");
      $("pj-ativ-tipo").innerHTML = opcoes(["Planejada", "Paraquedas", "Interna"], "Interna");
      $("btn-enviar-sprint").dataset.modo = "enviar";
    } else {
      $("planejar-caption").textContent =
        "Não há sprint ativa. Marque as demandas e clique em Criar sprint e enviar para abrir uma sprint nova já com elas dentro.";
      $("planejar-nova-atividade").hidden = true;
      $("btn-enviar-sprint").dataset.modo = "criar";
    }
  }

  async function carregarBacklog() {
    const resp = await fetch("/api/backlog");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    state.backlog = await resp.json();
    renderClassificar();
    renderPlanejar();
  }

  // ── Macro/Sistema: adicionar ────────────────────────────────────────────
  $("novo-macro").addEventListener("input", (e) => { $("btn-add-macro").disabled = !e.target.value.trim(); });
  $("btn-add-macro").addEventListener("click", async () => {
    const nome = $("novo-macro").value.trim();
    await fetch("/api/backlog/config/macroprocesso", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome }),
    });
    $("novo-macro").value = ""; $("btn-add-macro").disabled = true;
    flash(`Macroprocesso '${nome}' cadastrado!`);
    carregarConfig();
  });
  $("novo-sistema").addEventListener("input", (e) => { $("btn-add-sistema").disabled = !e.target.value.trim(); });
  $("btn-add-sistema").addEventListener("click", async () => {
    const nome = $("novo-sistema").value.trim();
    await fetch("/api/backlog/config/sistema", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome }),
    });
    $("novo-sistema").value = ""; $("btn-add-sistema").disabled = true;
    flash(`Sistema '${nome}' cadastrado!`);
    carregarConfig();
  });


  // ── ABA CLASSIFICAR ──────────────────────────────────────────────────────
  function filtrarBacklog(termo) {
    if (!termo) return state.backlog;
    const t = termo.trim();
    const idsMatch = t.match(/\d{4,}/g);
    const resto = t.replace(/[\d\s;,\-–—/]+/g, "");
    if (idsMatch && !resto) {
      const ids = idsMatch.map(Number);
      return state.backlog.filter((r) => ids.includes(r.id));
    }
    const termoLower = t.toLowerCase();
    return state.backlog.filter((r) => r.titulo.toLowerCase().includes(termoLower) || String(r.id).includes(termoLower));
  }

  function renderClassificar() {
    const filtrado = filtrarBacklog($("busca-classificar").value);
    $("contagem-classificar").textContent = `${filtrado.length} de ${state.backlog.length} demandas no Backlog — edite direto na tabela (salva sozinho).`;

    const macros = state.config.macroprocessos;
    const sistemas = state.config.sistemas;
    const tbody = document.querySelector("#tabela-classificar tbody");
    tbody.innerHTML = filtrado.map((r) => {
      const listaMacro = [""].concat(macros.includes(r.macroprocesso) || !r.macroprocesso ? macros : macros.concat([r.macroprocesso]));
      const listaSist = [""].concat(sistemas.includes(r.sistema) || !r.sistema ? sistemas : sistemas.concat([r.sistema]));
      return `
      <tr data-id="${r.id}">
        <td>${r.id}</td>
        <td class="det-titulo-cell" style="cursor:pointer;text-decoration:underline;">${escapeHTML(r.titulo)}</td>
        <td>${escapeHTML(r.estado || "")}</td>
        <td>${escapeHTML(r.prioridade_exibicao || "")}</td>
        <td>${r.score_sugerido}</td>
        <td data-sort="${r.score_exibicao ?? r.score_sugerido}"><input type="number" class="f-score" min="0" max="10" step="0.5" value="${r.score_exibicao ?? r.score_sugerido}"></td>
        <td>${r.aging_dias}</td>
        <td data-sort="${escapeHTML(r.macroprocesso)}"><select class="f-macro">${opcoes(listaMacro, r.macroprocesso)}</select></td>
        <td data-sort="${escapeHTML(r.sistema)}"><select class="f-sist">${opcoes(listaSist, r.sistema)}</select></td>
        <td data-sort="${escapeHTML(r.observacoes)}"><input type="text" class="f-obs" value="${escapeHTML(r.observacoes)}"></td>
        <td data-sort="${escapeHTML(r.data_importacao || "")}" data-sort-tipo="data-br">${escapeHTML(r.data_importacao || "—")}</td>
      </tr>`;
    }).join("");
    gpSyncDataSort(tbody);

    tbody.querySelectorAll("tr").forEach((tr) => {
      const salvar = () => salvarCuradoriaLinha(Number(tr.dataset.id), tr);
      tr.querySelector(".f-score").addEventListener("change", salvar);
      tr.querySelector(".f-macro").addEventListener("change", salvar);
      tr.querySelector(".f-sist").addEventListener("change", salvar);
      tr.querySelector(".f-obs").addEventListener("change", salvar);
      tr.querySelector(".det-titulo-cell").addEventListener("click", () => abrirDetalhes(Number(tr.dataset.id)));
    });
  }

  async function salvarCuradoriaLinha(id, tr) {
    const registro = state.backlog.find((r) => r.id === id);
    const body = {
      macroprocesso: tr.querySelector(".f-macro").value,
      sistema: tr.querySelector(".f-sist").value,
      score: parseFloat(tr.querySelector(".f-score").value || "0"),
      score_sugerido: registro ? registro.score_sugerido : 0,
      observacoes: tr.querySelector(".f-obs").value,
    };
    const resp = await fetch(`/api/backlog/demanda/${id}/curadoria`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (resp.ok) {
      flash(`✅ Demanda ${id} salva.`);
      carregarBacklog();
    } else {
      flashErro(`Não foi possível salvar a demanda ${id}.`);
    }
  }

  $("busca-classificar").addEventListener("input", renderClassificar);

  // ── Modal de detalhes ────────────────────────────────────────────────────
  function abrirDetalhes(id) {
    const r = state.backlog.find((x) => x.id === id);
    if (!r) return;
    state.detId = id;

    $("det-titulo").textContent = `${id} — ${r.titulo}`;
    const extras = [];
    if (r.solicitante) extras.push(`<b>Solicitante:</b> ${escapeHTML(r.solicitante)}`);
    if (r.responsavel_atendimento) extras.push(`<b>Resp. atendimento:</b> ${escapeHTML(r.responsavel_atendimento)}`);
    if (r.data_criacao) extras.push(`<b>Criado em:</b> ${escapeHTML(String(r.data_criacao).slice(0, 10))}`);
    extras.push(`<b>Aging:</b> ${r.aging_dias} dias`);
    $("det-meta").innerHTML = extras.map((e) => `<div>${e}</div>`).join("");

    const macros = state.config.macroprocessos;
    const sistemas = state.config.sistemas;
    $("det-macro").innerHTML = opcoes([""].concat(macros.includes(r.macroprocesso) || !r.macroprocesso ? macros : macros.concat([r.macroprocesso])), r.macroprocesso);
    $("det-sist").innerHTML = opcoes([""].concat(sistemas.includes(r.sistema) || !r.sistema ? sistemas : sistemas.concat([r.sistema])), r.sistema);
    $("det-score").value = r.score_exibicao ?? r.score_sugerido;
    $("det-obs").value = r.observacoes;

    if (state.config.sprint_ativa) {
      $("det-sprint-bloco").hidden = false;
      const tipo = state.config.sprint_ativa.em_andamento ? "Paraquedas" : "Planejada";
      $("det-sprint-info").textContent = `Sprint ativa: ${state.config.sprint_ativa.nome} — envio como ${tipo}`;
      $("det-sprint-resp").innerHTML = ['<option value=""></option>'].concat(opcoes(state.config.apelidos, "")).join("");
    } else {
      $("det-sprint-bloco").hidden = true;
    }

    $("modal-detalhes").showModal();
  }

  $("det-fechar").addEventListener("click", () => $("modal-detalhes").close());
  $("det-salvar").addEventListener("click", async () => {
    const r = state.backlog.find((x) => x.id === state.detId);
    const resp = await fetch(`/api/backlog/demanda/${state.detId}/curadoria`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        macroprocesso: $("det-macro").value, sistema: $("det-sist").value,
        score: parseFloat($("det-score").value || "0"),
        score_sugerido: r ? r.score_sugerido : 0, observacoes: $("det-obs").value,
      }),
    });
    if (resp.ok) {
      flash(`Demanda ${state.detId} classificada e salva.`);
      $("modal-detalhes").close();
      carregarBacklog();
    } else {
      flashErro(`Não foi possível salvar a demanda ${state.detId}.`);
    }
  });
  $("det-sprint-enviar").addEventListener("click", async () => {
    const resp = await fetch("/api/backlog/enviar-sprint", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ linhas: [{ id: state.detId, tipo_entrada: state.config.sprint_ativa.em_andamento ? "Paraquedas" : "Planejada", responsavel: $("det-sprint-resp").value }] }),
    });
    const dados = await resp.json();
    if (resp.ok) {
      flash(`✅ Demanda ${state.detId} enviada para ${dados.sprint_nome}.`);
      $("modal-detalhes").close();
      carregarBacklog();
    } else {
      flashErro(dados.erro || "Erro ao enviar.");
    }
  });

  // ── ABA PLANEJAR ─────────────────────────────────────────────────────────
  function renderPlanejar() {
    const tipoPadrao = state.config.sprint_ativa && state.config.sprint_ativa.em_andamento ? "Paraquedas" : "Planejada";
    const tbody = document.querySelector("#tabela-planejar tbody");
    tbody.innerHTML = state.backlog.map((r) => `
      <tr data-id="${r.id}">
        <td><input type="checkbox" class="sel-planejar"></td>
        <td>${r.id}</td>
        <td>${escapeHTML(r.titulo)}</td>
        <td>${r.score_exibicao ?? r.score_sugerido}</td>
        <td data-sort="${tipoPadrao}"><select class="f-tipo-entrada">${opcoes(["Planejada", "Paraquedas", "Interna"], tipoPadrao)}</select></td>
        <td data-sort="${escapeHTML(r.responsavel_apelido)}"><select class="f-responsavel">${['<option value=""></option>'].concat(opcoes(state.config.apelidos, r.responsavel_apelido)).join("")}</select></td>
      </tr>`).join("");
    gpSyncDataSort(tbody);

    tbody.querySelectorAll(".sel-planejar").forEach((cb) => cb.addEventListener("change", atualizarHigienePlanejar));
    atualizarHigienePlanejar();
  }

  function linhasMarcadas() {
    return Array.from(document.querySelectorAll("#tabela-planejar tbody tr")).filter((tr) => tr.querySelector(".sel-planejar").checked);
  }

  function atualizarHigienePlanejar() {
    const marcadas = linhasMarcadas();
    const n = marcadas.length;
    const modo = $("btn-enviar-sprint").dataset.modo;
    $("btn-enviar-sprint").textContent = modo === "criar" ? `➕ Criar sprint e enviar ${n} demanda(s)` : `➕ Enviar ${n} demanda(s) para a sprint`;
    $("btn-enviar-sprint").disabled = n === 0;

    if (n === 0) { $("planejar-higiene").hidden = true; return; }
    const semResp = marcadas.filter((tr) => !tr.querySelector(".f-responsavel").value).length;
    const ids = marcadas.map((tr) => Number(tr.dataset.id));
    const semCur = state.backlog.filter((r) => ids.includes(r.id) && (!r.macroprocesso || !r.sistema)).length;
    const avisos = [];
    if (semResp) avisos.push(`${semResp} sem responsável`);
    if (semCur) avisos.push(`${semCur} sem curadoria`);
    if (avisos.length) {
      $("planejar-higiene").hidden = false;
      $("planejar-higiene").textContent = "⚠️ Higiene: " + avisos.join(" e ") + ". Você ainda pode enviar.";
    } else {
      $("planejar-higiene").hidden = true;
    }
  }

  function linhasParaEnvio() {
    return linhasMarcadas().map((tr) => ({
      id: Number(tr.dataset.id),
      tipo_entrada: tr.querySelector(".f-tipo-entrada").value,
      responsavel: tr.querySelector(".f-responsavel").value,
    }));
  }

  $("btn-enviar-sprint").addEventListener("click", async () => {
    const linhas = linhasParaEnvio();
    if (!linhas.length) return;
    if ($("btn-enviar-sprint").dataset.modo === "criar") {
      $("cs-info").textContent = `${linhas.length} demanda(s) marcada(s) serão movidas para a nova sprint.`;
      state.linhasPendentes = linhas;
      $("modal-criar-sprint").showModal();
      return;
    }
    const resp = await fetch("/api/backlog/enviar-sprint", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ linhas }),
    });
    const dados = await resp.json();
    if (resp.ok) {
      flash(`${dados.enviadas} demanda(s) enviada(s) para a sprint ${dados.sprint_nome}.`);
      carregarBacklog();
    } else {
      flashErro(dados.erro || "Não foi possível enviar as demandas.");
    }
  });

  $("cs-nome").addEventListener("input", (e) => { $("cs-criar").disabled = !e.target.value.trim(); });
  $("cs-cancelar").addEventListener("click", () => $("modal-criar-sprint").close());
  $("cs-criar").addEventListener("click", async () => {
    const resp = await fetch("/api/backlog/criar-sprint-enviar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome: $("cs-nome").value, meta: $("cs-meta").value,
        data_inicio: $("cs-inicio").value || null, data_fim: $("cs-fim").value || null,
        linhas: state.linhasPendentes || [],
      }),
    });
    const dados = await resp.json();
    if (resp.ok) {
      flash(`Sprint '${dados.sprint_nome}' criada com ${dados.enviadas} demanda(s).`);
      $("modal-criar-sprint").close();
      carregarConfig();
      carregarBacklog();
    } else {
      flashErro(dados.erro || "Não foi possível criar a sprint.");
    }
  });

  $("pj-ativ-titulo").addEventListener("input", (e) => { $("pj-ativ-criar").disabled = !e.target.value.trim(); });
  $("pj-ativ-criar").addEventListener("click", async () => {
    const titulo = $("pj-ativ-titulo").value.trim();
    const resp = await fetch("/api/sprint/atividade", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ titulo, responsavel: $("pj-ativ-resp").value, tipo_entrada: $("pj-ativ-tipo").value }),
    });
    if (resp.ok) {
      $("pj-ativ-titulo").value = ""; $("pj-ativ-criar").disabled = true;
      flash(`Atividade '${titulo}' criada na sprint ${state.config.sprint_ativa.nome}.`);
    }
  });

  // ── Inicialização ────────────────────────────────────────────────────────
  (async function init() {
    await carregarConfig();
    await carregarBacklog();
    await carregarUltimaImportacao();
  })();
})();
