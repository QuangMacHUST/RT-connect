import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import { environment } from '../env'

let client: SupabaseClient | null | undefined

export function getSupabaseClient(): SupabaseClient | null {
  if (client !== undefined) return client
  const url = environment.VITE_SUPABASE_URL
  const publishableKey = environment.VITE_SUPABASE_PUBLISHABLE_KEY
  client = url && publishableKey
    ? createClient(url, publishableKey, { auth: { persistSession: true, autoRefreshToken: true } })
    : null
  return client
}

export const authConfigurationMessage = 'Supabase Auth chưa được cấu hình cho môi trường này.'
