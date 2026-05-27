import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        quazar: {
          bg: "#0f0f12",
          panel: "#18181c",
          border: "#2a2a32",
          accent: "#6366f1",
          accentHover: "#818cf8",
          text: "#e4e4e7",
          muted: "#71717a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
