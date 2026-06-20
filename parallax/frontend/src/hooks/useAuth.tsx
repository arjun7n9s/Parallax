import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

const KEY_STORAGE = "parallax.sessionKey";
const DEMO_KEY = "demo-7c1f2d-a87e9-9fe870-3401";

interface AuthContextValue {
  key: string | null;
  signIn: (key: string) => void;
  signOut: () => void;
  isAuthed: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [key, setKey] = useState<string | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem(KEY_STORAGE);
    if (stored) setKey(stored);
  }, []);

  const signIn = (newKey: string) => {
    const v = newKey.trim() || DEMO_KEY;
    sessionStorage.setItem(KEY_STORAGE, v);
    setKey(v);
  };

  const signOut = () => {
    sessionStorage.removeItem(KEY_STORAGE);
    setKey(null);
  };

  return (
    <AuthContext.Provider value={{ key, signIn, signOut, isAuthed: !!key }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthed } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!isAuthed) navigate("/auth", { replace: true });
  }, [isAuthed, navigate]);
  if (!isAuthed) return null;
  return <>{children}</>;
}
