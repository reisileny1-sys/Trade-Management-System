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

function destinoAposLogin(usuario) {
  if (usuario.perfil === "admin") return Api.caminho("pages/admin.html");
  const next = new URLSearchParams(location.search).get("next");
  if (next && next.startsWith("/")) return next;
  return Api.caminho("index.html");
}

document.addEventListener("DOMContentLoaded", () => {
  const login = document.getElementById("form-login");
  const cadastro = document.getElementById("form-cadastro");
  const perfil = document.getElementById("form-perfil");
  const botaoAtualizar = document.getElementById("btn-atualizar-conta");
  const sair = document.getElementById("btn-sair");
  const excluirConta = document.getElementById("btn-excluir-conta");

  login?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const msg = document.getElementById("msg-auth");
    try {
      const dados = await Api.post("/login", {
        email: login.email.value,
        senha: login.senha.value,
      });
      Auth.guardar(dados.usuario, dados.token);
      location.href = destinoAposLogin(dados.usuario);
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
    let editandoPerfil = false;
    const modalAtualizacao = document.getElementById("modal-confirmacao-atualizacao");
    const confirmarAtualizacao = document.getElementById("confirmar-atualizacao");
    const cancelarAtualizacao = document.getElementById("cancelar-atualizacao");
    const msgPerfil = document.getElementById("msg-auth");

    function definirEdicaoPerfil(ativa) {
      editandoPerfil = ativa;
      perfil.nome_completo.readOnly = !ativa;
      perfil.cpf.readOnly = true;
      perfil.celular.readOnly = !ativa;
      perfil.email.readOnly = !ativa;
    }

    function fecharModalAtualizacao() {
      modalAtualizacao.classList.remove("aberto");
      botaoAtualizar.focus();
    }

    Api.get("/me")
      .then(({ usuario }) => {
        perfil.nome_completo.value = usuario.nome_completo;
        perfil.cpf.value = usuario.cpf;
        perfil.celular.value = usuario.celular;
        perfil.email.value = usuario.email;
        Auth.guardar(usuario, Api.token());
      })
      .catch((erro) => mostrarMsg(msgPerfil, erro.message, "erro"));

    perfil.addEventListener("submit", (ev) => {
      ev.preventDefault();
      if (!editandoPerfil) {
        definirEdicaoPerfil(true);
        msgPerfil.hidden = true;
        perfil.nome_completo.focus();
        return;
      }
      modalAtualizacao.classList.add("aberto");
      cancelarAtualizacao.focus();
    });

    cancelarAtualizacao.addEventListener("click", fecharModalAtualizacao);
    modalAtualizacao.addEventListener("click", (ev) => {
      if (ev.target === modalAtualizacao && !confirmarAtualizacao.disabled) {
        fecharModalAtualizacao();
      }
    });
    document.addEventListener("keydown", (ev) => {
      if (!modalAtualizacao.classList.contains("aberto")) return;
      if (ev.key === "Escape" && !confirmarAtualizacao.disabled) {
        ev.preventDefault();
        fecharModalAtualizacao();
      } else if (ev.key === "Tab") {
        const focoNoSim = document.activeElement === confirmarAtualizacao;
        const focoNoNao = document.activeElement === cancelarAtualizacao;
        if (ev.shiftKey && focoNoSim) {
          ev.preventDefault();
          cancelarAtualizacao.focus();
        } else if (!ev.shiftKey && focoNoNao) {
          ev.preventDefault();
          confirmarAtualizacao.focus();
        }
      }
    });

    confirmarAtualizacao.addEventListener("click", async () => {
      botaoAtualizar.disabled = true;
      confirmarAtualizacao.disabled = true;
      cancelarAtualizacao.disabled = true;
      try {
        const { usuario } = await Api.put("/me", {
          nome_completo: perfil.nome_completo.value,
          celular: perfil.celular.value,
          email: perfil.email.value,
        });
        Auth.guardar(usuario, Api.token());
        perfil.nome_completo.value = usuario.nome_completo;
        perfil.cpf.value = usuario.cpf;
        perfil.celular.value = usuario.celular;
        perfil.email.value = usuario.email;
        definirEdicaoPerfil(false);
        modalAtualizacao.classList.remove("aberto");
        mostrarMsg(msgPerfil, "Conta atualizada com sucesso.", "ok");
      } catch (erro) {
        modalAtualizacao.classList.remove("aberto");
        mostrarMsg(msgPerfil, erro.message, "erro");
      } finally {
        botaoAtualizar.disabled = false;
        confirmarAtualizacao.disabled = false;
        cancelarAtualizacao.disabled = false;
        botaoAtualizar.focus();
      }
    });

    const modalExclusao = document.getElementById("modal-excluir-conta");
    const confirmarExclusao = document.getElementById("confirmar-excluir-conta");
    const cancelarExclusao = document.getElementById("cancelar-excluir-conta");

    function fecharModalExclusao() {
      modalExclusao.classList.remove("aberto");
      excluirConta.focus();
    }

    excluirConta.addEventListener("click", () => {
      modalExclusao.classList.add("aberto");
      cancelarExclusao.focus();
    });
    cancelarExclusao.addEventListener("click", fecharModalExclusao);
    modalExclusao.addEventListener("click", (ev) => {
      if (ev.target === modalExclusao) fecharModalExclusao();
    });
    document.addEventListener("keydown", (ev) => {
      if (!modalExclusao.classList.contains("aberto")) return;
      if (ev.key === "Escape") {
        ev.preventDefault();
        fecharModalExclusao();
      } else if (ev.key === "Tab") {
        const focoNoSim = document.activeElement === confirmarExclusao;
        const focoNoNao = document.activeElement === cancelarExclusao;
        if (ev.shiftKey && focoNoSim) {
          ev.preventDefault();
          cancelarExclusao.focus();
        } else if (!ev.shiftKey && focoNoNao) {
          ev.preventDefault();
          confirmarExclusao.focus();
        }
      }
    });
    confirmarExclusao.addEventListener("click", async () => {
      confirmarExclusao.disabled = true;
      cancelarExclusao.disabled = true;
      try {
        await Api.del("/me");
      } catch (erro) {
        modalExclusao.classList.remove("aberto");
        mostrarMsg(document.getElementById("msg-auth"), erro.message, "erro");
        confirmarExclusao.disabled = false;
        cancelarExclusao.disabled = false;
        excluirConta.focus();
        return;
      }
      Auth.limpar();
      Carrinho.limpar();
      sessionStorage.removeItem("quitanda_ultimo_pedido");
      sessionStorage.removeItem("quitanda_idem");
      location.href = Api.caminho("index.html");
    });
  }

  sair?.addEventListener("click", () => Auth.sair());
});

