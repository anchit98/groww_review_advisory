import { NavLink } from "react-router-dom";

import { cn } from "../lib/cn";

const tabs = [
  { to: "/", label: "Summary", end: true },
  { to: "/themes", label: "Themes" },
  { to: "/quotes", label: "Quotes" },
];

export function AppHeader() {
  return (
    <header className="glass-header sticky top-0 z-20">
      <div className="mx-auto flex max-w-container flex-col gap-3 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-4 md:px-10">
        <div className="flex min-w-0 items-center gap-3">
          <img
            src="/groww-logo.webp"
            alt=""
            width={40}
            height={40}
            className="h-10 w-10 shrink-0 rounded-xl object-contain"
            aria-hidden
          />
          <div className="min-w-0">
            <p className="truncate text-xs font-medium uppercase tracking-[0.18em] text-on-surface-variant/90 sm:tracking-[0.22em]">
              Groww Review Advisory
            </p>
            <p className="hidden bg-gradient-to-r from-on-surface to-primary bg-clip-text text-sm font-semibold text-transparent sm:block">
              Command Center · Advisory Portal
            </p>
            <p className="bg-gradient-to-r from-on-surface to-primary bg-clip-text text-sm font-semibold text-transparent sm:hidden">
              Advisory Portal
            </p>
          </div>
        </div>
        <nav
          className="glass-nav flex w-full items-stretch gap-0.5 sm:w-auto sm:items-center"
          aria-label="Primary"
        >
          {tabs.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "glass-nav-tab flex-1 text-center sm:flex-initial sm:px-[1.125rem]",
                  isActive && "glass-nav-tab-active",
                )
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
