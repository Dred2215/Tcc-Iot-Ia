import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

interface ButtonCardProps {
  title: string;
  icon: ReactNode;
  route: string;
  description?: string;
}

export const ButtonCard = ({ title, icon, route, description }: ButtonCardProps) => {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(route)}
      className="group relative w-full max-w-sm p-8 bg-gradient-card rounded-2xl shadow-card border border-border/50 transition-all duration-300 hover:shadow-hover hover:shadow-glow hover:bg-gradient-hover hover:scale-105 active:scale-95"
    >
      <div className="flex flex-col items-center space-y-4">
        <div className="p-4 rounded-full bg-primary/10 group-hover:bg-primary/20 transition-colors duration-300">
          <div className="text-primary text-4xl group-hover:text-primary-foreground transition-colors duration-300">
            {icon}
          </div>
        </div>
        
        <div className="text-center">
          <h3 className="text-xl font-semibold text-foreground group-hover:text-primary-foreground transition-colors duration-300">
            {title}
          </h3>
          {description && (
            <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/80 transition-colors duration-300 mt-1">
              {description}
            </p>
          )}
        </div>
      </div>
      
      {/* Subtle glow effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-accent opacity-0 group-hover:opacity-10 transition-opacity duration-300" />
    </button>
  );
};