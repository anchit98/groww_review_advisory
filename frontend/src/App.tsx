import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { PulseLayout } from "./layouts/PulseLayout";
import { QuotesPage } from "./pages/QuotesPage";
import { SummaryPage } from "./pages/SummaryPage";
import { ThemesPage } from "./pages/ThemesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route element={<PulseLayout />}>
          <Route index element={<SummaryPage />} />
          <Route path="themes" element={<ThemesPage />} />
          <Route path="quotes" element={<QuotesPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
