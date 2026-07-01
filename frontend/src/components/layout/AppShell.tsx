import type { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">VeriFi</h1>
        <p className="app-subtitle">
          Policy-grounded answers from verified Fidelity documents
        </p>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}
