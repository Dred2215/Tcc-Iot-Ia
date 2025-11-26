const DEFAULT_WEBHOOK_MESSAGE_CHAT_RESPONSE = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook/message_input";

type EnvRecord = Record<string, unknown>;

const RUNTIME_ENV_KEYS = ["__ENV__", "__env__", "__APP_ENV__", "__app_env__"] as const;

const asRecord = (value: unknown): EnvRecord | undefined =>
  value && typeof value === "object" ? (value as EnvRecord) : undefined;

const getImportMetaEnv = (): EnvRecord | undefined => {
  try {
    return asRecord((import.meta as ImportMeta).env);
  } catch {
    return undefined;
  }
};

const getGlobalObject = (): EnvRecord | undefined => {
  if (typeof globalThis === "object" && globalThis) {
    return globalThis as unknown as EnvRecord;
  }
  return undefined;
};

const getProcessEnv = (globalObj: EnvRecord | undefined): EnvRecord | undefined => {
  if (!globalObj) return undefined;
  const processLike = asRecord(globalObj.process);
  const env = processLike && "env" in processLike ? asRecord((processLike as EnvRecord).env) : undefined;
  return env;
};

const collectEnvSources = (): EnvRecord[] => {
  const sources: EnvRecord[] = [];

  const metaEnv = getImportMetaEnv();
  if (metaEnv) {
    sources.push(metaEnv);
  }

  const globalObj = getGlobalObject();
  if (globalObj) {
    sources.push(globalObj);

    for (const key of RUNTIME_ENV_KEYS) {
      const runtimeEnv = asRecord(globalObj[key]);
      if (runtimeEnv) {
        sources.push(runtimeEnv);
      }
    }

    const processEnv = getProcessEnv(globalObj);
    if (processEnv) {
      sources.push(processEnv);
    }
  }

  return sources;
};

const pickEnvValue = (keys: string[]): string | undefined => {
  const sources = collectEnvSources();
  for (const key of keys) {
    for (const source of sources) {
      const rawValue = source[key];
      if (typeof rawValue === "string") {
        const trimmed = rawValue.trim();
        if (trimmed.length > 0) {
          return trimmed;
        }
      }
    }
  }
  return undefined;
};

export const getChatWebhookUrl = (): string => {
  const resolved = pickEnvValue([
    "VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE",
    "WEBHOOK_MESSAGE_CHAT_RESPONSE",
  ]);

  if (!resolved) {
    console.warn(
      "[Env] VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE/WEBHOOK_MESSAGE_CHAT_RESPONSE não configurado. Usando fallback padrão."
    );
    return DEFAULT_WEBHOOK_MESSAGE_CHAT_RESPONSE;
  }

  return resolved;
};

export { DEFAULT_WEBHOOK_MESSAGE_CHAT_RESPONSE };
