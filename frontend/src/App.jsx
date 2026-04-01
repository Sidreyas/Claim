import { Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import AppLayout from './components/AppLayout';
import ClaimList from './components/ClaimList';
import ClaimForm from './components/ClaimForm';
import ClaimDetail from './components/ClaimDetail';
import InfoPage from './components/InfoPage';
import FAQPage from './components/FAQPage';
import ContactPage from './components/ContactPage';

export default function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<ClaimList />} />
          <Route path="claims" element={<ClaimList />} />
          <Route path="claims/:claimId" element={<ClaimDetail />} />
          <Route path="details/:claimId" element={<ClaimDetail />} />
          <Route path="claimrequestform" element={<ClaimForm />} />
          <Route path="submit" element={<Navigate to="/claimrequestform" replace />} />
          <Route path="info" element={<InfoPage />} />
          <Route path="faq" element={<FAQPage />} />
          <Route path="contact" element={<ContactPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </ConfigProvider>
  );
}
