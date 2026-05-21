import { Outlet, useLocation } from "react-router-dom";

import { AppHeader } from "./AppHeader";

export function AppShell() {
  const location = useLocation();

  return (
    <div className="relative flex min-h-screen min-h-[100dvh] flex-col">
      <div className="ambient-bg" aria-hidden />
      <AppHeader />
      <main className="relative z-10 flex-1 overflow-x-hidden overflow-y-auto px-4 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:px-6 sm:py-8 md:px-10">
        <div key={location.pathname} className="mx-auto w-full max-w-container animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
