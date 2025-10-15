import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Register from "./pages/Register";
import Text from "./pages/Text";
import Voice from "./pages/Voice";
import WebVoice_test from "./pages/WebVoice_test";  // 🆕 <-- Importa o novo componente
import WebVoice from "./pages/Voice";  // 🆕 <-- Importa o novo componente
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Register />} />
          <Route path="/text" element={<Text />} />
          <Route path="/voice" element={<Voice />} />
          <Route path="/webvoice" element={<WebVoice />} /> {/* 🆕 Nova rota */}
          <Route path="/webvoice_test" element={<WebVoice_test />} /> 
          <Route path="/login" element={<Login />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
