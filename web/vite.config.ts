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
          manualChunks(id) {
            if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) {
              return "react";
            }
            if (id.includes("node_modules/antd") || id.includes("node_modules/@ant-design/icons")) {
              return "antd";
            }
            return undefined;
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
