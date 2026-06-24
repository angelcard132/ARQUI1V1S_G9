import { createContext, useContext, useState, useCallback } from "react";

// Credenciales quemadas — sin backend, sin registro.
const VALID_USER = "admin";
const VALID_PASS = "admin1234";

const SESSION_KEY = "invernadero_session";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return sessionStorage.getItem(SESSION_KEY) === "true";
  });
  const [authError, setAuthError] = useState("");

  const login = useCallback((username, password) => {
    if (username === VALID_USER && password === VALID_PASS) {
      sessionStorage.setItem(SESSION_KEY, "true");
      setIsAuthenticated(true);
      setAuthError("");
      return true;
    }
    setAuthError("Usuario o contraseña incorrectos.");
    return false;
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, authError }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}