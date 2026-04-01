import { Typography, Card, Descriptions } from 'antd';
import { MailOutlined, PhoneOutlined, EnvironmentOutlined } from '@ant-design/icons';

const { Title } = Typography;

export default function ContactPage() {
  return (
    <div>
      <Title level={3}>Contact Us</Title>
      <Card>
        <Descriptions column={1} bordered>
          <Descriptions.Item
            label={
              <span>
                <MailOutlined /> Email
              </span>
            }
          >
            support@skillquotient.com
          </Descriptions.Item>
          <Descriptions.Item
            label={
              <span>
                <PhoneOutlined /> Phone
              </span>
            }
          >
            +60 3-1234 5678
          </Descriptions.Item>
          <Descriptions.Item
            label={
              <span>
                <EnvironmentOutlined /> Address
              </span>
            }
          >
            Level 10, Menara Great Eastern, Kuala Lumpur, Malaysia
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
