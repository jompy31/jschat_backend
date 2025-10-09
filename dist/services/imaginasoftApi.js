"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.updatePatient = exports.createPatient = exports.getPatientById = exports.getPatients = exports.getClinicById = exports.getClinics = exports.updateAppointment = exports.createAppointment = exports.getAppointmentById = exports.getAppointments = void 0;
const axios_1 = __importDefault(require("axios"));
const api = axios_1.default.create({
    baseURL: process.env.IMAGINASOFT_BASE_URL,
    auth: {
        username: process.env.IMAGINASOFT_USER || '',
        password: process.env.IMAGINASOFT_PASSWORD || ''
    }
});
// --- Appointments ---
const getAppointments = async (params = {}) => {
    const response = await api.get('/Appointments', { params });
    return response.data;
};
exports.getAppointments = getAppointments;
const getAppointmentById = async (appointmentId) => {
    const response = await api.get(`/Appointments/${appointmentId}`);
    return response.data;
};
exports.getAppointmentById = getAppointmentById;
const createAppointment = async (appointmentData) => {
    const response = await api.post('/Appointments', appointmentData);
    return response.data;
};
exports.createAppointment = createAppointment;
const updateAppointment = async (appointmentId, appointmentData) => {
    const response = await api.put(`/Appointments/${appointmentId}`, appointmentData);
    return response.data;
};
exports.updateAppointment = updateAppointment;
// --- Clinic ---
const getClinics = async () => {
    const response = await api.get('/Clinic');
    return response.data;
};
exports.getClinics = getClinics;
const getClinicById = async (clinicId) => {
    const response = await api.get(`/Clinic/${clinicId}`);
    return response.data;
};
exports.getClinicById = getClinicById;
// --- Patients ---
const getPatients = async (params = {}) => {
    const response = await api.get('/Patients', { params });
    return response.data;
};
exports.getPatients = getPatients;
const getPatientById = async (patientId) => {
    const response = await api.get(`/Patients/${patientId}`);
    return response.data;
};
exports.getPatientById = getPatientById;
const createPatient = async (patientData) => {
    const response = await api.post('/Patients', patientData);
    return response.data;
};
exports.createPatient = createPatient;
const updatePatient = async (patientId, patientData) => {
    const response = await api.put(`/Patients/${patientId}`, patientData);
    return response.data;
};
exports.updatePatient = updatePatient;
