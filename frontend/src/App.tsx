import { Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthProvider";
import { RequireAuth } from "./auth/RequireAuth";
import { ViewModeProvider } from "./layout/ViewModeProvider";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { HomePage } from "./pages/HomePage";
import { AccountDetailPage } from "./pages/AccountDetailPage";
import { TransferPage } from "./pages/TransferPage";
import { ProfilePage } from "./pages/ProfilePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { SubscriptionsPage } from "./subscriptions/SubscriptionsPage";
import { KateConsentPage } from "./skills/KateConsentPage";
import { DashboardPage } from "./dashboard/DashboardPage";
import { FamilyPage } from "./family/FamilyPage";

export function App() {
  return (
    <ViewModeProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<HomePage />} />
            <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
            <Route path="/transfer" element={<TransferPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/kate" element={<KateConsentPage />} />
            <Route path="/family" element={<FamilyPage />} />
          </Route>
          <Route
            path="/jury"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </AuthProvider>
    </ViewModeProvider>
  );
}
