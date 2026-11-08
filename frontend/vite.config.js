import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // strictPort: the gateway only allows requests from port 5173,
  // so fail loudly instead of silently moving to another port.
  server: { port: 5173, strictPort: true },
  test: { environment: "node" },
});
