import { ArrowLeft, Terminal } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ChatInterface } from "@/components/ChatInterface";

const Text = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-primary">
      <div className="container mx-auto px-4 py-12">
        {/* Back button */}
        <button
          onClick={() => navigate("/")}
          className="inline-flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors duration-200 mb-8"
        >
          <ArrowLeft size={20} />
          <span>Back to Home</span>
        </button>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-card rounded-full mb-6 shadow-card">
            <Terminal className="text-tech-blue" size={32} />
          </div>
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Text Control Interface
          </h1>
          <p className="text-lg text-muted-foreground">
            Chat with your smart home AI assistant
          </p>
        </div>

        {/* Chat Interface */}
        <div className="max-w-4xl mx-auto">
          <ChatInterface />
        </div>

        {/* Help section */}
        <div className="max-w-4xl mx-auto mt-8">
          <div className="bg-gradient-card rounded-2xl p-6 shadow-card border border-border/50">
            <h2 className="text-lg font-semibold text-foreground mb-4">Try these commands:</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="flex items-center space-x-3 text-sm text-muted-foreground">
                <div className="w-2 h-2 bg-tech-blue rounded-full" />
                <span>"Turn on the living room lights"</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-muted-foreground">
                <div className="w-2 h-2 bg-tech-blue rounded-full" />
                <span>"Set temperature to 24 degrees"</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-muted-foreground">
                <div className="w-2 h-2 bg-tech-blue rounded-full" />
                <span>"Check security system status"</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-muted-foreground">
                <div className="w-2 h-2 bg-tech-blue rounded-full" />
                <span>"Play music in the kitchen"</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Text;