#!/usr/bin/env bash
# Regenera todos os assets do jogo a partir dos scripts (nenhum é modelado à mão).
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PY="${BPY_PYTHON:-/opt/bpyenv/bin/python}"
cd "$RAIZ"
bash tools/blender/personagens/baixar_dados_mpfb2.sh
"$PY" tools/blender/kits/parede_teste.py
"$PY" tools/blender/kits/gerar_kits.py
"$PY" tools/blender/personagens/gerar_personagem.py --todos
"$PY" tools/blender/animacoes/gerar_animacoes.py
python3 tools/areas/gerar_areas.py
"$PY" tools/audio/gerar_sons.py
bash tools/comprimir_assets.sh
