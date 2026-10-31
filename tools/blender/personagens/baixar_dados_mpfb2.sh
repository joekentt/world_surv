#!/usr/bin/env bash
# Baixa apenas os DADOS do MPFB2 (malha base HM08, targets, rigs e pesos), que são CC0.
# O código do MPFB2 (GPL) não é executado nem incorporado: o gerador próprio em
# gerar_personagem.py lê esses arquivos diretamente. Ver docs/progresso.md, fase 0.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/../../.." && pwd)"
DESTINO="$RAIZ/.cache/mpfb2_data"
COMMIT="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
if [ -f "$DESTINO/.commit" ] && [ "$(cat "$DESTINO/.commit")" = "$COMMIT" ]; then
  echo "dados do MPFB2 já presentes em $DESTINO"; exit 0
fi
TMP="$(mktemp -d)"
git clone --filter=blob:none --no-checkout https://github.com/makehumancommunity/mpfb2 "$TMP/mpfb2"
git -C "$TMP/mpfb2" sparse-checkout set --no-cone \
  src/mpfb/data/3dobjs src/mpfb/data/targets src/mpfb/data/rigs/standard \
  src/mpfb/data/mesh_metadata LICENSE.ASSETS.md
git -C "$TMP/mpfb2" checkout "$COMMIT"
rm -rf "$DESTINO"; mkdir -p "$DESTINO"
cp -r "$TMP/mpfb2/src/mpfb/data/"{3dobjs,targets,mesh_metadata} "$DESTINO/"
mkdir -p "$DESTINO/rigs"; cp -r "$TMP/mpfb2/src/mpfb/data/rigs/standard" "$DESTINO/rigs/"
cp "$TMP/mpfb2/LICENSE.ASSETS.md" "$DESTINO/"
echo "$COMMIT" > "$DESTINO/.commit"
rm -rf "$TMP"
echo "dados do MPFB2 copiados para $DESTINO"
