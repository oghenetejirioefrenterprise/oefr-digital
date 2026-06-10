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
        navy: {
          50: "#e8edf5",
          100: "#c4d0e5",
          200: "#9db0d2",
          300: "#7590bf",
          400: "#5678b2",
          500: "#3860a5",
          600: "#2d4f8a",
          700: "#1e3a6e",
          800: "#122653",
          900: "#0a1628",
          950: "#060d1a",
        },
        green: {
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
        },
        lime: {
          400: "#a3e635",
          500: "#84cc16",
          600: "#65a30d",
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
};
export default config;
