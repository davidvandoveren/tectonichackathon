import { Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthProvider";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { HomePage } from "./pages/HomePage";
import { AccountDetailPage } from "./pages/AccountDetailPage";
import { TransferPage } from "./pages/TransferPage";
import { ProfilePage } from "./pages/ProfilePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SubscriptionsPage } from "./subscriptions/SubscriptionsPage";
import { FamilyPage } from "./family/FamilyPage";

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
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
          <Route path="/family" element={<FamilyPage />} />
        </Route>
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </AuthProvider>
  );
}
