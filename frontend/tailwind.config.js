/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgApp: '#070a13',
        bgCard: 'rgba(16, 22, 40, 0.65)',
        borderLight: 'rgba(255, 255, 255, 0.06)',
        primary: '#00f2fe',
        secondary: '#8a2be2',
        accentBlue: '#0072ff',
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        title: ['Outfit', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
