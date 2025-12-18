import { WEBHOOK_BASE_URL } from "./backend_config"; // importa a URL base do webhook do n8n já normalizada e validada

export interface RegisterUserInput { // define os dados que o frontend precisa para registrar um usuário
  fullName: string; // nome completo digitado pelo usuário no formulário
  email: string; // e-mail usado para login e identificação
  password: string; // senha definida pelo usuário
  phone?: string; // telefone é opcional no cadastro
}

export interface RegisterWebhookPayload { // define o formato exato do JSON que será enviado ao webhook do n8n
  event: "user_registration"; // tipo de evento fixo, útil para o fluxo no n8n
  timestamp: string; // momento da requisição em formato ISO (para log e auditoria)
  user: { // bloco com os dados públicos do usuário
    full_name: string; // nome completo no formato esperado pelo backend/n8n
    email: string; // e-mail do usuário
    phone?: string | null; // telefone pode ser string ou null se não informado
  };
  credentials: { // bloco separado para credenciais (boa prática de organização)
    password: string; // senha do usuário
  };
  meta: { // bloco para metadados da requisição
    source: string; // identifica de onde veio a requisição (nome do sistema/frontend)
    version: string; // versão atual do frontend, útil para depuração
  };
}

export interface RegisterWebhookResponse { // descreve como esperamos que o webhook responda
  status: "success" | "error" | string; // status principal da operação
  message?: string; // mensagem descritiva opcional (erro ou sucesso)
  userId?: string; // opcional: id do usuário criado, se o backend retornar
  data?: unknown; // campo genérico para dados extras retornados pelo webhook
}

export interface RegisterUserResult { // descreve o retorno da função registerUser no frontend
  requestPayload: RegisterWebhookPayload; // payload que foi enviado ao webhook (útil para log/debug)
  responsePayload: RegisterWebhookResponse; // resposta recebida do webhook após o cadastro
}

// Aqui usamos diretamente a base do webhook + rota fixa.
// WEBHOOK_BASE_URL já está normalizada (sem "/" no final) lá no backend_config.
export const REGISTER_WEBHOOK_URL = `${WEBHOOK_BASE_URL}/register-user`; // monta a URL completa do endpoint de cadastro de usuário no n8n

// Função responsável por montar o payload no formato exato que o webhook espera.
export const buildRegisterPayload = (input: RegisterUserInput): RegisterWebhookPayload => ({ // cria o objeto a partir dos dados do formulário
  event: "user_registration", // identifica o tipo de evento para o fluxo do n8n
  timestamp: new Date().toISOString(), // registra o momento da requisição em formato padrão ISO
  user: {
    full_name: input.fullName, // mapeia o campo fullName do formulário para full_name do payload
    email: input.email, // mapeia o e-mail informando pelo usuário
    phone: input.phone ?? null, // se phone for undefined, salva como null (padrão explícito)
  },
  credentials: {
    password: input.password, // envia a senha digitada pelo usuário
  },
  meta: {
    source: "zenith-house-frontend", // identifica que esta requisição veio do frontend Zenith House
    version: "1.0.0", // versão do frontend, você pode atualizar conforme o projeto evolui
  },
});

// Função que realmente faz a chamada HTTP para o webhook de registro de usuário.
export async function registerUser(input: RegisterUserInput): Promise<RegisterUserResult> { // define função assíncrona que retorna o resultado do cadastro
  const requestPayload = buildRegisterPayload(input); // monta o payload com base nos dados do formulário

  const response = await fetch(REGISTER_WEBHOOK_URL, { // faz a requisição POST para o endpoint de cadastro no n8n
    method: "POST", // método HTTP POST pois estamos enviando dados para criação
    headers: {
      "Content-Type": "application/json", // indica que o corpo da requisição está em JSON
    },
    body: JSON.stringify(requestPayload), // converte o payload em string JSON para envio na requisição
  });

  if (!response.ok) { // verifica se o status HTTP NÃO está na faixa 200–299
    const errorText = await response.text().catch(() => ""); // tenta ler o corpo da resposta como texto para detalhar o erro
    // monta uma mensagem de erro com código HTTP, texto padrão e, se existir, detalhe adicional do backend
    throw new Error(`Falha ao registrar usuario: ${response.status} ${response.statusText} ${errorText}`.trim()); // lança erro para ser tratado pelo chamador
  }

  // tenta interpretar a resposta como JSON no formato esperado
  const responsePayload = (await response
    .json()
    .catch(() => ({ status: "error", message: "Resposta JSON invalida" }))) as RegisterWebhookResponse; // em caso de falha no .json(), assume um objeto de erro padrão

  return {
    requestPayload, // devolve o payload enviado (útil para logs ou exibir em tela de debug)
    responsePayload, // devolve a resposta que veio do n8n/backend após processar o cadastro
  };
}
