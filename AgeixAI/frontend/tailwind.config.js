/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', '"Courier New"', "monospace"],
      },
      colors: {
        bg: { primary: "#060d1a", secondary: "#070e1e", card: "#0a1428" },
        cyan: { DEFAULT: "#00e5ff" },
        red: { acc: "#ff4466" },
        green: { acc: "#00ff88" },
        amber: { acc: "#ffd700" },
      },
    },
  },
  plugins: [],
}
