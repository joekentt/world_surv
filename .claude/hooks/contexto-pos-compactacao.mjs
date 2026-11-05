// Hook SessionStart (matcher "compact"): devolve ao contexto o estado do projeto
// depois de cada compactação. O texto impresso no stdout entra no contexto do Claude.
import { readFileSync, existsSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

function ler(caminho) {
  const arquivo = join(raiz, caminho);
  return existsSync(arquivo) ? readFileSync(arquivo, 'utf8') : `(${caminho} não encontrado)`;
}

let commits;
try {
  commits = execSync('git log --oneline -5', { cwd: raiz, encoding: 'utf8' });
} catch {
  commits = '(git log indisponível)\n';
}

process.stdout.write(
  'CONTEXTO RESTAURADO APÓS COMPACTAÇÃO\n\n' +
  '## docs/estado.md\n' + ler('docs/estado.md') + '\n\n' +
  '## Últimos commits\n' + commits + '\n' +
  'Antes de continuar, releia o arquivo de docs/spec/ da tarefa atual e atualize docs/estado.md se houver progresso não registrado.\n'
);
