#!/usr/bin/env bash
# Fase 7: comprime todos os GLB de public/assets com meshoptimizer (EXT_meshopt_compression +
# quantização) e converte o áudio para OGG Vorbis. Rodar depois de gerar os assets.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
antes=$(du -sb public/assets | cut -f1)
for glb in public/assets/kits/*.glb public/assets/personagens/*.glb public/assets/teste/*.glb; do
  npx gltf-transform optimize "$glb" "${glb%.glb}.tmp.glb" --compress meshopt --texture-compress false \
    --simplify false --instance false --join false --flatten false --palette false --prune false > /dev/null
  mv "${glb%.glb}.tmp.glb" "$glb"
done
if ls public/assets/audio/*.wav > /dev/null 2>&1; then
  /opt/bpyenv/bin/python tools/audio/converter_ogg.py
fi
depois=$(du -sb public/assets | cut -f1)
echo "assets: $((antes / 1024 / 1024)) MB -> $((depois / 1024 / 1024)) MB"
