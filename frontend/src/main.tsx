import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles/global.css";
import { sessionSlot } from "./lib/sessionSlot";

// Inside the /demo phones: behave like a phone screen (no desktop scrollbars).
if (sessionSlot) {
  document.documentElement.classList.add("embedded-phone");
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
