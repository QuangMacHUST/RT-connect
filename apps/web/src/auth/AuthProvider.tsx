import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import type { Session } from '@supabase/supabase-js'

import { authConfigurationMessage, getSupabaseClient } from './supabase'

type AuthContextValue = {
  session: Session | null
  loading: boolean
  configured: boolean
  signInWithPassword: (email: string, password: string) => Promise<string | null>
  sendMagicLink: (email: string) => Promise<string | null>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const supabase = getSupabaseClient()
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(() => Boolean(supabase))

  useEffect(() => {
    if (!supabase) return
    let active = true
    void supabase.auth.getSession().then(({ data }) => {
      if (active) {
        setSession(data.session)
        setLoading(false)
      }
    })
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setLoading(false)
    })
    return () => {
      active = false
      data.subscription.unsubscribe()
    }
  }, [supabase])

  const value = useMemo<AuthContextValue>(() => ({
    session,
    loading,
    configured: Boolean(supabase),
    async signInWithPassword(email, password) {
      if (!supabase) return authConfigurationMessage
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      return error?.message ?? null
    },
    async sendMagicLink(email) {
      if (!supabase) return authConfigurationMessage
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` }
      })
      return error?.message ?? null
    },
    async signOut() {
      if (supabase) await supabase.auth.signOut()
    }
  }), [loading, session, supabase])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Context hook intentionally shares this module with its provider.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
