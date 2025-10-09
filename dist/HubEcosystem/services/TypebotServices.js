"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TypebotService = void 0;
const axios_1 = __importDefault(require("axios"));
class TypebotService {
    constructor(apiUrl, token) {
        this.apiUrl = apiUrl;
        this.token = token;
    }
    async getWorkspaces() {
        const config = {
            method: "get",
            url: `${this.apiUrl}/api/v1/workspaces`,
            headers: {
                Authorization: `Bearer ${this.token}`
            }
        };
        try {
            const response = await (0, axios_1.default)(config);
            return response.data;
        }
        catch (error) {
            console.error(error);
            throw error;
        }
    }
    async startChat(publicId, message, queueValues, nome, numero, ticketId) {
        const startChatConfig = {
            method: "post",
            url: `${this.apiUrl}/api/v1/typebots/${publicId}/startChat`,
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${this.token}`
            },
            data: {
                message,
                isStreamEnabled: true,
                isOnlyRegistering: false,
                prefilledVariables: {
                    "fila1": queueValues[0] || "",
                    "fila2": queueValues[1] || "",
                    "fila3": queueValues[2] || "",
                    "fila4": queueValues[3] || "",
                    "fila5": queueValues[4] || "",
                    "fila6": queueValues[5] || "",
                    "fila7": queueValues[6] || "",
                    "fila8": queueValues[7] || "",
                    "fila9": queueValues[8] || "",
                    "fila10": queueValues[9] || "",
                    "fila11": queueValues[10] || "",
                    "fila12": queueValues[11] || "",
                    "fila13": queueValues[12] || "",
                    "fila14": queueValues[13] || "",
                    "fila15": queueValues[14] || "",
                    "fila16": queueValues[15] || "",
                    "fila17": queueValues[16] || "",
                    "fila18": queueValues[17] || "",
                    "fila19": queueValues[18] || "",
                    "fila20": queueValues[19] || "",
                    "nome": nome,
                    "numero": numero,
                    "ticketId": ticketId,
                }
            }
        };
        try {
            const response = await (0, axios_1.default)(startChatConfig);
            return response.data;
        }
        catch (error) {
            console.error(error);
            throw error;
        }
    }
    async startNewChat(publicId, queueValues, nome, numero) {
        const startChatConfig = {
            method: "post",
            url: `${this.apiUrl}/api/v1/typebots/${publicId}/startChat`,
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${this.token}`
            },
            data: {
                isStreamEnabled: true,
                isOnlyRegistering: true,
                prefilledVariables: {
                    "fila1": queueValues[0] || "",
                    "fila2": queueValues[1] || "",
                    "fila3": queueValues[2] || "",
                    "fila4": queueValues[3] || "",
                    "fila5": queueValues[4] || "",
                    "fila6": queueValues[5] || "",
                    "fila7": queueValues[6] || "",
                    "fila8": queueValues[7] || "",
                    "fila9": queueValues[8] || "",
                    "fila10": queueValues[9] || "",
                    "fila11": queueValues[10] || "",
                    "fila12": queueValues[11] || "",
                    "fila13": queueValues[12] || "",
                    "fila14": queueValues[13] || "",
                    "fila15": queueValues[14] || "",
                    "fila16": queueValues[15] || "",
                    "fila17": queueValues[16] || "",
                    "fila18": queueValues[17] || "",
                    "fila19": queueValues[18] || "",
                    "fila20": queueValues[19] || "",
                    "nome": nome,
                    "numero": numero,
                }
            }
        };
        try {
            const response = await (0, axios_1.default)(startChatConfig);
            return response.data;
        }
        catch (error) {
            console.error(error);
            throw error;
        }
    }
    async continueChat(sessionId, message) {
        const continueChatConfig = {
            method: "post",
            url: `${this.apiUrl}/api/v1/sessions/${sessionId}/continueChat`,
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${this.token}`
            },
            data: {
                message
            }
        };
        try {
            const response = await (0, axios_1.default)(continueChatConfig);
            return response.data;
        }
        catch (error) {
            console.error(error);
            throw error;
        }
    }
}
exports.TypebotService = TypebotService;
