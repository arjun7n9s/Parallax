import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, RequireAuth } from "./hooks/useAuth";
import { Sidebar } from "./components/layout/Sidebar";
import { Ticker } from "./components/layout/Ticker";
import { DemoBanner, DemoGuardProvider } from "./components/DemoNotice";
import { tickerItems } from "./lib/mock-data";

const Landing = lazy(() => import("./pages/Landing"));
const Auth = lazy(() => import("./pages/Auth"));
const Console = lazy(() => import("./pages/Console"));
const ThreatHunt = lazy(() => import("./pages/ThreatHunt"));
const AnalysisDetail = lazy(() => import("./pages/AnalysisDetail"));
const TAIG = lazy(() => import("./pages/TAIG"));
const Economics = lazy(() => import("./pages/Economics"));
const Activity = lazy(() => import("./pages/Activity"));
const Settings = lazy(() => import("./pages/Settings"));
const Intel = lazy(() => import("./pages/Intel"));

function AppShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const showTicker = !pathname.startsWith("/auth") && pathname !== "/";

  return (
    <DemoGuardProvider>
      <div className="min-h-screen flex bg-bone text-ink">
        <Sidebar />
        <main className="flex-1 min-w-0 flex flex-col">
          <DemoBanner />
          {showTicker && <Ticker items={tickerItems} />}
          <div className="flex-1 min-w-0">{children}</div>
        </main>
      </div>
    </DemoGuardProvider>
  );
}

function Loading() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="font-mono text-xs uppercase tracking-widest text-ink/40">Loading…</div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/auth" element={<Auth />} />
          <Route
            path="/console"
            element={
              <RequireAuth>
                <AppShell>
                  <Console />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/console/:id"
            element={
              <RequireAuth>
                <AppShell>
                  <AnalysisDetail />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/hunt"
            element={
              <RequireAuth>
                <AppShell>
                  <ThreatHunt />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/intel"
            element={
              <RequireAuth>
                <AppShell>
                  <Intel />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/graph"
            element={
              <RequireAuth>
                <AppShell>
                  <TAIG />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/cost"
            element={
              <RequireAuth>
                <AppShell>
                  <Economics />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/activity"
            element={
              <RequireAuth>
                <AppShell>
                  <Activity />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/settings"
            element={
              <RequireAuth>
                <AppShell>
                  <Settings />
                </AppShell>
              </RequireAuth>
            }
          />
        </Routes>
      </Suspense>
    </AuthProvider>
  );
}
