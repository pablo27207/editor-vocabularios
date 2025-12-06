/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./app/templates/**/*.html",
        "./app/static/js/**/*.js"
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                primary: '#334155', // Slate-700
                secondary: '#64748b', // Slate-500
            }
        },
    },
    plugins: [],
}
