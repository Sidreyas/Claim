import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  DatePicker,
  Button,
  Upload,
  Row,
  Col,
  Typography,
  Alert,
  Spin,
  Result,
  Tag,
  Descriptions,
  Image,
  Space,
  Divider,
  message,
} from 'antd';
import {
  InboxOutlined,
  SendOutlined,
  CloseOutlined,
  FileImageOutlined,
  CheckCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import api from '../api/client';

const { Title, Paragraph, Text } = Typography;
const { Dragger } = Upload;
const { TextArea } = Input;

export default function ClaimForm() {
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [ocrData, setOcrData] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleUpload = async (info) => {
    const file = info.file;
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const { data } = await api.post('/upload_image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (data.status === 'success') {
        setUploadedFile({
          filename: data.filename,
          path: data.image_path,
          preview: URL.createObjectURL(file),
        });
        message.success('Document uploaded successfully');

        setOcrLoading(true);
        try {
          const ocrRes = await api.get(`/do_ocr?file=${data.filename}`, { timeout: 300000 });
          const extracted = Array.isArray(ocrRes.data) ? ocrRes.data[0] : ocrRes.data;

          if (extracted.error) {
            message.warning(extracted.error);
          } else {
            setOcrData(extracted);
            form.setFieldsValue({
              Patient_Name: extracted['Name'] || '',
              IC: extracted['IC or NRIC'] || '',
              Date_Admission: null,
              Date_Discharge: null,
            });
            message.success('Document analysed successfully');
          }
        } catch (ocrErr) {
          const errMsg = ocrErr.response?.data?.error
            || ocrErr.response?.data?.message
            || 'OCR extraction failed. Please fill the form manually.';
          message.warning(errMsg);
        }
        setOcrLoading(false);
      }
    } catch (err) {
      message.error('Upload failed: ' + (err.response?.data?.message || err.message));
    }
    setUploading(false);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const formPayload = {
        IC: values.IC || '',
        Patient_Name: values.Patient_Name || '',
        Age: '',
        Doctor: '',
        Specialty: 'General Medicine',
        Hospital: '',
        Date_Admission: values.Date_Admission?.format('DD/MM/YYYY') || '',
        Date_Discharge: values.Date_Discharge?.format('DD/MM/YYYY') || '',
        Diagnosis: '',
        Image_Path: uploadedFile?.filename || '',
        Notes_for_Follow_up: '',
      };

      const ocrPayload = {
        IC: ocrData?.['IC or NRIC'] || '',
        Patient_Name: ocrData?.['Name'] || '',
        Age: ocrData?.['Age'] || '',
        Doctor: ocrData?.['Name of Medical Officer'] || '',
        Specialty: 'General Medicine',
        Hospital: ocrData?.['Hospital Name'] || '',
        Date_Admission: ocrData?.['Date of Admission'] || '',
        Date_Discharge: ocrData?.['Date of Discharge'] || '',
        Diagnosis: ocrData?.['Diagnosis'] || '',
        Notes_for_Follow_up: ocrData?.['Follow up Notes'] || '',
        Image_Path: uploadedFile?.filename || '',
      };

      const { data } = await api.post('/submit_claim', {
        form_data: formPayload,
        ocr_data: ocrPayload,
      });

      setSubmitResult(data);
      message.success('Claim submitted successfully');
    } catch (err) {
      if (err.response?.data) {
        setSubmitResult(err.response.data);
      } else if (err.errorFields) {
        return;
      } else {
        message.error('Submission failed: ' + err.message);
      }
    }
    setSubmitting(false);
  };

  const handleReset = () => {
    setUploadedFile(null);
    setOcrData(null);
    setSubmitResult(null);
    form.resetFields();
  };

  if (submitResult) {
    return (
      <div>
        <Title level={3}>Claim Request Form</Title>
        <Card>
          <Result
            status={submitResult.status === 'rejected' ? 'error' : 'success'}
            title={
              submitResult.status === 'rejected'
                ? 'Claim Rejected'
                : submitResult.status === 'pending_approval'
                ? 'Claim Needs Review (Potential Fraud Detected)'
                : 'Claim Submitted Successfully'
            }
            subTitle={`Claim ID: ${submitResult.claim_id || 'N/A'}`}
            extra={[
              <Button
                key="view"
                type="primary"
                onClick={() =>
                  submitResult.claim_id && navigate(`/claims/${submitResult.claim_id}`)
                }
              >
                View Claim Details
              </Button>,
              <Button key="new" onClick={handleReset}>
                Submit Another Claim
              </Button>,
              <Button key="list" onClick={() => navigate('/')}>
                Back to Claim List
              </Button>,
            ]}
          />

          {submitResult.errors?.length > 0 && (
            <Alert
              type="error"
              message="Validation Errors"
              description={submitResult.errors.map((e, i) => (
                <div key={i}>{e}</div>
              ))}
              style={{ marginTop: 16 }}
            />
          )}

          {submitResult.validation_messages?.warnings?.length > 0 && (
            <Alert
              type="warning"
              message="Warnings"
              description={submitResult.validation_messages.warnings.map((w, i) => (
                <div key={i}>{w}</div>
              ))}
              style={{ marginTop: 16 }}
            />
          )}

          {submitResult.Analysis_Result?.length > 0 && (
            <Card title="Fraud Analysis" style={{ marginTop: 16 }} type="inner">
              {submitResult.Analysis_Result.map((fr, i) => (
                <Card
                  key={i}
                  size="small"
                  style={{ marginBottom: 12 }}
                  title={`Match #${i + 1} - IC: ${fr.Matched_IC}`}
                >
                  <p>
                    <strong>Text Similarity:</strong>{' '}
                    <Tag color={fr.Text_Similarity > 0.9 ? 'red' : 'orange'}>
                      {(fr.Text_Similarity * 100).toFixed(1)}%
                    </Tag>
                  </p>
                  {fr.Image_Similarity != null && (
                    <p>
                      <strong>Image Similarity:</strong>{' '}
                      <Tag color={fr.Image_Similarity > 0.9 ? 'red' : 'orange'}>
                        {(fr.Image_Similarity * 100).toFixed(1)}%
                      </Tag>
                    </p>
                  )}
                </Card>
              ))}
            </Card>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Title level={3}>Claim Request Form</Title>

      <Row gutter={24}>
        <Col xs={24} lg={14}>
          <Card title="Claim Details" style={{ marginBottom: 16 }}>
            <Form form={form} layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="Patient_Name"
                    label="Patient Name"
                    rules={[{ required: true, message: 'Patient name is required' }]}
                  >
                    <Input placeholder="Enter patient name" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="IC"
                    label="NRIC"
                    rules={[{ required: true, message: 'NRIC is required' }]}
                  >
                    <Input placeholder="e.g. 960707-14-6352" />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="Date_Admission" label="Date of Admission">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="Date_Discharge" label="Date of Discharge">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>

            <Divider orientation="left">Discharge Note</Divider>

            <Spin
              spinning={uploading || ocrLoading}
              tip={ocrLoading ? 'Analysing document...' : 'Uploading...'}
            >
              <Dragger
                name="file"
                accept=".jpg,.jpeg,.png,.gif,.pdf"
                showUploadList={false}
                beforeUpload={() => false}
                onChange={(info) => {
                  if (info.file) handleUpload(info);
                }}
                style={{ marginBottom: 16 }}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">
                  Drag and drop your documents here
                </p>
                <p className="ant-upload-hint">or click here to upload</p>
              </Dragger>
            </Spin>

            {uploadedFile && (
              <Alert
                message={
                  <Space>
                    <FileImageOutlined />
                    <span>Uploaded: {uploadedFile.filename}</span>
                    {ocrData && (
                      <Tag color="green" icon={<CheckCircleOutlined />}>
                        OCR Complete
                      </Tag>
                    )}
                  </Space>
                }
                type="success"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {uploadedFile?.preview && (
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <Image
                  src={uploadedFile.preview}
                  alt="Discharge note"
                  style={{ maxHeight: 300, maxWidth: '100%' }}
                />
              </div>
            )}

            {ocrData && (
              <Card size="small" title="Extracted Data from Document" type="inner">
                <Descriptions column={1} size="small" bordered>
                  {Object.entries(ocrData).map(([key, val]) => (
                    <Descriptions.Item label={key} key={key}>
                      {val || <Text type="secondary">-</Text>}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            )}

            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <Button icon={<CloseOutlined />} onClick={() => navigate('/')}>
                Cancel
              </Button>
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={submitting}
                onClick={handleSubmit}
                disabled={!uploadedFile}
              >
                Submit
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <BulbOutlined />
                Submitting Your Claim: Tips for Accuracy and Speed
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <ul style={{ paddingLeft: 20, margin: 0 }}>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Be Thorough and Accurate:</Text>{' '}
                <Text type="secondary">
                  Double-check all the information you provide for accuracy and completeness.
                </Text>
              </li>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Clearly Explain What Happened:</Text>{' '}
                <Text type="secondary">
                  Use clear and concise language. Avoid jargon or ambiguity.
                </Text>
              </li>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Upload Legible Documents:</Text>{' '}
                <Text type="secondary">
                  Ensure scanned or photographed documents are clear and easy to read.
                </Text>
              </li>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Don&apos;t Delay:</Text>{' '}
                <Text type="secondary">
                  Submit your claim as soon as reasonably possible after the incident.
                </Text>
              </li>
            </ul>
          </Card>

          <Card title="What to Expect After Submission">
            <ul style={{ paddingLeft: 20, margin: 0 }}>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Claim Number:</Text>{' '}
                <Text type="secondary">
                  You will receive a unique claim number for your reference.
                </Text>
              </li>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Review Process:</Text>{' '}
                <Text type="secondary">
                  Our team will review your information and may contact you if needed.
                </Text>
              </li>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Communication:</Text>{' '}
                <Text type="secondary">
                  We will keep you informed about the progress and status of your claim.
                </Text>
              </li>
              <li style={{ marginBottom: 12 }}>
                <Text strong>Honesty is Key:</Text>{' '}
                <Text type="secondary">
                  Be truthful and transparent throughout the process.
                </Text>
              </li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
