import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "ADG_");
  const backendTarget = env.ADG_WEB_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
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
        "/admin": backendTarget,
        "/mcp": backendTarget,
        "/runtime": backendTarget
      }
    }
  };
});
