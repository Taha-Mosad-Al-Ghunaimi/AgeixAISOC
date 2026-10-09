import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        nexus: {
          bg: "#0a0e17",
          surface: "#111827",
          border: "#1e293b",
          cyan: "#00f0ff",
          "cyan-dim": "#0088aa",
          red: "#ff003c",
          "red-dim": "#cc0030",
          green: "#00ff88",
          "green-dim": "#00aa55",
          amber: "#ffaa00",
          purple: "#7c3aed",
          gray: "#94a3b8",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "scan-line": "scan-line 4s linear infinite",
        "fade-in": "fade-in 0.5s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
        "neon-pulse-green": "neon-pulse-green 2s ease-in-out infinite",
        "neon-pulse-red": "neon-pulse-red 2s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        "scan-line": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "neon-pulse-green": {
          "0%, 100%": {
            textShadow: "0 0 7px rgba(0,255,136,0.8), 0 0 15px rgba(0,255,136,0.5), 0 0 30px rgba(0,255,136,0.3)",
          },
          "50%": {
            textShadow: "0 0 10px rgba(0,255,136,1), 0 0 25px rgba(0,255,136,0.7), 0 0 45px rgba(0,255,136,0.4)",
          },
        },
        "neon-pulse-red": {
          "0%, 100%": {
            textShadow: "0 0 7px rgba(255,0,60,0.8), 0 0 15px rgba(255,0,60,0.5), 0 0 30px rgba(255,0,60,0.3)",
          },
          "50%": {
            textShadow: "0 0 10px rgba(255,0,60,1), 0 0 25px rgba(255,0,60,0.7), 0 0 45px rgba(255,0,60,0.4)",
          },
        },
      },
    },
  },
  plugins: [],
};
export default config;
