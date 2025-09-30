import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "@/services/user_login";

const Login = () => {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    const result = await loginUser(formData.email, formData.password);

    if (result.status === "success" && result.session_id) {
      localStorage.setItem("session_id", result.session_id);
      navigate("/"); // envia para a Home
    } else {
      setError(result.message || "Login failed");
    }

    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-primary px-4">
      <div className="w-full max-w-md bg-gradient-card rounded-2xl shadow-card border border-border/50 p-8">
        {/* Header */}
        <h2 className="text-3xl font-bold text-center bg-gradient-accent bg-clip-text text-transparent mb-6">
          Welcome Back
        </h2>
        <p className="text-center text-muted-foreground mb-8">
          Log in to control your smart home
        </p>

        {/* Error */}
        {error && (
          <div className="mb-4 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            name="email"
            placeholder="Email"
            value={formData.email}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 bg-dark-surface border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />

          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 bg-dark-surface border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-6 py-2 bg-gradient-accent text-primary-foreground rounded-lg font-medium hover:bg-gradient-hover transition-all duration-200 disabled:opacity-50 shadow-card hover:shadow-hover"
          >
            {isLoading ? "Logging in..." : "Log In"}
          </button>
        </form>

        {/* Link para Register */}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Don’t have an account?{" "}
          <button
            onClick={() => navigate("/register")}
            className="text-primary hover:underline"
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
};

export default Login;
