(function () {
  const form = document.getElementById("form-login");
  const erro = document.getElementById("erro");

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    erro.textContent = "";
    const usuario = document.getElementById("usuario").value;
    const senha = document.getElementById("senha").value;

    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, senha }),
    });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      window.location.href = "/kanban";
    } else {
      erro.textContent = dados.erro || "Usuário ou senha incorretos.";
    }
  });
})();
