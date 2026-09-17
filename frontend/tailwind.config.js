/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        navy: {
          50: '#f4f6fb',
          100: '#e8ecf6',
          200: '#cbd6eb',
          300: '#9eb4dc',
          400: '#698dc9',
          500: '#436cb4',
          600: '#325399',
          700: '#28427d',
          800: '#1c2d55',
          900: '#0f1933',
          950: '#080d1c',
        },
        gov: {
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#1d4ed8',
          600: '#1e40af',
          700: '#1e3a8a',
          800: '#172554',
          900: '#0f172a',
        },
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.03)',
        'card-hover': '0 12px 24px -6px rgba(15, 23, 42, 0.08), 0 4px 8px -4px rgba(15, 23, 42, 0.03)',
        'elevated': '0 20px 30px -10px rgba(15, 23, 42, 0.12), 0 8px 12px -6px rgba(15, 23, 42, 0.06)',
        'glow-blue': '0 0 25px -5px rgba(30, 64, 175, 0.25)',
        'glow-emerald': '0 0 25px -5px rgba(5, 150, 105, 0.25)',
      },
    },
  },
  plugins: [],
}

