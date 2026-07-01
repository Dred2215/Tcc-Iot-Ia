import { BACKEND_BASE_URL } from "./backend_config"; // URL base do backend FastAPI, ja normalizada

// O backend faz o proxy para o webhook de status do n8n (fachada unica, sem chamada direta do frontend ao n8n).
const STATUS_CHECK_URL = `${BACKEND_BASE_URL}/status_check`;

// Resultado normalizado da consulta de status, pensado para exibicao clara em tela.
export interface StatusCheckResult {
  ok: boolean; // true se o HTTP status estiver na faixa 2xx
  status: number; // codigo HTTP retornado (ex: 200, 404, 500)
  statusText: string; // texto do status HTTP (ex: "OK", "Not Found")
  url: string; // URL efetivamente chamada (util para validar env/dominio em tela)
  bodyText: string; // corpo bruto da resposta como texto (fallback sempre disponivel)
  parsed?: unknown; // corpo interpretado como JSON quando possivel; undefined se nao for JSON
}

// Consulta o webhook de status de producao e devolve um resultado legivel para diagnostico.
// Nao lanca em erro HTTP: retorna ok=false para a UI decidir como exibir (sucesso vs erro).
export async function checkStatus(): Promise<StatusCheckResult> {
  const response = await fetch(STATUS_CHECK_URL, {
    method: "GET", // sonda simples de status, sem corpo
    headers: {
      Accept: "application/json, text/plain, */*", // aceita JSON ou texto puro
    },
  });

  // Le como texto primeiro: garante que sempre teremos algo para mostrar,
  // mesmo quando a resposta nao for JSON valido.
  const bodyText = await response.text().catch(() => "");

  let parsed: unknown; // tenta interpretar como JSON apenas para exibicao formatada
  if (bodyText) {
    try {
      parsed = JSON.parse(bodyText);
    } catch {
      parsed = undefined; // corpo nao e JSON; mantemos apenas o texto bruto
    }
  }

  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    url: STATUS_CHECK_URL,
    bodyText,
    parsed,
  };
}

// Formata o resultado da sonda de status em um texto legivel para o bloco <pre> na UI.
export function formatStatusResult(result: StatusCheckResult): string {
  const header = `GET ${result.url}\nHTTP ${result.status} ${result.statusText}`.trim();
  // Prefere a versao JSON identada quando disponivel; caso contrario mostra o texto bruto.
  const body =
    result.parsed !== undefined
      ? JSON.stringify(result.parsed, null, 2)
      : result.bodyText || "(resposta vazia)";

  return `${header}\n\n${body}`;
}
