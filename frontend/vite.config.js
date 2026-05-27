import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import dotenv from 'dotenv'
import path from 'path'

// Load environment variables from the backend .env file
dotenv.config({ path: path.resolve(__dirname, '../backend/.env') })

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'process.env.BACKEND_PORT': JSON.stringify(process.env.PORT || '8000'),
  },
  server: {
    port: parseInt(process.env.FRONTEND_PORT) || 5173,
  }
})
