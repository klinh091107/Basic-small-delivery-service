import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import { Icon, Loading, Notice } from "./components";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api("/auth/me", { signal: controller.signal })
      .then(setEmployee)
      .catch(err => {
        if (err.name === "AbortError") return;
        if (err.status === 401) setEmployee(null);
        else setError(err.message);
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    const expired = () => setEmployee(null);
    window.addEventListener("staff-session-expired", expired);
    return () => window.removeEventListener("staff-session-expired", expired);
  }, []);

  async function signIn(employee_code, password) {
    const saved = await api("/auth/login", { method: "POST", body: { employee_code, password } });
    setEmployee(saved);
  }
  async function signOut() {
    await api("/auth/logout", { method: "POST" });
    setEmployee(null);
  }
  if (loading) return <div className="auth-loading"><Loading text="Checking your session…" /></div>;
  if (error) return <div className="auth-loading"><Notice error={error} /><button className="button secondary" onClick={() => setRetry(n => n + 1)}>Retry Connection</button></div>;
  return <AuthContext.Provider value={{ employee, signIn, signOut }}>{children}</AuthContext.Provider>;
}

export function RequireLogin({ children }) {
  const { employee } = useAuth();
  const location = useLocation();
  if (!employee) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return children;
}

export function LoginPage() {
  const { employee, signIn } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const from = location.state?.from;
  const destination = typeof from === "string" && from.startsWith("/") && !from.startsWith("//") && !from.startsWith("/login") ? from : "/";
  useEffect(() => { document.title = "Staff sign in · Produce Desk"; }, []);
  if (employee) return <Navigate to={destination} replace />;
  async function submit(event) {
    event.preventDefault();
    if (!code.trim() || !password.trim()) return setError("Enter your employee code and password.");
    setSaving(true); setError("");
    try {
      await signIn(code.trim(), password);
      navigate(destination, { replace: true });
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }
  return <main className="login-page">
    <div className="login-brand"><span className="brand-mark"><Icon name="leaf" size={26} /></span><span>Produce Desk<small>ORDER MANAGEMENT</small></span></div>
    <section className="login-card" aria-labelledby="login-title">
      <div className="eyebrow">STAFF WORKSPACE</div>
      <h1 id="login-title">Welcome back</h1>
      <p className="login-description">Sign in to manage produce orders and deliveries.</p>
      <Notice error={error} />
      <form onSubmit={submit}>
        <fieldset disabled={saving}>
          <div className="field"><label htmlFor="employee-code">Employee code</label><input id="employee-code" name="username" autoComplete="username" autoCapitalize="characters" spellCheck={false} maxLength={40} value={code} onChange={event => setCode(event.target.value)} required placeholder="Enter your employee code" autoFocus /></div>
          <div className="field"><label htmlFor="employee-password">Password</label><div className="password-field"><input id="employee-password" name="password" type={visible ? "text" : "password"} autoComplete="current-password" maxLength={256} value={password} onChange={event => setPassword(event.target.value)} required placeholder="Enter your password" /><button type="button" aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} onClick={() => setVisible(value => !value)}>{visible ? "Hide" : "Show"}</button></div></div>
          <button className="button primary login-submit" type="submit">{saving ? "Signing in…" : "Sign In"}<Icon name="arrow" size={16} /></button>
        </fieldset>
      </form>
      <p className="login-help">Need access? Contact your workspace administrator.</p>
    </section>
    <p className="login-footer">Internal staff access · Produce Desk</p>
  </main>;
}

export function StaffMenu() {
  const { employee, signOut } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function logout() {
    setBusy(true); setError("");
    try { await signOut(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="staff-menu"><span className="staff-code" title={employee.full_name}>{employee.employee_code}</span><button className="button secondary small" disabled={busy} onClick={logout}>{busy ? "Signing out…" : "Sign Out"}</button>{error && <span role="alert" className="logout-error">{error}</span>}</div>;
}
