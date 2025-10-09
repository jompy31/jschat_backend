"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
// backend/src/routes/clinicChatRoutes.ts
const express_1 = require("express");
const ClinicChatService_1 = require("../services/ClinicChatService");
const router = (0, express_1.Router)();
router.post('/clinic-schedule', async (req, res) => {
    const { patientInfo, medicId, date, time } = req.body;
    try {
        const result = await (0, ClinicChatService_1.handleAppointmentRequest)(patientInfo, medicId, date, time);
        res.json(result);
    }
    catch (error) {
        console.error('Erro ao agendar consulta:', error);
        res.status(500).json({ error: 'Erro interno ao agendar consulta', details: error.message });
    }
});
exports.default = router;
