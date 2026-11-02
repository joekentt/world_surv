import { CFG } from "../config";

/** Opções de câmera escolhidas pelo jogador (seção 3.2), guardadas no navegador. */
export interface OpcoesCamera {
  sensibilidade: number;
  inverterY: boolean;
  recentralizar: boolean;
  atrasoRecentralizar: number;
}

const CHAVE = "vila_cisterna_opcoes_camera";

export function opcoesPadrao(): OpcoesCamera {
  return {
    sensibilidade: 1,
    inverterY: CFG.camera.inverterY,
    recentralizar: CFG.camera.recentralizar,
    atrasoRecentralizar: CFG.camera.atrasoRecentralizar,
  };
}

export function carregarOpcoes(): OpcoesCamera {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (bruto) return { ...opcoesPadrao(), ...JSON.parse(bruto) };
  } catch {
    // armazenamento indisponível (janela privada, previews): usa o padrão
  }
  return opcoesPadrao();
}

export function salvarOpcoes(o: OpcoesCamera): void {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(o));
  } catch {
    // sem armazenamento, as opções valem só nesta sessão
  }
}
