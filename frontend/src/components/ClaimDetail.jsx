import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Spin,
  Alert,
  Modal,
  Input,
  Typography,
  Divider,
  Row,
  Col,
  Result,
  message,
  Image,
  Progress,
  List,
  Statistic,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowLeftOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  SafetyCertificateOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';
import api from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const STATUS_CONFIG = {
  pending_review: { color: 'blue', label: 'New' },
  pending_approval: { color: 'orange', label: 'Pending Approval' },
  approved: { color: 'green', label: 'Approved' },
  rejected: { color: 'red', label: 'Rejected' },
  processed: { color: 'purple', label: 'Under Review' },
};

function getImageUrl(imagePath) {
  if (!imagePath) return null;
  const filename = imagePath.replace(/^uploaded_images[\\/]/, '');
  return `/api/get_image/${filename}`;
}

function SimilarityGauge({ value, label }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? '#ff4d4f' : pct >= 70 ? '#faad14' : '#52c41a';
  return (
    <div style={{ textAlign: 'center' }}>
      <Progress
        type="circle"
        percent={pct}
        size={80}
        strokeColor={color}
        format={(p) => <span style={{ fontSize: 16, fontWeight: 600 }}>{p}%</span>}
      />
      <div style={{ marginTop: 4 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
      </div>
    </div>
  );
}

function DetailRow({ label, newVal, matchVal, highlight }) {
  const isDiff = newVal !== matchVal && newVal && matchVal;
  return (
    <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
      <td style={{
        padding: '8px 12px',
        fontWeight: 600,
        backgroundColor: '#fafafa',
        width: 140,
        fontSize: 13,
        verticalAlign: 'top',
      }}>
        {label}
      </td>
      <td style={{
        padding: '8px 12px',
        fontSize: 13,
        backgroundColor: highlight && isDiff ? '#fff7e6' : 'transparent',
        verticalAlign: 'top',
      }}>
        {newVal || '-'}
      </td>
      <td style={{
        padding: '8px 12px',
        fontSize: 13,
        backgroundColor: highlight && isDiff ? '#fff7e6' : 'transparent',
        verticalAlign: 'top',
      }}>
        {matchVal || '-'}
      </td>
    </tr>
  );
}

export default function ClaimDetail() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectModalOpen, setRejectModalOpen] = useState(false);

  const fetchClaim = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/get_claim/${claimId}`);
      setClaim(data);
    } catch {
      message.error('Failed to load claim');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchClaim();
  }, [claimId]);

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await api.post(`/approve_claim/${claimId}`, { approved_by: 'Admin' });
      message.success('Claim approved');
      fetchClaim();
    } catch (err) {
      message.error('Approval failed: ' + (err.response?.data?.message || err.message));
    }
    setActionLoading(false);
  };

  const handleReject = async () => {
    setActionLoading(true);
    try {
      await api.post(`/reject_claim/${claimId}`, {
        rejected_by: 'Admin',
        reason: rejectReason || 'No reason provided',
      });
      message.success('Claim rejected');
      setRejectModalOpen(false);
      fetchClaim();
    } catch (err) {
      message.error('Rejection failed: ' + (err.response?.data?.message || err.message));
    }
    setActionLoading(false);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!claim) {
    return (
      <Result
        status="404"
        title="Claim Not Found"
        extra={<Button onClick={() => navigate('/claims')}>Back to List</Button>}
      />
    );
  }

  const statusCfg = STATUS_CONFIG[claim.status] || { color: 'default', label: claim.status };
  const claimData = claim.final_claim_data || claim.form_data || {};
  const canAct = ['pending_review', 'pending_approval'].includes(claim.status);
  const hasFraud = claim.Analysis_Result?.length > 0;
  const fraud = hasFraud ? claim.Analysis_Result[0] : null;
  const matchRecord = fraud?.Matching_Record;
  const analysis = fraud?.Analysis;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/claims')}>
            Back to Claims
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            Claim Review
            <Tag color={statusCfg.color} style={{ marginLeft: 12, verticalAlign: 'middle', fontSize: 13 }}>
              {statusCfg.label}
            </Tag>
          </Title>
        </Space>
        {canAct && (
          <Space>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              loading={actionLoading}
              onClick={handleApprove}
            >
              Approve
            </Button>
            <Button
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => setRejectModalOpen(true)}
            >
              Reject
            </Button>
          </Space>
        )}
      </div>

      {claim.status === 'approved' && (
        <Alert
          message="This claim has been approved"
          description={`Approved by: ${claim.approved_by || 'Unknown'} at ${claim.approval_timestamp || ''}`}
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {claim.status === 'rejected' && claim.rejection_reason && (
        <Alert
          message="This claim has been rejected"
          description={`Reason: ${claim.rejection_reason}`}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Fraud Alert Banner + Similarity Scores */}
      {hasFraud && (
        <Card
          style={{
            marginBottom: 20,
            borderLeft: '4px solid #ff4d4f',
            background: 'linear-gradient(135deg, #fff2f0 0%, #ffffff 100%)',
          }}
          bodyStyle={{ padding: '16px 24px' }}
        >
          <Row align="middle" justify="space-between">
            <Col>
              <Space align="center" size={12}>
                <WarningOutlined style={{ fontSize: 28, color: '#ff4d4f' }} />
                <div>
                  <Title level={4} style={{ margin: 0, color: '#cf1322' }}>
                    Potential Fraud Detected
                  </Title>
                  <Text type="secondary">
                    {fraud.Fraud_Types?.map((ft, j) => (
                      <Tag key={j} color="red" style={{ marginTop: 4 }}>{ft}</Tag>
                    ))}
                  </Text>
                </div>
              </Space>
            </Col>
            <Col>
              <Space size={24}>
                <SimilarityGauge value={fraud.Text_Similarity} label="Text Similarity" />
                {fraud.Image_Similarity != null && (
                  <SimilarityGauge value={fraud.Image_Similarity} label="Image Similarity" />
                )}
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {!hasFraud && (
        <Alert
          message="No Fraud Detected"
          description="This claim did not match any existing records above the fraud threshold."
          type="success"
          showIcon
          icon={<SafetyCertificateOutlined />}
          style={{ marginBottom: 20 }}
        />
      )}

      {/* AI Fraud Analysis Summary */}
      {analysis && (
        <Card
          title={
            <Space>
              <FileSearchOutlined style={{ color: '#1677ff' }} />
              <span>Fraud Detection Analysis</span>
            </Space>
          }
          style={{ marginBottom: 20 }}
        >
          {analysis.Summary && (
            <Paragraph style={{ fontSize: 14, marginBottom: 16 }}>
              {analysis.Summary}
            </Paragraph>
          )}

          {analysis['Fraud Indicators'] && (
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>Fraud Indicators:</Text>
              <List
                size="small"
                dataSource={Array.isArray(analysis['Fraud Indicators']) ? analysis['Fraud Indicators'] : []}
                renderItem={(item) => (
                  <List.Item style={{ padding: '6px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <Space align="start">
                      <ExclamationCircleOutlined style={{ color: '#faad14', marginTop: 4 }} />
                      <Text style={{ fontSize: 13 }}>{item}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </div>
          )}
        </Card>
      )}

      {/* Side-by-Side Image + Details Comparison */}
      {hasFraud && matchRecord && (
        <Card
          title={
            <Space>
              <ExclamationCircleOutlined style={{ color: '#faad14' }} />
              <span>Document Comparison - New Claim vs Matching Record</span>
            </Space>
          }
          style={{ marginBottom: 20 }}
        >
          {/* Images side by side */}
          <Row gutter={24} style={{ marginBottom: 24 }}>
            <Col xs={24} md={12}>
              <Card
                size="small"
                title={<Text strong style={{ color: '#1677ff' }}>New Claim Document</Text>}
                styles={{ body: { textAlign: 'center', padding: 12, minHeight: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' } }}
              >
                {claimData.Image_Path ? (
                  <Image
                    src={getImageUrl(claimData.Image_Path)}
                    alt="New claim document"
                    style={{ maxHeight: 300, objectFit: 'contain' }}
                    fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mge0aCSFgsw+SXWzGU1mQW4Ij8VBMAlGIHAOFBITGBqYAOA9UHBobEZoBFEJEBJWLx9AIcviAoYJBYlAh7AEgJCOxFjJkGBoCRGdmYGBgd4RQSwPwNyBLJ8kIRCILkHBgIGVv8HBYSE5JTUlFYulpaWl5QUF+fn5FQWFReUFpYU="
                  />
                ) : (
                  <Text type="secondary">No image available</Text>
                )}
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card
                size="small"
                title={<Text strong style={{ color: '#fa8c16' }}>Matching Record Document</Text>}
                styles={{ body: { textAlign: 'center', padding: 12, minHeight: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' } }}
              >
                {matchRecord.Image_Path ? (
                  <Image
                    src={getImageUrl(matchRecord.Image_Path)}
                    alt="Matching record document"
                    style={{ maxHeight: 300, objectFit: 'contain' }}
                    fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mge0aCSFgsw+SXWzGU1mQW4Ij8VBMAlGIHAOFBITGBqYAOA9UHBobEZoBFEJEBJWLx9AIcviAoYJBYlAh7AEgJCOxFjJkGBoCRGdmYGBgd4RQSwPwNyBLJ8kIRCILkHBgIGVv8HBYSE5JTUlFYulpaWl5QUF+fn5FQWFReUFpYU="
                  />
                ) : (
                  <Text type="secondary">No image available</Text>
                )}
              </Card>
            </Col>
          </Row>

          {/* Details comparison table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #f0f0f0' }}>
            <thead>
              <tr style={{ backgroundColor: '#fafafa', borderBottom: '2px solid #e8e8e8' }}>
                <th style={{ padding: '10px 12px', textAlign: 'left', width: 140, fontSize: 13 }}>Field</th>
                <th style={{ padding: '10px 12px', textAlign: 'left', fontSize: 13 }}>
                  <Tag color="blue">New Claim</Tag>
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'left', fontSize: 13 }}>
                  <Tag color="orange">Matching Record</Tag>
                </th>
              </tr>
            </thead>
            <tbody>
              <DetailRow label="IC / NRIC" newVal={claimData.IC} matchVal={matchRecord.IC} highlight />
              <DetailRow label="Patient Name" newVal={claimData.Name || claimData.Patient_Name} matchVal={matchRecord.Name} highlight />
              <DetailRow label="Age" newVal={claimData.Age} matchVal={matchRecord.Age} />
              <DetailRow label="Doctor" newVal={claimData.Doctor} matchVal={matchRecord.Doctor} highlight />
              <DetailRow label="Hospital" newVal={claimData.Hospital} matchVal={matchRecord.Hospital} highlight />
              <DetailRow label="Specialty" newVal={claimData.Specialty} matchVal={matchRecord.Specialty} />
              <DetailRow label="Admission" newVal={claimData.Date_Admission} matchVal={matchRecord.Date_Admission} highlight />
              <DetailRow label="Discharge" newVal={claimData.Date_Discharge} matchVal={matchRecord.Date_Discharge} highlight />
              <DetailRow label="Diagnosis" newVal={claimData.Diagnosis} matchVal={matchRecord.Diagnosis} highlight />
              <DetailRow label="Follow-up" newVal={claimData.Notes_for_Follow_up} matchVal={matchRecord.Notes_for_Follow_up} highlight />
            </tbody>
          </table>
        </Card>
      )}

      {/* Validation Messages */}
      {claim.validation_messages && (
        (claim.validation_messages.warnings?.length > 0 ||
         Object.keys(claim.validation_messages.updates || {}).length > 0) && (
          <Card title="Validation Messages" style={{ marginBottom: 20 }}>
            {claim.validation_messages.warnings?.map((w, i) => (
              <Alert key={i} message={w} type="warning" showIcon style={{ marginBottom: 8 }} />
            ))}
            {Object.keys(claim.validation_messages.updates || {}).length > 0 && (
              <Descriptions
                title="Fields Updated from Discharge Note"
                column={1}
                size="small"
                bordered
                style={{ marginTop: 8 }}
              >
                {Object.entries(claim.validation_messages.updates).map(([k, v]) => (
                  <Descriptions.Item label={k} key={k}>{v}</Descriptions.Item>
                ))}
              </Descriptions>
            )}
          </Card>
        )
      )}

      {/* Detailed Analysis Result */}
      {analysis && (
        <Card
          title={
            <Space>
              <FileSearchOutlined />
              <span>Detailed Analysis Result</span>
            </Space>
          }
          style={{ marginBottom: 20 }}
        >
          {analysis['Analysis Result'] && (
            <Alert
              message="Analysis Conclusion"
              description={analysis['Analysis Result']}
              type={analysis['Analysis Result']?.toLowerCase().includes('fraud') ? 'error' : 'warning'}
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {analysis['Patient Information'] && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>Patient Information: </Text>
              <Text>{analysis['Patient Information']}</Text>
            </div>
          )}

          {analysis['Diagnosis Comparison'] && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>Diagnosis Comparison: </Text>
              <Text>{analysis['Diagnosis Comparison']}</Text>
            </div>
          )}

          {analysis['Treatment Details'] && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>Treatment Details: </Text>
              <Text>{analysis['Treatment Details']}</Text>
            </div>
          )}

          {analysis['Typographical Errors'] && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>Typographical Errors: </Text>
              <Text>{analysis['Typographical Errors']}</Text>
            </div>
          )}

          {/* Render any other keys not explicitly handled */}
          {Object.entries(analysis)
            .filter(([k]) => ![
              'Summary', 'Fraud Indicators', 'Analysis Result',
              'Patient Information', 'Diagnosis Comparison',
              'Treatment Details', 'Typographical Errors',
            ].includes(k))
            .map(([k, v]) => (
              <div key={k} style={{ marginBottom: 12 }}>
                <Text strong>{k}: </Text>
                {Array.isArray(v) ? (
                  <ul style={{ margin: '4px 0 0 16px', paddingLeft: 0 }}>
                    {v.map((item, idx) => <li key={idx} style={{ fontSize: 13 }}>{item}</li>)}
                  </ul>
                ) : typeof v === 'object' ? (
                  <pre style={{ margin: '4px 0 0 0', fontSize: 12, whiteSpace: 'pre-wrap', background: '#fafafa', padding: 8, borderRadius: 4 }}>
                    {JSON.stringify(v, null, 2)}
                  </pre>
                ) : (
                  <Text>{String(v)}</Text>
                )}
              </div>
            ))}
        </Card>
      )}

      {/* Patient & Claim Info (collapsible at bottom for reference) */}
      <Card title="Patient & Claim Information" style={{ marginBottom: 20 }}>
        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
          <Descriptions.Item label="Claim ID">
            <Text copyable style={{ fontSize: 12 }}>{claimId}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Submitted At">{claim.timestamp || '-'}</Descriptions.Item>
          <Descriptions.Item label="Patient Name">
            {claimData.Name || claimData.Patient_Name || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="IC / NRIC">{claimData.IC || '-'}</Descriptions.Item>
          <Descriptions.Item label="Age">{claimData.Age || '-'}</Descriptions.Item>
          <Descriptions.Item label="Doctor">{claimData.Doctor || '-'}</Descriptions.Item>
          <Descriptions.Item label="Hospital">{claimData.Hospital || '-'}</Descriptions.Item>
          <Descriptions.Item label="Specialty">{claimData.Specialty || '-'}</Descriptions.Item>
          <Descriptions.Item label="Admission Date">{claimData.Date_Admission || '-'}</Descriptions.Item>
          <Descriptions.Item label="Discharge Date">{claimData.Date_Discharge || '-'}</Descriptions.Item>
          <Descriptions.Item label="Diagnosis" span={2}>{claimData.Diagnosis || '-'}</Descriptions.Item>
          <Descriptions.Item label="Follow-up Notes" span={2}>{claimData.Notes_for_Follow_up || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Reject Modal */}
      <Modal
        title="Reject Claim"
        open={rejectModalOpen}
        onOk={handleReject}
        onCancel={() => setRejectModalOpen(false)}
        confirmLoading={actionLoading}
        okText="Reject"
        okButtonProps={{ danger: true }}
      >
        <p>Please provide a reason for rejection:</p>
        <TextArea
          rows={4}
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          placeholder="Enter rejection reason..."
        />
      </Modal>
    </div>
  );
}
