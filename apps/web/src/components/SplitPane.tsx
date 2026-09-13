import type { PropsWithChildren } from 'react'

export function SplitPane({ children }: PropsWithChildren) {
  return <div className="split-pane">{children}</div>
}
