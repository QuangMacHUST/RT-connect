import type { ReactNode } from 'react'

type CompactPageProps = {
  title: string
  description: string
  eyebrow?: string
  actions?: ReactNode
  children: ReactNode
}

export function CompactPage({ title, description, eyebrow, actions, children }: CompactPageProps) {
  return <div className="page compact-page">
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
    {children}
  </div>
}
