"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.handleAppointmentRequest = exports.checkAppointmentAvailability = void 0;
const imaginasoftApi_1 = require("./imaginasoftApi");
// Função para verificar disponibilidade
const checkAppointmentAvailability = async (medicId, date, time) => {
    const appointments = await (0, imaginasoftApi_1.getAppointments)({ medicId, date, time });
    return { available: appointments.length === 0, appointments };
};
exports.checkAppointmentAvailability = checkAppointmentAvailability;
const handleAppointmentRequest = async (patientInfo, medicId, date, time) => {
    // Primeiro, criar paciente na Imaginasoft (se ainda não existir)
    const patient = await (0, imaginasoftApi_1.createPatient)(patientInfo);
    // Verificar disponibilidade utilizando método ajustado acima
    const availability = await (0, exports.checkAppointmentAvailability)(medicId, date, time);
    if (availability.available) {
        // Realizar agendamento utilizando método existente createAppointment
        const appointment = await (0, imaginasoftApi_1.createAppointment)({
            patientId: patient.id,
            medicId,
            date,
            time
        });
        return { success: true, appointment };
    }
    else {
        return { success: false, message: 'Horário indisponível', availability };
    }
};
exports.handleAppointmentRequest = handleAppointmentRequest;
