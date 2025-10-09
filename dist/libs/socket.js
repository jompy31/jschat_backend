"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getIO = exports.initIO = void 0;
const socket_io_1 = require("socket.io");
const AppError_1 = __importDefault(require("../errors/AppError"));
const User_1 = __importDefault(require("../models/User"));
let io;
const initIO = (httpServer) => {
    io = new socket_io_1.Server(httpServer, {
        allowRequest: (req, callback) => {
            const isOriginValid = req.headers.origin;
            callback(null, isOriginValid === process.env.FRONTEND_URL);
        },
        cors: {
            origin: process.env.FRONTEND_URL
        }
    });
    // if (process.env.SOCKET_ADMIN && JSON.parse(process.env.SOCKET_ADMIN)) {
    //   User.findByPk(1).then(
    //     (adminUser) => {
    //       instrument(io, {
    //         auth: {
    //           type: "basic",
    //           username: adminUser.email,
    //           password: adminUser.passwordHash
    //         },
    //         mode: "development",
    //       });
    //     }
    //   );
    // }
    const workspaces = io.of(/^\/\w+$/);
    workspaces.on("connection", socket => {
        const { userId } = socket.handshake.query;
        // Caso o userId seja passado, armazene no socket
        if (userId) {
            socket.data.userId = userId;
        }
        let offlineTimeout = null;
        // Quando o cliente se desconectar
        socket.on("disconnect", async () => {
            const userId = socket.data.userId;
            console.log(`Client disconnected: ${socket.id}`);
            if (userId) {
                // Inicia o timer de 60 segundos se tiver necessidade
                offlineTimeout = setTimeout(async () => {
                    try {
                        // Atualiza o status do usuário para offline instant
                        await User_1.default.update({ online: false }, { where: { id: userId } });
                        console.log(`User ${userId} marcado como off-line após fechar o navegador`);
                    }
                    catch (error) {
                        console.error("Erro ao marcar o usuário como offline:", error);
                    }
                }, 0); // instant para marcar como offline
            }
        });
        // Quando o cliente reconectar
        socket.on('reconnect', async () => {
            const userId = socket.data.userId;
            console.log(`Client reconnected: ${socket.id}`);
            if (offlineTimeout) {
                // Se o cliente reconectar, limpa o timer
                clearTimeout(offlineTimeout);
                offlineTimeout = null;
            }
            if (userId) {
                try {
                    // Atualiza o status para "online"
                    await User_1.default.update({ online: true }, { where: { id: userId } });
                    console.log(`User ${userId} marcado como on-line`);
                }
                catch (error) {
                    console.error("Erro ao marcar o usuário como online:", error);
                }
            }
        });
        // Outros eventos de conexão
        socket.on("joinChatBox", (ticketId) => {
            socket.join(ticketId);
        });
        socket.on("joinNotification", () => {
            socket.join("notification");
        });
        socket.on("joinTickets", (status) => {
            socket.join(status);
        });
        socket.on("joinTicketsLeave", (status) => {
            socket.leave(status);
        });
        socket.on("joinChatBoxLeave", (ticketId) => {
            socket.leave(ticketId);
        });
    });
    return io;
};
exports.initIO = initIO;
const getIO = () => {
    if (!io) {
        throw new AppError_1.default("Socket IO not initialized");
    }
    return io;
};
exports.getIO = getIO;
