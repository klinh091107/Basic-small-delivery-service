import { useEffect, useState } from "react";

export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Requested-With": "ProduceDesk", ...options.headers },
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Cannot reach the server. Check that the backend is running and try again.",
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "The server returned an unexpected response. Please try again.",
    );
  }
  if (!response.ok) {
    const error = new Error(
      data.error?.message || "The request could not be completed.",
    );
    error.status = response.status;
    if (response.status === 401 && !path.startsWith("/auth/")) {
      window.dispatchEvent(new Event("staff-session-expired"));
    }
    throw error;
  }
  return data;
}

export function useApi(path, refresh = 0) {
  const [result, setResult] = useState({
    path: null,
    refresh: null,
    data: null,
    error: "",
    loading: true,
  });
  useEffect(() => {
    const controller = new AbortController();
    setResult({ path, refresh, data: null, error: "", loading: true });
    api(path, { signal: controller.signal })
      .then((data) =>
        setResult({ path, refresh, data, error: "", loading: false }),
      )
      .catch((error) => {
        if (error.name !== "AbortError")
          setResult({
            path,
            refresh,
            data: null,
            error: error.message,
            loading: false,
          });
      });
    return () => controller.abort();
  }, [path, refresh]);
  return result.path === path && result.refresh === refresh
    ? result
    : { data: null, error: "", loading: true };
}

export function useDebounce(value, delay = 200) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function formatDate(value) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

export function formatTime(value) {
  return (
    new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "UTC",
    }).format(new Date(value)) + " UTC"
  );
}
