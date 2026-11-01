export type Acao =
  | "esquerda" | "direita" | "cima" | "baixo" | "pular" | "correr" | "agachar"
  | "interagir" | "inventario" | "diario" | "menu" | "confirmar";

const TECLAS: Record<string, Acao[]> = {
  KeyA: ["esquerda"], ArrowLeft: ["esquerda"], KeyD: ["direita"], ArrowRight: ["direita"],
  KeyW: ["cima"], ArrowUp: ["cima"], KeyS: ["baixo"], ArrowDown: ["baixo"],
  Space: ["pular", "confirmar"], ShiftLeft: ["correr"], ShiftRight: ["correr"],
  ControlLeft: ["agachar"], KeyC: ["agachar"], KeyE: ["interagir"], Enter: ["confirmar", "interagir"],
  KeyI: ["inventario"], Tab: ["inventario"], KeyJ: ["diario"], Escape: ["menu"],
};

// Mapeamento "standard" do Gamepad API: 0 A, 1 B, 2 X, 3 Y, 4 LB, 5 RB, 6 LT, 7 RT, 8 Back, 9 Start, 12-15 direcional.
const BOTOES: Record<number, Acao[]> = {
  0: ["pular", "confirmar"], 1: ["agachar"], 2: ["interagir"], 3: ["inventario"],
  5: ["correr"], 7: ["correr"], 8: ["diario"], 9: ["menu"],
  12: ["cima"], 13: ["baixo"], 14: ["esquerda"], 15: ["direita"],
};

/** Entrada unificada de teclado e gamepad, lida uma vez por quadro. */
export class Entrada {
  private teclas = new Set<string>();
  /** Teclas apertadas desde o último quadro: um toque curto conta mesmo se for solto antes do quadro. */
  private tocadas = new Set<string>();
  private atual = new Set<Acao>();
  private anterior = new Set<Acao>();
  /** Eixo horizontal analógico (-1 a 1). */
  eixoX = 0;
  eixoY = 0;
  usandoGamepad = false;
  bloqueada = false;

  constructor(alvo: Window = window) {
    alvo.addEventListener("keydown", (e) => {
      if (TECLAS[e.code]) e.preventDefault();
      this.teclas.add(e.code);
      if (!e.repeat) this.tocadas.add(e.code);
      this.usandoGamepad = false;
    });
    alvo.addEventListener("keyup", (e) => this.teclas.delete(e.code));
    alvo.addEventListener("blur", () => this.teclas.clear());
  }

  /** Chamado no início de cada quadro. */
  atualizar(): void {
    this.anterior = this.atual;
    this.atual = new Set();
    for (const t of this.teclas) for (const a of TECLAS[t] ?? []) this.atual.add(a);
    for (const t of this.tocadas) for (const a of TECLAS[t] ?? []) this.atual.add(a);
    this.tocadas.clear();
    let ex = (this.atual.has("direita") ? 1 : 0) - (this.atual.has("esquerda") ? 1 : 0);
    let ey = (this.atual.has("cima") ? 1 : 0) - (this.atual.has("baixo") ? 1 : 0);
    const pads = typeof navigator.getGamepads === "function" ? navigator.getGamepads() : [];
    for (const gp of pads) {
      if (!gp) continue;
      gp.buttons.forEach((b, i) => {
        if (b.pressed) {
          for (const a of BOTOES[i] ?? []) this.atual.add(a);
          this.usandoGamepad = true;
        }
      });
      const ax = gp.axes[0] ?? 0;
      const ay = -(gp.axes[1] ?? 0);
      if (Math.abs(ax) > 0.2) { ex = ax; this.usandoGamepad = true; }
      if (Math.abs(ay) > 0.35) { ey = ay; this.usandoGamepad = true; }
      if ((gp.buttons[7]?.value ?? 0) > 0.4) this.atual.add("correr");
    }
    if (ex < -0.2) this.atual.add("esquerda");
    if (ex > 0.2) this.atual.add("direita");
    if (ey > 0.35) this.atual.add("cima");
    if (ey < -0.35) this.atual.add("baixo");
    this.eixoX = ex;
    this.eixoY = ey;
  }

  segurando(a: Acao): boolean {
    return !this.bloqueada && this.atual.has(a);
  }

  apertou(a: Acao): boolean {
    return !this.bloqueada && this.atual.has(a) && !this.anterior.has(a);
  }

  /** Igual a apertou(), mas funciona mesmo com a entrada de jogo bloqueada (menus, diálogos). */
  apertouUI(a: Acao): boolean {
    return this.atual.has(a) && !this.anterior.has(a);
  }

  soltou(a: Acao): boolean {
    return !this.atual.has(a) && this.anterior.has(a);
  }

  /** Simulação de teclas para testes automatizados. */
  simular(codigo: string, pressionada: boolean): void {
    if (pressionada) {
      this.teclas.add(codigo);
      this.tocadas.add(codigo);
    }
    else this.teclas.delete(codigo);
  }
}
