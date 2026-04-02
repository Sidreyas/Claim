import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Typography, Row, Col, Statistic, Button, Space, Empty, Modal, message } from 'antd';
import {
  PlusCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  UnorderedListOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import api from '../api/client';

const { Title } = Typography;

const STATUS_CONFIG = {
  pending_review: { color: 'blue', label: 'New' },
  pending_approval: { color: 'orange', label: 'Pending' },
  approved: { color: 'green', label: 'Reviewed' },
  rejected: { color: 'red', label: 'Rejected' },
  processed: { color: 'purple', label: 'Under Review' },
};

export default function ClaimList() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState(null);
  const navigate = useNavigate();

  const fetchClaims = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/get_claims');
      const list = Object.entries(data).map(([id, claim]) => ({
        key: id,
        claim_id: id,
        ...claim,
      }));
      setClaims(list);
    } catch {
      setClaims([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchClaims();
  }, []);

  const handleCleanupAll = () => {
    Modal.confirm({
      title: 'Clear all claims and FAISS storage?',
      content:
        'This removes all pending claims and resets the fraud detection database. New claims will not be compared against old records.',
      okText: 'Clear all',
      okType: 'danger',
      onOk: async () => {
        try {
          const { data } = await api.delete('/claims');
          if (data.text_ntotal_after_clear !== 0 || data.len_records_after_clear !== 0) {
            message.warning(
              `Clear finished but FAISS still reports vectors (text=${data.text_ntotal_after_clear}, records=${data.len_records_after_clear}). Restart the API and try again.`,
            );
          } else {
            message.success('All claims and FAISS storage cleared');
          }
          await fetchClaims();
        } catch (e) {
          message.error(
            e?.response?.data?.message || e?.message || 'Failed to clear claims',
          );
        }
      },
    });
  };

  const statusCounts = claims.reduce((acc, c) => {
    const status = c.status || 'unknown';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});

  const filteredClaims = activeFilter
    ? claims.filter((c) => c.status === activeFilter)
    : claims;

  const summaryCards = [
    {
      title: 'My List',
      count: claims.length,
      color: '#1890ff',
      icon: <UnorderedListOutlined />,
      filter: null,
    },
    {
      title: 'New',
      count: statusCounts['pending_review'] || 0,
      color: '#1890ff',
      icon: <PlusCircleOutlined />,
      filter: 'pending_review',
    },
    {
      title: 'Pending',
      count: statusCounts['pending_approval'] || 0,
      color: '#fa8c16',
      icon: <ClockCircleOutlined />,
      filter: 'pending_approval',
    },
    {
      title: 'Under Review',
      count: statusCounts['processed'] || 0,
      color: '#722ed1',
      icon: <SyncOutlined />,
      filter: 'processed',
    },
    {
      title: 'Reviewed',
      count: (statusCounts['approved'] || 0) + (statusCounts['rejected'] || 0),
      color: '#52c41a',
      icon: <CheckCircleOutlined />,
      filter: 'reviewed',
    },
  ];

  const columns = [
    {
      title: 'Claim ID',
      dataIndex: 'claim_id',
      key: 'claim_id',
      width: 130,
      render: (id) => id?.slice(0, 8) + '...',
    },
    {
      title: 'IC NUMBER',
      key: 'ic',
      render: (_, r) =>
        r.final_claim_data?.IC || r.form_data?.IC || '-',
    },
    {
      title: 'PATIENT NAME',
      key: 'name',
      render: (_, r) =>
        r.final_claim_data?.Name ||
        r.final_claim_data?.Patient_Name ||
        r.form_data?.Patient_Name ||
        '-',
    },
    {
      title: 'DOCTOR NAME',
      key: 'doctor',
      render: (_, r) =>
        r.final_claim_data?.Doctor || r.form_data?.Doctor || '-',
    },
    {
      title: 'HOSPITAL',
      key: 'hospital',
      render: (_, r) =>
        r.final_claim_data?.Hospital || r.form_data?.Hospital || '-',
    },
    {
      title: 'ADMISSION DATE',
      key: 'admission',
      render: (_, r) =>
        r.final_claim_data?.Date_Admission ||
        r.form_data?.Date_Admission ||
        '-',
    },
    {
      title: 'SIMILARITY SCORE',
      key: 'similarity',
      render: (_, r) => {
        const results = r.Analysis_Result;
        if (results && results.length > 0) {
          const score = results[0].Text_Similarity;
          return score != null ? `${(score * 100).toFixed(1)}%` : '-';
        }
        return '-';
      },
    },
    {
      title: 'CLAIM Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const cfg = STATUS_CONFIG[status] || { color: 'default', label: status };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: 'DETAILS',
      key: 'details',
      render: (_, r) => (
        <Button type="link" size="small" onClick={() => navigate(`/details/${r.claim_id}`)}>
          Review
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        Claim List
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        {summaryCards.map((card) => (
          <Col key={card.title} xs={12} sm={8} md={6} lg={4}>
            <Card
              hoverable
              size="small"
              onClick={() => setActiveFilter(card.filter === activeFilter ? null : card.filter)}
              style={{
                borderTop: `3px solid ${card.color}`,
                cursor: 'pointer',
                background: card.filter === activeFilter ? '#e6f7ff' : '#fff',
              }}
            >
              <Statistic
                title={card.title}
                value={card.count}
                prefix={card.icon}
                valueStyle={{ color: card.color, fontSize: 24 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Button type="primary" icon={<PlusCircleOutlined />} onClick={() => navigate('/claimrequestform')}>
            New Claim
          </Button>
          <Button icon={<SyncOutlined />} onClick={fetchClaims} loading={loading}>
            Refresh
          </Button>
          <Button danger icon={<DeleteOutlined />} onClick={handleCleanupAll} disabled={claims.length === 0}>
            Clear all claims
          </Button>
          {activeFilter && (
            <Button onClick={() => setActiveFilter(null)}>Clear Filter</Button>
          )}
        </Space>

        <Table
          columns={columns}
          dataSource={filteredClaims}
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true }}
          scroll={{ x: 1000 }}
          locale={{ emptyText: <Empty description="No data" /> }}
          size="middle"
        />
      </Card>
    </div>
  );
}
