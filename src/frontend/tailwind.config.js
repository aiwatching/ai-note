/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontSize: {
        'xs': '0.75rem',
        'sm': '0.8125rem',
        'base': '0.875rem',
        'lg': '0.9375rem',
      },
    },
  },
  plugins: [],
}
