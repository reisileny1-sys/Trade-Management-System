const Api = (() => {
  const raiz = document.body?.dataset.root || "";
  const base = `${location.origin}/api`;

  function token() {
    return sessionStorage.getItem("quitanda_token") || "";
  }

  async function pedir(caminho, opcoes = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, opcoes.headers || {});
    const atual = token();
    if (atual) headers.Authorization = `Bearer ${atual}`;
    let resposta;
    try {
      resposta = await fetch(base + caminho, Object.assign({}, opcoes, { headers }));
    } catch (erro) {
      throw new Error("Não foi possível conectar à API. Inicie o servidor Python.");
    }
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      throw new Error(dados.erro || "Falha na comunicação com o servidor.");
    }
    return dados;
  }

  return {
    raiz,
    caminho(caminho) {
      return `${raiz || "."}/${caminho}`;
    },
    token,
    get: (c) => pedir(c),
    post: (c, corpo) => pedir(c, { method: "POST", body: JSON.stringify(corpo || {}) }),
    put: (c, corpo) => pedir(c, { method: "PUT", body: JSON.stringify(corpo || {}) }),
    patch: (c, corpo) => pedir(c, { method: "PATCH", body: JSON.stringify(corpo || {}) }),
    del: (c) => pedir(c, { method: "DELETE" }),
    imagem(nome) {
      if (!nome) return `${raiz || "."}/assets/imagens/cesta.svg`;
      if (nome.startsWith("http")) return nome;
      return `${raiz || "."}/assets/imagens/${nome}`;
    },
    dinheiro(valor) {
      return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    },
    data(iso) {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleString("pt-BR");
    },
  };
})();
