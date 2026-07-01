import { ButtonCard } from "@/components/ButtonCard";
import { Activity, Keyboard, Loader2, Mic, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { checkAuth } from "@/services/auth_user";
import { checkStatus, formatStatusResult } from "@/services/status_check";

type StatusState = "idle" | "loading" | "success" | "error";





const Home = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [userType, setUserType] = useState<string | undefined>(undefined);
  const [statusState, setStatusState] = useState<StatusState>("idle");
  const [statusResult, setStatusResult] = useState<string | null>(null);

  useEffect(() => {
    const hasRefreshed = sessionStorage.getItem("home_refreshed");
    if (!hasRefreshed) {
      sessionStorage.setItem("home_refreshed", "true");
      window.location.reload();
    }
  }, []);

  useEffect(() => {
    (async () => {
      const result = await checkAuth();

      if (result.status === "error") {
        console.warn("[Home Auth ❌] Sessão inválida, redirecionando...");
        navigate("/login");
      } else {
        // 🔍 Captura o usuário corretamente, mesmo se vier dentro de data.data
        const userData =
          result.user ||
          result.data?.user ||
          result.data?.data?.user ||
          null;

        const resolvedType =
          result.type ||
          result.data?.type ||
          result.data?.data?.type;

        setUserType(resolvedType);

        if (userData) {
          console.log(
            `%c[Home Auth ✅] Usuário autenticado: ${userData.email}`,
            "color: #00ff99; font-weight: bold;"
          );
        } else {
          console.log(
            "%c[Home Auth ⚠️] Sessão válida, mas sem dados de usuário retornados.",
            "color: #ffaa00; font-weight: bold;"
          );
        }

        console.log("[Home Auth] Tipo de usuário:", resolvedType || "não informado");
      }

      setLoading(false);
    })();
  }, [navigate]);


  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-primary">
        <p className="text-lg text-muted-foreground">Checking authentication...</p>
      </div>
    );
  }

  function handleLogout(event: React.MouseEvent<HTMLButtonElement, MouseEvent>): void {
    event.preventDefault();
    localStorage.removeItem("auth_token");
    navigate("/login");
  }

  // Sonda de diagnostico: chama o webhook de status e mostra a resposta em tela.
  // Trata loading, sucesso (2xx) e erro (falha de rede ou HTTP nao-2xx).
  async function handleCheckStatus(): Promise<void> {
    setStatusState("loading");
    setStatusResult(null);

    try {
      const result = await checkStatus();
      setStatusResult(formatStatusResult(result));
      setStatusState(result.ok ? "success" : "error");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatusResult(`Falha ao consultar o status:\n${message}`);
      setStatusState("error");
    }
  }
  // Define os cards dinamicamente para que o layout se ajuste ao total exibido
  const cards = [
    {
      key: "text",
      title: "Text Control",
      description: "Type commands to control your devices",
      icon: <Keyboard size={48} />,
      route: "/text",
    },
    {
      key: "voice",
      title: "Voice Control",
      description: "Speak naturally to your smart home",
      icon: <Mic size={48} />,
      route: "/webvoice_test",
    },
  ];

  if (userType === "admin") {
    cards.push({
      key: "register",
      title: "User Registration",
      description: "Create new user profiles via webhook",
      icon: <UserPlus size={48} />,
      route: "/register",
    });
  }

  // Ajusta colunas e largura máxima de acordo com a quantidade de cards
  const gridCols =
    cards.length === 2
      ? "md:grid-cols-2 max-w-4xl"
      : "md:grid-cols-2 xl:grid-cols-3 max-w-5xl";

  return (
    <div className="min-h-screen bg-gradient-primary">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-accent bg-clip-text text-transparent mb-4">
            Smart Home Interface
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Control your smart home with intuitive text commands or natural voice interactions
          </p>
        </header>

        {/* Control Cards */}
        <div
          className={`grid grid-cols-1 ${gridCols} gap-8 justify-items-center items-stretch mx-auto`}
        >
          {cards.map((card) => (
            <ButtonCard
              key={card.key}
              title={card.title}
              description={card.description}
              icon={card.icon}
              route={card.route}
            />
          ))}
        </div>

        {/* Status indicator */}
        <div className="text-center mt-16">
          <div className="inline-flex items-center space-x-2 px-4 py-2 bg-dark-surface/50 rounded-full border border-border/30">
            <div className="w-2 h-2 bg-tech-blue rounded-full animate-pulse" />
            <span className="text-sm text-muted-foreground">System Online</span>
          </div>

          {/* Sonda de status: valida se o backend consegue alcancar o webhook do n8n */}
          <div className="mt-6 flex flex-col items-center">
            <button
              onClick={handleCheckStatus}
              disabled={statusState === "loading"}
              className="inline-flex items-center justify-center space-x-2 px-6 py-3 rounded-lg bg-gradient-accent text-primary-foreground font-semibold shadow-card hover:shadow-hover transition duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {statusState === "loading" ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>Consultando status...</span>
                </>
              ) : (
                <>
                  <Activity size={20} />
                  <span>Verificar Status</span>
                </>
              )}
            </button>

            {statusResult && (
              <div className="mt-6 w-full max-w-2xl text-left">
                <h3
                  className={`text-sm font-semibold uppercase tracking-wide mb-2 ${
                    statusState === "error" ? "text-destructive" : "text-tech-blue"
                  }`}
                >
                  {statusState === "error" ? "Erro na consulta" : "Resposta do webhook"}
                </h3>
                <pre className="max-h-72 overflow-auto rounded-xl bg-black/40 p-4 text-xs text-foreground/80 whitespace-pre-wrap break-words">
{statusResult}
                </pre>
              </div>
            )}
          </div>

          <div className="text-center mt-16">
            <div className="mt-4">
              <button
                onClick={handleLogout}
                className="text-sm text-muted-foreground hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
