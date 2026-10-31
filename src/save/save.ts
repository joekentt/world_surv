import type { DadosJogo } from "../core/estado";

const BANCO = "vila_cisterna";
const LOJA = "saves";
const SLOT = "slot1";

function abrir(): Promise<IDBDatabase> {
  return new Promise((ok, erro) => {
    const req = indexedDB.open(BANCO, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(LOJA);
    req.onsuccess = () => ok(req.result);
    req.onerror = () => erro(req.error);
  });
}

/** Save em um slot no IndexedDB do navegador. */
export async function salvarJogo(d: DadosJogo): Promise<void> {
  const db = await abrir();
  await new Promise<void>((ok, erro) => {
    const tx = db.transaction(LOJA, "readwrite");
    tx.objectStore(LOJA).put(JSON.parse(JSON.stringify({ ...d, salvoEm: Date.now() })), SLOT);
    tx.oncomplete = () => ok();
    tx.onerror = () => erro(tx.error);
  });
  db.close();
}

export async function carregarJogo(): Promise<DadosJogo | null> {
  try {
    const db = await abrir();
    const d = await new Promise<DadosJogo | null>((ok, erro) => {
      const req = db.transaction(LOJA, "readonly").objectStore(LOJA).get(SLOT);
      req.onsuccess = () => ok((req.result as DadosJogo) ?? null);
      req.onerror = () => erro(req.error);
    });
    db.close();
    return d;
  } catch {
    return null;
  }
}

export async function apagarJogo(): Promise<void> {
  const db = await abrir();
  await new Promise<void>((ok) => {
    const tx = db.transaction(LOJA, "readwrite");
    tx.objectStore(LOJA).delete(SLOT);
    tx.oncomplete = () => ok();
  });
  db.close();
}
