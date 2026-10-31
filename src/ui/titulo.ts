import { UI } from "./textos";

/** Tela de título: novo jogo ou continuar do save. */
export function mostrarTitulo(temSave: boolean): Promise<"novo" | "continuar"> {
  const el = document.createElement("div");
  el.className = "titulo interativo";
  el.innerHTML = `<h1>${UI.titulo}</h1><p class="sub">${UI.subtitulo}</p>
    <div class="botoes">${temSave ? `<button data-v="continuar">${UI.continuar}</button>` : ""}<button data-v="novo">${UI.novoJogo}</button></div>
    <p class="controles">${UI.controles}<br>${UI.controlesGamepad}</p>`;
  document.getElementById("ui")!.appendChild(el);
  const botoes = [...el.querySelectorAll("button")];
  let sel = 0;
  botoes[0]?.focus();
  return new Promise((ok) => {
    const escolher = (v: string) => {
      window.removeEventListener("keydown", teclado);
      el.classList.add("saindo");
      setTimeout(() => el.remove(), 600);
      ok(v as "novo" | "continuar");
    };
    const teclado = (e: KeyboardEvent) => {
      if (["ArrowDown", "ArrowUp", "KeyW", "KeyS"].includes(e.code)) {
        sel = (sel + 1) % botoes.length;
        botoes[sel].focus();
      }
      if (["Enter", "Space", "KeyE"].includes(e.code)) escolher(botoes[sel].dataset.v!);
    };
    window.addEventListener("keydown", teclado);
    el.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest("button");
      if (b) escolher(b.dataset.v!);
    });
    const pad = setInterval(() => {
      const gp = navigator.getGamepads?.()[0];
      if (gp?.buttons[0]?.pressed) {
        clearInterval(pad);
        escolher(botoes[sel].dataset.v!);
      }
    }, 100);
  });
}
