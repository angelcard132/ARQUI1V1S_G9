import { useState, useRef, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { login, authError } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [shake, setShake] = useState(false);
  const userInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    userInputRef.current?.focus();
  }, []);

function handleSubmit(e) {
  e.preventDefault();

  const ok = login(username.trim(), password);

  if (ok) {
    navigate("/"); 
  } else {
    setShake(true);
    setTimeout(() => setShake(false), 400);
  }
}

  return (
    <div className="login-screen">
      <div className={`login-card ${shake ? "login-card--shake" : ""}`}>

        <header className="login-header">
          <div className="login-header__led" aria-hidden="true" />
          <p className="login-header__eyebrow">PROYECTO 2 ARQUI 1</p>
          <h1 className="login-header__title">LOGIN</h1>
        </header>

        <form className="login-form" onSubmit={handleSubmit} autoComplete="off">
          <label className="login-field">
            <span className="login-field__label">USUARIO</span>
            <input
              ref={userInputRef}
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              autoComplete="username"
              className="login-field__input"
            />
          </label>

          <label className="login-field">
            <span className="login-field__label">CONTRASEÑA</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              className="login-field__input"
            />
          </label>

          {authError && (
            <div className="login-error" role="alert">
              <span className="login-error__dot" aria-hidden="true" />
              {authError}
            </div>
          )}

          <button type="submit" className="login-submit">
            Iniciar sesión
          </button>
        </form>

      </div>
    </div>
  );
}