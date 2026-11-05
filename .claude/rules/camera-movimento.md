---
paths:
  - "src/camera/**"
  - "src/player/**"
---

# Câmera e movimento

Especificação completa: `docs/spec/03-camera-movimento.md`. Leia antes de mudar qualquer comportamento.

Invariantes que não podem regredir:

- Câmera livre em terceira pessoa, sem travamento em plano. O mouse (ou analógico direito) tem prioridade sobre qualquer ajuste automático.
- Movimento relativo à câmera: W leva o personagem para onde a câmera aponta.
- Personagem andando com o mouse parado por 0,8 s: a câmera volta gradualmente para as costas do personagem.
- Exceção: se o personagem anda em direção à câmera (ângulo acima de 135°), a câmera só recentraliza depois de 1,5 s na mesma direção.
- Personagem parado e mouse parado: a câmera não se move.
- Colisão por esfera: a câmera nunca entra na geometria.
- Todo valor numérico vem de `src/config.ts`.
- Os seis testes da seção 3.4 (`tests/fase1.spec.ts`) continuam passando depois de qualquer mudança aqui.
