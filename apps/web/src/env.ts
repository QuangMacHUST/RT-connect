import { z } from 'zod'

const environmentSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default('http://localhost:8000/api/v1'),
  VITE_APP_VERSION: z.string().min(1).default('0.1.0-dev'),
  VITE_SUPABASE_URL: z.string().url().optional().or(z.literal('')),
  VITE_SUPABASE_PUBLISHABLE_KEY: z.string().optional()
})

export const environment = environmentSchema.parse({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_APP_VERSION: import.meta.env.VITE_APP_VERSION,
  VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
  VITE_SUPABASE_PUBLISHABLE_KEY: import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
})
