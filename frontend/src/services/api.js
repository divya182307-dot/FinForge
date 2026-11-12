/**
 * FinAudit AI - Centralized API Service
 * Configured with Axios for all backend operations.
 */
import axios from 'axios';

const API_BASE_URL = import.meta?.env?.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getCompanies = async () => {
  const response = await apiClient.get('/companies');
  return response.data;
};

export const runAudit = async (ticker, period = 'FY2023') => {
  const response = await apiClient.post('/audit/run', { ticker, period });
  return response.data;
};

export const getAuditDetails = async (auditId) => {
  const response = await apiClient.get(`/audit/${auditId}`);
  return response.data;
};

export const getReviews = async (auditId = null) => {
  const url = auditId ? `/reviews?audit_id=${auditId}` : '/reviews';
  const response = await apiClient.get(url);
  return response.data;
};

export const submitReviewDecision = async (reviewId, { decision, correctedValue, reason, comments }) => {
  const payload = {
    decision,
    corrected_value: correctedValue ? parseFloat(correctedValue) : null,
    reason,
    comments,
  };
  const response = await apiClient.post(`/reviews/${reviewId}/decision`, payload);
  return response.data;
};

export const getAuditHistory = async (auditId) => {
  const response = await apiClient.get(`/audit/${auditId}/history`);
  return response.data;
};

export const getAccuracyReport = async (auditId) => {
  const response = await apiClient.get(`/audit/${auditId}/report`);
  return response.data;
};

export const getDashboardSummary = async () => {
  const response = await apiClient.get('/dashboard/summary');
  return response.data;
};

export const getWorkflowState = async (auditId) => {
  const response = await apiClient.get(`/workflow/${auditId}`);
  return response.data;
};

export const getAllAudits = async () => {
  const response = await apiClient.get('/audits');
  return response.data;
};

export default {
  getCompanies,
  runAudit,
  getAuditDetails,
  getReviews,
  submitReviewDecision,
  getAuditHistory,
  getAccuracyReport,
  getDashboardSummary,
  getWorkflowState,
  getAllAudits,
};

