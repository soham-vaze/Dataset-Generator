import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext();

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem("token"));
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem("userEmail"));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      setIsAuthenticated(true);
      // Fetch email if we don't have it yet
      if (!userEmail) {
        axios.get(`${API_BASE}/me`).then((res) => {
          setUserEmail(res.data.email);
          localStorage.setItem("userEmail", res.data.email);
        }).catch(() => {});
      }
    } else {
      delete axios.defaults.headers.common["Authorization"];
      setIsAuthenticated(false);
    }
  }, [token]);

  const login = (newToken) => {
    setToken(newToken);
    localStorage.setItem("token", newToken);
    // Fetch email after login
    axios.get(`${API_BASE}/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    }).then((res) => {
      setUserEmail(res.data.email);
      localStorage.setItem("userEmail", res.data.email);
    }).catch(() => {});
  };

  const logout = () => {
    setToken(null);
    setUserEmail(null);
    localStorage.removeItem("token");
    localStorage.removeItem("userEmail");
  };

  return (
    <AuthContext.Provider value={{ token, login, logout, isAuthenticated, userEmail }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
