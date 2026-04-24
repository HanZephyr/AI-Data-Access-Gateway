import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom"],
          antd: ["antd", "@ant-design/icons"]
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      "/admin": "http://127.0.0.1:8000",
      "/mcp": "http://127.0.0.1:8000",
      "/internal": "http://127.0.0.1:8000"
    }
  }
});
