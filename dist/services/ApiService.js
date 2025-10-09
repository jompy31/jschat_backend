"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const axios_1 = __importDefault(require("axios"));
const ApiAuthService_1 = __importDefault(require("./ApiAuthService")); // Serviço de autenticação para obter o token
const API_BASE_URL = 'https://sandboxapicore.imaginasoft.pt/api/v1';
class ApiService {
    static async getAuthToken() {
        return await ApiAuthService_1.default.getAuthToken(); // Obter o token de autenticação
    }
    // Endpoint para autenticação (já implementado no AuthService)
    // ...
    // Endpoint para obter todos os usuários
    static async getUsers() {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.get(`${API_BASE_URL}/users`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to fetch users: ' + error.message);
        }
    }
    // Endpoint para obter um usuário por ID
    static async getUserById(id) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.get(`${API_BASE_URL}/users/${id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to fetch user by ID: ' + error.message);
        }
    }
    // Endpoint para criar um novo usuário
    static async createUser(userData) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.post(`${API_BASE_URL}/users`, userData, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to create user: ' + error.message);
        }
    }
    // Endpoint para atualizar um usuário
    static async updateUser(id, userData) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.put(`${API_BASE_URL}/users/${id}`, userData, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to update user: ' + error.message);
        }
    }
    // Endpoint para deletar um usuário
    static async deleteUser(id) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.delete(`${API_BASE_URL}/users/${id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to delete user: ' + error.message);
        }
    }
    // Endpoint para obter todos os produtos
    static async getProducts() {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.get(`${API_BASE_URL}/products`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to fetch products: ' + error.message);
        }
    }
    // Endpoint para obter um produto por ID
    static async getProductById(id) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.get(`${API_BASE_URL}/products/${id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to fetch product by ID: ' + error.message);
        }
    }
    // Endpoint para criar um novo produto
    static async createProduct(productData) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.post(`${API_BASE_URL}/products`, productData, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to create product: ' + error.message);
        }
    }
    // Endpoint para atualizar um produto
    static async updateProduct(id, productData) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.put(`${API_BASE_URL}/products/${id}`, productData, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to update product: ' + error.message);
        }
    }
    // Endpoint para deletar um produto
    static async deleteProduct(id) {
        const token = await this.getAuthToken();
        try {
            const response = await axios_1.default.delete(`${API_BASE_URL}/products/${id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            return response.data;
        }
        catch (error) {
            throw new Error('Failed to delete product: ' + error.message);
        }
    }
}
exports.default = ApiService;
