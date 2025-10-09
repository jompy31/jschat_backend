"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const Chat_1 = __importDefault(require("../../models/Chat"));
const ChatMessage_1 = __importDefault(require("../../models/ChatMessage"));
const ChatUser_1 = __importDefault(require("../../models/ChatUser"));
const User_1 = __importDefault(require("../../models/User"));
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
async function CreateMessageService({ senderId, chatId, message, medias }) {
    let mediaPath = "";
    let mediaName = "";
    // Processar mídia se existir
    if (medias && medias.length > 0) {
        const media = medias[0];
        const dir = path_1.default.join(__dirname, "..", "..", "..", "public", "chat-media");
        // Garantir que o diretório existe
        if (!fs_1.default.existsSync(dir)) {
            fs_1.default.mkdirSync(dir, { recursive: true });
        }
        // Criar nome de arquivo único
        mediaName = `${new Date().getTime()}-${media.originalname.replace(/\s/g, "_")}`;
        const filePath = path_1.default.join(dir, mediaName);
        // Salvar arquivo
        fs_1.default.writeFileSync(filePath, media.buffer);
        // Definir caminho da mídia para salvar no banco de dados
        mediaPath = `/chat-media/${mediaName}`;
    }
    const newMessage = await ChatMessage_1.default.create({
        senderId,
        chatId,
        message,
        mediaPath,
        mediaName
    });
    await newMessage.reload({
        include: [
            { model: User_1.default, as: "sender", attributes: ["id", "name"] },
            {
                model: Chat_1.default,
                as: "chat",
                include: [{ model: ChatUser_1.default, as: "users" }]
            }
        ]
    });
    const sender = await User_1.default.findByPk(senderId);
    await newMessage.chat.update({ lastMessage: `${sender.name}: ${message}` });
    const chatUsers = await ChatUser_1.default.findAll({
        where: { chatId }
    });
    for (let chatUser of chatUsers) {
        if (chatUser.userId === senderId) {
            await chatUser.update({ unreads: 0 });
        }
        else {
            await chatUser.update({ unreads: chatUser.unreads + 1 });
        }
    }
    return newMessage;
}
exports.default = CreateMessageService;
