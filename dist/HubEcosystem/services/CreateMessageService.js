"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const socket_1 = require("../../libs/socket");
const Message_1 = __importDefault(require("../../models/Message"));
const CreateMessageService = async (messageData) => {
    const { contactId, body, ticketId, fromMe, companyId, fileName, mediaType, originalName, ack } = messageData;
    if ((!body || body === "") && (!fileName || fileName === "")) {
        return;
    }
    const data = {
        contactId,
        body,
        ticketId,
        fromMe,
        companyId,
        ack
    };
    if (fileName) {
        data.mediaUrl = fileName;
        data.mediaType = mediaType === "photo" ? "image" : mediaType;
        data.body = data.mediaUrl;
    }
    try {
        console.log("criando mensagem: ", data);
        const newMessage = await Message_1.default.create(data);
        console.log("mensagem criada: ", newMessage);
        await newMessage.reload({
            include: [
                {
                    association: "ticket",
                    include: [
                        {
                            association: "contact"
                        },
                        {
                            association: "user"
                        },
                        {
                            association: "queue"
                        },
                        {
                            association: "tags"
                        },
                        {
                            association: "whatsapp"
                        }
                    ]
                }
            ]
        });
        const io = (0, socket_1.getIO)();
        io.of(String(companyId)).emit(`company-${companyId}-appMessage`, {
            action: "create",
            message: newMessage,
            ticket: newMessage.ticket,
            contact: newMessage.ticket.contact
        });
        return newMessage;
    }
    catch (error) {
        console.log(error);
    }
};
exports.default = CreateMessageService;
