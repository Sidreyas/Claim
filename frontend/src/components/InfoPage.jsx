import { Card, Typography, Divider, List } from 'antd';
import {
  SafetyCertificateOutlined,
  ScanOutlined,
  AuditOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const features = [
  {
    icon: <ScanOutlined style={{ fontSize: 24, color: '#1890ff' }} />,
    title: 'OCR Document Extraction',
    desc: 'Automatically extracts patient and medical information from hospital discharge notes using Google Gemini AI.',
  },
  {
    icon: <SafetyCertificateOutlined style={{ fontSize: 24, color: '#52c41a' }} />,
    title: 'Fraud Detection',
    desc: 'Uses text and image embeddings with FAISS similarity search to detect duplicate or suspicious claims.',
  },
  {
    icon: <AuditOutlined style={{ fontSize: 24, color: '#722ed1' }} />,
    title: 'Claim Validation',
    desc: 'Cross-references form data against discharge note data and flags exclusion-word diagnoses for second opinion.',
  },
  {
    icon: <CheckCircleOutlined style={{ fontSize: 24, color: '#fa8c16' }} />,
    title: 'Approval Workflow',
    desc: 'Claims go through a structured review and approval process with full audit trail.',
  },
];

export default function InfoPage() {
  return (
    <div>
      <Title level={3}>Information</Title>
      <Card>
        <Title level={4}>Insurance Claim Fraud Detection System</Title>
        <Paragraph>
          This system helps insurance companies detect potentially fraudulent medical claims
          by analysing hospital discharge notes, comparing them against a database of existing
          claims, and using AI to identify suspicious patterns.
        </Paragraph>

        <Divider orientation="left">Key Features</Divider>

        <List
          grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 2 }}
          dataSource={features}
          renderItem={(item) => (
            <List.Item>
              <Card size="small">
                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  {item.icon}
                  <div>
                    <Title level={5} style={{ margin: 0 }}>
                      {item.title}
                    </Title>
                    <Paragraph type="secondary" style={{ margin: 0, marginTop: 4 }}>
                      {item.desc}
                    </Paragraph>
                  </div>
                </div>
              </Card>
            </List.Item>
          )}
        />

        <Divider orientation="left">How It Works</Divider>

        <List
          dataSource={[
            'Upload a hospital discharge note image.',
            'OCR extracts key patient and medical fields automatically.',
            'Review and confirm the extracted data, then submit the claim.',
            'The system validates the claim against the discharge note and checks for excluded diagnoses.',
            'FAISS similarity search compares the claim against the existing database.',
            'If suspicious matches are found, AI generates a detailed fraud analysis report.',
            'Reviewers can approve or reject claims based on the analysis.',
          ]}
          renderItem={(item, i) => (
            <List.Item>
              <strong>{i + 1}.</strong> {item}
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
