import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { ArrowLeft, Loader2, ShieldCheck, UserPlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { registerUser } from "@/services/user_registration";
import { useToast } from "@/components/ui/use-toast";

const registrationSchema = z
  .object({
    fullName: z
      .string()
      .trim()
      .min(3, "O nome completo deve ter pelo menos 3 caracteres"),
    email: z
      .string()
      .trim()
      .email("Informe um e-mail valido"),
    password: z
      .string()
      .min(6, "A senha precisa ter pelo menos 6 caracteres"),
    confirmPassword: z
      .string()
      .min(1, "Confirme sua senha"),
    phone: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.password !== data.confirmPassword) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "As senhas nao coincidem",
        path: ["confirmPassword"],
      });
    }

    if (data.phone && data.phone.trim().length > 0) {
      const digitsOnly = data.phone.replace(/\D/g, "");

      if (digitsOnly.length < 10) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Informe um telefone com DDD",
          path: ["phone"],
        });
      }
    }
  });

type RegistrationFormState = z.infer<typeof registrationSchema>;

type FieldErrors = Partial<Record<keyof RegistrationFormState, string>>;

type WebhookPreview = {
  request: string;
  response: string;
};

const Register = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [formState, setFormState] = useState<RegistrationFormState>({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    phone: "",
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [webhookPreview, setWebhookPreview] = useState<WebhookPreview | null>(null);

  const handleChange = (field: keyof RegistrationFormState) => (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;

    setFormState((prev) => ({
      ...prev,
      [field]: value,
    }));

    setErrors((prev) => ({
      ...prev,
      [field]: undefined,
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrors({});

    const result = registrationSchema.safeParse({
      ...formState,
      fullName: formState.fullName.trim(),
      email: formState.email.trim(),
      phone: formState.phone?.trim(),
    });

    if (!result.success) {
      const fieldErrors: FieldErrors = {};

      result.error.issues.forEach((issue) => {
        const fieldKey = issue.path[0] as keyof RegistrationFormState;
        fieldErrors[fieldKey] = issue.message;
      });

      setErrors(fieldErrors);
      return;
    }

    setIsSubmitting(true);

    try {
      const parsedData = result.data;

      const registrationResult = await registerUser({
        fullName: parsedData.fullName,
        email: parsedData.email,
        password: parsedData.password,
        phone: parsedData.phone && parsedData.phone.length > 0 ? parsedData.phone : undefined,
      });

      setWebhookPreview({
        request: JSON.stringify(registrationResult.requestPayload, null, 2),
        response: JSON.stringify(registrationResult.responsePayload, null, 2),
      });

      toast({
        title: "Registro enviado",
        description: `Usuario ${registrationResult.responsePayload.user?.email ?? parsedData.email} cadastrado com sucesso.`,
      });

      setFormState({
        fullName: "",
        email: "",
        password: "",
        confirmPassword: "",
        phone: "",
      });
    } catch (error) {
      console.error("Falha ao registrar usuario", error);

      toast({
        title: "Erro ao registrar",
        description: error instanceof Error ? error.message : "Nao foi possivel cadastrar o usuario. Tente novamente.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasAnyError = useMemo(() => Object.values(errors).some(Boolean), [errors]);

  return (
    <div className="min-h-screen bg-gradient-primary">
      <div className="container mx-auto px-4 py-12">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors duration-200 mb-8"
        >
          <ArrowLeft size={20} />
          <span>Voltar</span>
        </button>

        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-card rounded-full mb-6 shadow-card border border-border/50">
            <UserPlus className="text-tech-blue" size={32} />
          </div>
          <h1 className="text-4xl font-bold text-foreground mb-4">Cadastro de Usuario</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Envie dados estruturados para registrar novos usuarios via webhook integrado ao banco.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-8 max-w-6xl mx-auto">
          <div className="bg-gradient-card rounded-2xl p-8 shadow-card border border-border/50">
            <form onSubmit={handleSubmit} className="space-y-6">
              {hasAnyError && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  Revise os campos destacados para continuar.
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-muted-foreground mb-2" htmlFor="fullName">
                    Nome completo
                  </label>
                  <input
                    id="fullName"
                    type="text"
                    value={formState.fullName}
                    onChange={handleChange("fullName")}
                    placeholder="Ex: Maria Silva"
                    className={`w-full px-4 py-3 rounded-lg border bg-dark-surface text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition ${
                      errors.fullName ? "border-destructive" : "border-border"
                    }`}
                  />
                  {errors.fullName && (
                    <span className="mt-1 block text-sm text-destructive">{errors.fullName}</span>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2" htmlFor="email">
                    E-mail profissional
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={formState.email}
                    onChange={handleChange("email")}
                    placeholder="contato@empresa.com"
                    className={`w-full px-4 py-3 rounded-lg border bg-dark-surface text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition ${
                      errors.email ? "border-destructive" : "border-border"
                    }`}
                  />
                  {errors.email && (
                    <span className="mt-1 block text-sm text-destructive">{errors.email}</span>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2" htmlFor="phone">
                    Telefone (opcional)
                  </label>
                  <input
                    id="phone"
                    type="tel"
                    value={formState.phone ?? ""}
                    onChange={handleChange("phone")}
                    placeholder="(11) 99999-0000"
                    className={`w-full px-4 py-3 rounded-lg border bg-dark-surface text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition ${
                      errors.phone ? "border-destructive" : "border-border"
                    }`}
                  />
                  {errors.phone && (
                    <span className="mt-1 block text-sm text-destructive">{errors.phone}</span>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2" htmlFor="password">
                    Senha
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={formState.password}
                    onChange={handleChange("password")}
                    placeholder="Minimo 6 caracteres"
                    className={`w-full px-4 py-3 rounded-lg border bg-dark-surface text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition ${
                      errors.password ? "border-destructive" : "border-border"
                    }`}
                  />
                  {errors.password && (
                    <span className="mt-1 block text-sm text-destructive">{errors.password}</span>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2" htmlFor="confirmPassword">
                    Confirmar senha
                  </label>
                  <input
                    id="confirmPassword"
                    type="password"
                    value={formState.confirmPassword}
                    onChange={handleChange("confirmPassword")}
                    placeholder="Repita a senha"
                    className={`w-full px-4 py-3 rounded-lg border bg-dark-surface text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition ${
                      errors.confirmPassword ? "border-destructive" : "border-border"
                    }`}
                  />
                  {errors.confirmPassword && (
                    <span className="mt-1 block text-sm text-destructive">{errors.confirmPassword}</span>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex items-center justify-center space-x-2 px-6 py-3 rounded-lg bg-gradient-accent text-primary-foreground font-semibold shadow-card hover:shadow-hover transition duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="animate-spin" size={20} />
                    <span>Enviando...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck size={20} />
                    <span>Registrar usuario</span>
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="space-y-6">
            <div className="bg-gradient-card rounded-2xl p-6 shadow-card border border-border/50">
              <h2 className="text-lg font-semibold text-foreground mb-2">Fluxo de integracao</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Os dados preenchidos sao enviados diretamente ao backend, que faz o hash da senha e persiste o cadastro no banco via SQLAlchemy, respondendo com um status estruturado.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-tech-blue rounded-full" />
                  <span>Endpoint: <strong>POST /register_user</strong></span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-tech-blue rounded-full" />
                  <span>Formato consistente e rastreavel</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-tech-blue rounded-full" />
                  <span>Resposta do backend exibida abaixo</span>
                </li>
              </ul>
            </div>

            {webhookPreview && (
              <div className="bg-dark-surface/60 backdrop-blur rounded-2xl p-6 border border-border/40 shadow-card space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Payload enviado
                  </h3>
                  <pre className="max-h-60 overflow-auto rounded-xl bg-black/40 p-4 text-xs text-foreground/80">
{webhookPreview.request}
                  </pre>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Resposta recebida
                  </h3>
                  <pre className="max-h-60 overflow-auto rounded-xl bg-black/40 p-4 text-xs text-foreground/80">
{webhookPreview.response}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
