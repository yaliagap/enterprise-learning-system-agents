import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@copilotkit/react-ui/dist/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ["var(--font-heading)", "Poppins", "sans-serif"],
        sans: ["var(--font-body)", "Open Sans", "sans-serif"],
      },
      colors: {
        // Primary design tokens
        primary: {
          DEFAULT: "#2563EB",
          50:  "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
        secondary: {
          DEFAULT: "#F59E0B",
          50:  "#FFFBEB",
          100: "#FEF3C7",
          200: "#FDE68A",
          500: "#F59E0B",
          600: "#D97706",
          700: "#B45309",
        },
        accent: {
          DEFAULT: "#10B981",
          50:  "#ECFDF5",
          100: "#D1FAE5",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
        },
        destructive: {
          DEFAULT: "#DC2626",
          50:  "#FEF2F2",
          100: "#FEE2E2",
          500: "#EF4444",
          600: "#DC2626",
          700: "#B91C1C",
        },
        // Surface / background
        background: "#F8FAFC",
        surface: "#FFFFFF",
        foreground: "#0F172A",
        muted: {
          DEFAULT: "#64748B",
          bg: "#F1F5F9",
        },
        border: "#E2E8F0",
        card: {
          DEFAULT: "#FFFFFF",
        },
        // Aliases — keep brand / copilot / navy / ai / status names pointing to tokens
        brand: {
          50:  "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
        copilot: {
          50:  "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
        navy: {
          600: "#1D4ED8",
          700: "#1E40AF",
          800: "#1E3A8A",
        },
        ai: {
          DEFAULT: "#2563EB",
          600: "#2563EB",
          700: "#1D4ED8",
        },
        // Status colours for workflow phases
        status: {
          planning: "#F59E0B",
          studying: "#2563EB",
          awaiting: "#7C3AED",
          assessing: "#DB2777",
          done: "#10B981",
        },
      },
      boxShadow: {
        card: "0 1px 3px rgba(37,99,235,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        "card-md": "0 4px 6px rgba(37,99,235,0.08), 0 2px 4px rgba(0,0,0,0.06)",
      },
      borderRadius: {
        card: "12px",
        badge: "6px",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.25s ease-out both",
        "slide-up": "slideUp 0.3s ease-out both",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
