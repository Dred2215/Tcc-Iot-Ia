import { BACKEND_BASE_URL } from "./backend_config"; // importa a URL base do backend FastAPI, já normalizada

export interface RegisterUserInput { // define os dados que o frontend precisa para registrar um usuário
  fullName: string; // nome completo digitado pelo usuário no formulário
  email: string; // e-mail usado para login e identificação
  password: string; // senha definida pelo usuário
  phone?: string; // telefone é opcional no cadastro
}

export interface RegisterBackendPayload { // formato exato do JSON esperado pelo endpoint /register_user do backend
  full_name: string; // nome completo no formato esperado pelo backend
  email: string; // e-mail do usuário
  password: string; // senha em texto plano; o backend faz o hash (bcrypt) antes de persistir
  phone?: string | null; // telefone pode ser string ou null se não informado
}

export interface RegisterBackendUser { // usuário criado, devolvido pelo backend
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  type: string;
}

export interface RegisterBackendResponse { // formato de resposta do endpoint /register_user
  status: "success" | "error" | string; // status principal da operação
  user?: RegisterBackendUser; // usuário criado, quando sucesso
  detail?: string; // mensagem de erro do backend (ex: e-mail já cadastrado)
}

export interface RegisterUserResult { // descreve o retorno da função registerUser no frontend
  requestPayload: RegisterBackendPayload; // payload que foi enviado ao backend (útil para log/debug)
  responsePayload: RegisterBackendResponse; // resposta recebida do backend após o cadastro
}

// Endpoint de cadastro de usuário no backend FastAPI (dono da persistência via SQLAlchemy).
export const REGISTER_USER_URL = `${BACKEND_BASE_URL}/register_user`; // monta a URL completa do endpoint de cadastro no backend

// Função responsável por montar o payload no formato exato que o backend espera.
export const buildRegisterPayload = (input: RegisterUserInput): RegisterBackendPayload => ({ // cria o objeto a partir dos dados do formulário
  full_name: input.fullName, // mapeia o campo fullName do formulário para full_name do payload
  email: input.email, // mapeia o e-mail informando pelo usuário
  password: input.password, // envia a senha digitada pelo usuário
  phone: input.phone ?? null, // se phone for undefined, salva como null (padrão explícito)
});

// Função que realmente faz a chamada HTTP para o endpoint de cadastro de usuário no backend.
export async function registerUser(input: RegisterUserInput): Promise<RegisterUserResult> { // define função assíncrona que retorna o resultado do cadastro
  const requestPayload = buildRegisterPayload(input); // monta o payload com base nos dados do formulário

  const response = await fetch(REGISTER_USER_URL, { // faz a requisição POST para o endpoint de cadastro no backend
    method: "POST", // método HTTP POST pois estamos enviando dados para criação
    headers: {
      "Content-Type": "application/json", // indica que o corpo da requisição está em JSON
    },
    body: JSON.stringify(requestPayload), // converte o payload em string JSON para envio na requisição
  });

  // tenta interpretar a resposta como JSON, mesmo em caso de erro (o backend devolve {detail} em 4xx/5xx)
  const responsePayload = (await response
    .json()
    .catch(() => ({ status: "error", detail: "Resposta JSON invalida" }))) as RegisterBackendResponse;

  if (!response.ok) { // verifica se o status HTTP NÃO está na faixa 200–299
    // usa a mensagem estruturada do backend (detail) quando disponível
    throw new Error(responsePayload.detail || `Falha ao registrar usuario: ${response.status} ${response.statusText}`.trim()); // lança erro para ser tratado pelo chamador
  }

  return {
    requestPayload, // devolve o payload enviado (útil para logs ou exibir em tela de debug)
    responsePayload, // devolve a resposta que veio do backend após processar o cadastro
  };
}
