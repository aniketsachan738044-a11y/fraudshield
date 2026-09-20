import { createContext, useContext, useEffect, useState } from "react";

const CurrencyContext = createContext({
  currency: "INR",
  setCurrency: () => {},
  cycleCurrency: () => {},
});

export function CurrencyProvider({ children }) {
  const [currency, setCurrency] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("fraudshield_currency") || "INR";
    }
    return "INR";
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("fraudshield_currency", currency);
    }
  }, [currency]);

  const cycleCurrency = () => {
    setCurrency((prev) => {
      if (prev === "INR") return "USD";
      if (prev === "USD") return "native";
      return "INR";
    });
  };

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, cycleCurrency }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  return useContext(CurrencyContext);
}
