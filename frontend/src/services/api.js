import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const classificarReclamacao = async (texto) => {
  const response = await api.post('/classify', { texto });
  return response.data;
};

export const uploadCSV = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload-csv', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const listarReclamacoes = async () => {
  const response = await api.get('/tickets');
  return response.data;
};

export const obterMetricas = async () => {
  const response = await api.get('/metrics');
  return response.data;
};

export const exportarDados = async (format) => {
  const response = await api.get(`/export?format=${format}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const limparReclamacoes = async () => {
  const response = await api.delete('/tickets');
  return response.data;
};

export default api;