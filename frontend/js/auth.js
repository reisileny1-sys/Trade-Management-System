const Auth = {
  usuario() {
    const bruto = sessionStorage.getItem("quitanda_usuario");
    if (!bruto) return null;
    try {
      return JSON.parse(bruto);
    } catch (_e) {
      this.limpar();
      return null;
    }
  },
  guardar(usuario, token) {
    sessionStorage.setItem("quitanda_usuario", JSON.stringify(usuario));
    sessionStorage.setItem("quitanda_token", token);
  },
  limpar() {
    sessionStorage.removeItem("quitanda_usuario");
    sessionStorage.removeItem("quitanda_token");
  },
  async sair() {
    try {
      await Api.post("/logout", {});
    } catch (_e) {
      /* sessão local ainda deve ser encerrada */
    }
    this.limpar();
    location.href = Api.caminho("index.html");
  },
  exigir(proxima) {
    if (this.usuario()) return true;
    const destino = encodeURIComponent(proxima || location.pathname);
    location.href = `${Api.caminho("pages/login.html")}?next=${destino}`;
    return false;
  },
};

function destinoAposLogin() {
  const next = new URLSearchParams(location.search).get("next");
  if (next && next.startsWith("/")) return next;
  return Api.caminho("index.html");
}

document.addEventListener("DOMContentLoaded", () => {
  const login = document.getElementById("form-login");
  const cadastro = document.getElementById("form-cadastro");
  const perfil = document.getElementById("form-perfil");
  const sair = document.getElementById("btn-sair");

  login?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const msg = document.getElementById("msg-auth");
    try {
      const dados = await Api.post("/login", {
        email: login.email.value,
        senha: login.senha.value,
      });
      Auth.guardar(dados.usuario, dados.token);
      location.href = destinoAposLogin();
    } catch (erro) {
      mostrarMsg(msg, erro.message, "erro");
    }
  });

  cadastro?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const msg = document.getElementById("msg-auth");
    const corpo = {
      nome_completo: cadastro.nome_completo.value,
      cpf: cadastro.cpf.value,
      celular: cadastro.celular.value,
      email: cadastro.email.value,
      senha: cadastro.senha.value,
      confirmacao_senha: cadastro.confirmacao_senha.value,
    };
    if (!cpfValido(corpo.cpf)) {
      mostrarMsg(msg, "CPF inválido.", "erro");
      return;
    }
    if (corpo.senha !== corpo.confirmacao_senha) {
      mostrarMsg(msg, "As senhas não coincidem.", "erro");
      return;
    }
    try {
      const dados = await Api.post("/usuarios", corpo);
      Auth.guardar(dados.usuario, dados.token);
      location.href = Api.caminho("index.html");
    } catch (erro) {
      mostrarMsg(msg, erro.message, "erro");
    }
  });

  if (perfil) {
    if (!Auth.exigir(location.pathname)) return;
    Api.get("/me")
      .then(({ usuario }) => {
        perfil.nome_completo.value = usuario.nome_completo;
        perfil.cpf.value = usuario.cpf;
        perfil.celular.value = usuario.celular;
        perfil.email.value = usuario.email;
        Auth.guardar(usuario, Api.token());
      })
      .catch((erro) => mostrarMsg(document.getElementById("msg-auth"), erro.message, "erro"));
    perfil.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      try {
        const { usuario } = await Api.put("/me", {
          nome_completo: perfil.nome_completo.value,
          celular: perfil.celular.value,
          email: perfil.email.value,
        });
        Auth.guardar(usuario, Api.token());
        mostrarMsg(document.getElementById("msg-auth"), "Perfil atualizado.", "ok");
      } catch (erro) {
        mostrarMsg(document.getElementById("msg-auth"), erro.message, "erro");
      }
    });
  }

  sair?.addEventListener("click", () => Auth.sair());
});

