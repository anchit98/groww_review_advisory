/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "var(--color-surface)",
        "surface-low": "var(--color-surface-container-low)",
        "surface-card": "var(--color-surface-container)",
        "surface-high": "var(--color-surface-container-high)",
        "on-surface": "var(--color-on-surface)",
        "on-surface-variant": "var(--color-on-surface-variant)",
        outline: "var(--color-outline)",
        "outline-variant": "var(--color-outline-variant)",
        primary: "var(--color-primary)",
        "primary-container": "var(--color-primary-container)",
        tertiary: "var(--color-tertiary)",
        error: "var(--color-error)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          "Segoe UI Variable",
          "system-ui",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      maxWidth: {
        container: "1280px",
      },
      borderRadius: {
        DEFAULT: "0.75rem",
        lg: "1rem",
        xl: "1.25rem",
        "2xl": "1.5rem",
      },
      animation: {
        "fade-in": "fade-in-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards",
        "fade-in-slow": "fade-in-up 0.7s cubic-bezier(0.22, 1, 0.36, 1) forwards",
      },
      keyframes: {
        "fade-in-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
