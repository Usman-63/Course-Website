/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0f172a", // Slate 950
          light: "#1e293b",   // Slate 800
          lighter: "#334155", // Slate 700
          hover: "#475569",   // Slate 600
        },
        primary: {
          DEFAULT: "#38bdf8", // Sky 400
          hover: "#0ea5e9",   // Sky 500
          light: "rgba(56, 189, 248, 0.1)",
        },
        yellow: {
          DEFAULT: "#fbbf24", // Amber 400 - Warm accent
          hover: "#f59e0b",   // Amber 500
        },
        surface: {
          DEFAULT: "#1e293b", // Slate 800
          hover: "#334155",   // Slate 700
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Lexend', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};