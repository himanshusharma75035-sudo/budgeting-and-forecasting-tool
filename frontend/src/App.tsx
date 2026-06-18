import { Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { AppShell } from "./components/AppShell";
import { EmptyState } from "./components/EmptyState";
import Accounts from "./pages/Accounts";
import Budgets from "./pages/Budgets";
import Dashboard from "./pages/Dashboard";
import DataImport from "./pages/DataImport";
import Forecasts from "./pages/Forecasts";
import Variance from "./pages/Variance";

export default function App() {
  return (
    <>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/import" element={<DataImport />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/forecasts" element={<Forecasts />} />
          <Route path="/variance" element={<Variance />} />
          <Route
            path="*"
            element={<EmptyState title="Page not found" description="That route does not exist." />}
          />
        </Routes>
      </AppShell>
      <Toaster richColors position="bottom-right" />
    </>
  );
}
