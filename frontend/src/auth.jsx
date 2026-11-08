import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, setUnauthorizedHandler, tokenStore } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [state, setState] = useState({
    status: tokenStore.get() ? "loading" : "anon",
    user: null,
  });

  const signOut = useCallback(() => {
    tokenStore.clear();
    setState({ status: "anon", user: null });
  }, []);

  // Any 401 from the API (an expired token, say) signs the user out.
  useEffect(() => {
    setUnauthorizedHandler(signOut);
  }, [signOut]);

  useEffect(() => {
    if (!tokenStore.get()) return;
    api
      .me()
      .then((user) => setState({ status: "authed", user }))
      .catch(() => setState({ status: "anon", user: null }));
  }, []);

  const signIn = useCallback(async (email, password) => {
    await api.login(email, password);
    const user = await api.me();
    setState({ status: "authed", user });
  }, []);

  const register = useCallback(
    async (email, password) => {
      await api.register(email, password);
      await signIn(email, password);
    },
    [signIn],
  );

  const value = useMemo(
    () => ({ ...state, signIn, register, signOut }),
    [state, signIn, register, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
