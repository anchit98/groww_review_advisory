import type { ReactNode } from "react";

/** Shared bottom copy styling so paired summary cards align on the last line. */
export function CardFooter({ children }: { children: ReactNode }) {
  return (
    <p className="mt-4 shrink-0 break-words text-xs leading-relaxed text-on-surface-variant/75">
      {children}
    </p>
  );
}
