"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const imaginasoftApi_1 = require("../services/imaginasoftApi");
const router = (0, express_1.Router)();
// --- Rotas de Clinics ---
router.get('/clinics', async (req, res) => {
    try {
        const clinics = await (0, imaginasoftApi_1.getClinics)();
        res.json(clinics);
    }
    catch (error) {
        console.error('Erro ao obter clínicas:', error);
        res.status(500).json({ error: 'Erro ao obter clínicas', details: error.message });
    }
});
router.get('/clinics/:id', async (req, res) => {
    try {
        const clinic = await (0, imaginasoftApi_1.getClinicById)(req.params.id);
        res.json(clinic);
    }
    catch (error) {
        console.error('Erro ao obter detalhes da clínica:', error);
        res.status(500).json({ error: 'Erro ao obter detalhes da clínica', details: error.message });
    }
});
// --- Rotas de Patients ---
router.get('/patients', async (req, res) => {
    try {
        const patients = await (0, imaginasoftApi_1.getPatients)(req.query);
        res.json(patients);
    }
    catch (error) {
        console.error('Erro ao obter pacientes:', error);
        res.status(500).json({ error: 'Erro ao obter pacientes', details: error.message });
    }
});
router.get('/patients/:id', async (req, res) => {
    try {
        const patient = await (0, imaginasoftApi_1.getPatientById)(req.params.id);
        res.json(patient);
    }
    catch (error) {
        console.error('Erro ao obter detalhes do paciente:', error);
        res.status(500).json({ error: 'Erro ao obter detalhes do paciente', details: error.message });
    }
});
router.post('/patients', async (req, res) => {
    try {
        const newPatient = await (0, imaginasoftApi_1.createPatient)(req.body);
        res.status(201).json(newPatient);
    }
    catch (error) {
        console.error('Erro ao criar paciente:', error);
        res.status(500).json({ error: 'Erro ao criar paciente', details: error.message });
    }
});
router.put('/patients/:id', async (req, res) => {
    try {
        const updatedPatient = await (0, imaginasoftApi_1.updatePatient)(req.params.id, req.body);
        res.json(updatedPatient);
    }
    catch (error) {
        console.error('Erro ao atualizar paciente:', error);
        res.status(500).json({ error: 'Erro ao atualizar paciente', details: error.message });
    }
});
// --- Rotas de Appointments ---
router.get('/appointments', async (req, res) => {
    try {
        const appointments = await (0, imaginasoftApi_1.getAppointments)(req.query);
        res.json(appointments);
    }
    catch (error) {
        console.error('Erro ao obter agendamentos:', error);
        res.status(500).json({ error: 'Erro ao obter agendamentos', details: error.message });
    }
});
router.get('/appointments/:id', async (req, res) => {
    try {
        const appointment = await (0, imaginasoftApi_1.getAppointmentById)(req.params.id);
        res.json(appointment);
    }
    catch (error) {
        console.error('Erro ao obter detalhes do agendamento:', error);
        res.status(500).json({ error: 'Erro ao obter detalhes do agendamento', details: error.message });
    }
});
router.post('/appointments', async (req, res) => {
    try {
        const newAppointment = await (0, imaginasoftApi_1.createAppointment)(req.body);
        res.status(201).json(newAppointment);
    }
    catch (error) {
        console.error('Erro ao criar agendamento:', error);
        res.status(500).json({ error: 'Erro ao criar agendamento', details: error.message });
    }
});
router.put('/appointments/:id', async (req, res) => {
    try {
        const updatedAppointment = await (0, imaginasoftApi_1.updateAppointment)(req.params.id, req.body);
        res.json(updatedAppointment);
    }
    catch (error) {
        console.error('Erro ao atualizar agendamento:', error);
        res.status(500).json({ error: 'Erro ao atualizar agendamento', details: error.message });
    }
});
exports.default = router;
