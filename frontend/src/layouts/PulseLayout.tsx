import { Outlet } from "react-router-dom";

import { RunProvider } from "../context/RunContext";

export function PulseLayout() {
  return (
    <RunProvider>
      <Outlet />
    </RunProvider>
  );
}
