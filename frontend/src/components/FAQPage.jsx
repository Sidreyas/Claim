import { Typography, Collapse, Card } from 'antd';

const { Title } = Typography;

const faqItems = [
  {
    key: '1',
    label: 'What file formats are supported for discharge notes?',
    children: 'The system accepts JPG, JPEG, PNG, GIF, and PDF files up to 16MB in size.',
  },
  {
    key: '2',
    label: 'How does the OCR extraction work?',
    children:
      'The system uses Google Gemini AI to read the uploaded discharge note image and extract key fields such as patient name, IC/NRIC, hospital, diagnosis, admission/discharge dates, and doctor name.',
  },
  {
    key: '3',
    label: 'What is the similarity score?',
    children:
      'The similarity score indicates how closely a new claim matches existing claims in the database. A high score (above 85%) may indicate a duplicate or fraudulent claim.',
  },
  {
    key: '4',
    label: 'What happens when fraud is detected?',
    children:
      'When fraud is detected, the claim is flagged as "Pending Approval" with a detailed AI-generated fraud analysis report. A reviewer must then approve or reject the claim.',
  },
  {
    key: '5',
    label: 'What are exclusion words?',
    children:
      'Certain diagnoses (e.g., pregnancy-related conditions, criminal activity, substance abuse) are flagged for a second opinion as they may be excluded under certain insurance policies.',
  },
  {
    key: '6',
    label: 'Can I edit the OCR-extracted data?',
    children:
      'Yes. After OCR extraction, you can review and edit all fields before submitting the claim. The system will validate your form data against the discharge note.',
  },
  {
    key: '7',
    label: 'How do I approve or reject a claim?',
    children:
      'Navigate to the claim detail page by clicking "View" in the claims list. If the claim is pending, you will see Approve and Reject buttons.',
  },
];

export default function FAQPage() {
  return (
    <div>
      <Title level={3}>Frequently Asked Questions</Title>
      <Card>
        <Collapse
          accordion
          items={faqItems}
          defaultActiveKey={['1']}
          size="large"
        />
      </Card>
    </div>
  );
}
