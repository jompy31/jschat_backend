"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const axios_1 = __importDefault(require("axios"));
const API_BASE_URL = 'https://sandboxapicore.imaginasoft.pt/api/v1';
const USERNAME = 'sandboxapi_nsapi_266844693';
const PASSWORD = 'ieN83R8ilgqPu6RCEsUFdg9H22OzfKG2wjSoSsnt@AqYKsntqJIF&Ux2$2O1';
class AuthService {
    static async fetchAuthToken() {
        try {
            const response = await axios_1.default.post(`${API_BASE_URL}/Authentication`, {
                username: USERNAME,
                password: PASSWORD,
            }, {
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            // Verifique se o token foi retornado corretamente
            if (!response.data.token) {
                throw new Error('Token not found in the response');
            }
            return response.data.token;
        }
        catch (error) {
            // Melhore o tratamento de erros
            if (error.response) {
                // Erro retornado pela API
                throw new Error(`Failed to authenticate: ${error.response.status} - ${error.response.data.message || 'No error message'}`);
            }
            else if (error.request) {
                // Erro de conexão
                throw new Error('Failed to authenticate: No response received from the server');
            }
            else {
                // Erro genérico
                throw new Error('Failed to authenticate: ' + error.message);
            }
        }
    }
    static async getAuthToken() {
        // Se o token já estiver em cache, retorne-o
        if (this.token) {
            return this.token;
        }
        // Caso contrário, obtenha um novo token
        this.token = await this.fetchAuthToken();
        return this.token;
    }
    // Método para limpar o cache do token (útil para logout ou token expirado)
    static clearToken() {
        this.token = null;
    }
}
AuthService.token = null; // Cache do token
exports.default = AuthService;
