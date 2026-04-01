import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, Avatar, Space } from 'antd';
import {
  UnorderedListOutlined,
  FormOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined,
  PhoneOutlined,
  UserOutlined,
} from '@ant-design/icons';

const { Sider, Content, Header } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <UnorderedListOutlined />, label: 'Claim List' },
  { key: '/claimrequestform', icon: <FormOutlined />, label: 'Claim request form' },
  { key: '/info', icon: <InfoCircleOutlined />, label: 'Information' },
  { key: '/faq', icon: <QuestionCircleOutlined />, label: 'FAQ' },
  { key: '/contact', icon: <PhoneOutlined />, label: 'Contact Us' },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = menuItems.find(
    (item) =>
      location.pathname === item.key ||
      (item.key !== '/' && location.pathname.startsWith(item.key))
  )?.key || '/';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Text
            strong
            style={{
              color: '#fff',
              fontSize: collapsed ? 14 : 18,
              whiteSpace: 'nowrap',
            }}
          >
            {collapsed ? 'SQ' : 'Skill Quotient'}
          </Text>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0, marginTop: 8 }}
        />

        <div
          style={{
            position: 'absolute',
            bottom: 48,
            left: 0,
            right: 0,
            padding: '12px 16px',
            borderTop: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Space>
            <Avatar size="small" icon={<UserOutlined />} />
            {!collapsed && (
              <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13 }}>
                Hi, Shareza Halim
              </Text>
            )}
          </Space>
        </div>
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 240, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            display: 'flex',
            alignItems: 'center',
            position: 'sticky',
            top: 0,
            zIndex: 5,
          }}
        >
          <Text strong style={{ fontSize: 16 }}>
            Insurance Claim Fraud Detection System
          </Text>
        </Header>

        <Content
          style={{
            margin: 24,
            padding: 24,
            background: '#f0f2f5',
            minHeight: 'calc(100vh - 64px - 48px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
