"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const downloadFIles_1 = require("../helpers/downloadFIles");
const CreateMessageService_1 = __importDefault(require("./CreateMessageService"));
const CreateOrUpdateTicketService_1 = __importDefault(require("./CreateOrUpdateTicketService"));
const FindOrCreateContactService_1 = __importDefault(require("./FindOrCreateContactService"));
const UpdateMessageAck_1 = require("./UpdateMessageAck");
const verifySentMessageStatus = (message) => {
    const { messageStatus: { code } } = message;
    const isMessageSent = code === "SENT";
    if (isMessageSent) {
        return true;
    }
    return false;
};
const HubMessageListener = async (message, connection, medias) => {
    const ignoreEvent = (message?.message.visitor?.name === "" || !message?.message.visitor?.name)
        && (message?.message.visitor?.firstName === "" || !message?.message.visitor?.firstName);
    if (ignoreEvent || message.direction === "OUT") {
        return;
    }
    const isMessageFromMe = message.type === "MESSAGE_STATUS";
    if (isMessageFromMe) {
        const isMessageSent = verifySentMessageStatus(message);
        if (isMessageSent) {
            console.log("HubMessageListener: message sent");
            (0, UpdateMessageAck_1.UpdateMessageAck)(message.messageId);
        }
        else {
            console.log("HubMessageListener: message not sent", message.messageStatus.code, message.messageStatus.description);
        }
        return;
    }
    const { message: { id, from, channel, contents, visitor } } = message;
    try {
        const contact = await (0, FindOrCreateContactService_1.default)({
            ...visitor,
            from,
            connection
        });
        const ticket = await (0, CreateOrUpdateTicketService_1.default)({
            contactId: contact.id,
            channel,
            contents,
            connection
        });
        if (contents[0]?.type === "text") {
            await (0, CreateMessageService_1.default)({
                contactId: contact.id,
                body: contents[0].text,
                ticketId: ticket.id,
                fromMe: false,
                companyId: connection.companyId
            });
        }
        else {
            const media = await (0, downloadFIles_1.downloadFiles)({
                content: contents[0],
                connection: connection,
            });
            await (0, CreateMessageService_1.default)({
                contactId: contact.id,
                body: contents[0].text,
                ticketId: ticket.id,
                fromMe: false,
                companyId: connection.companyId,
                fileName: `${media.filename}`,
                mediaType: media.mimeType.split("/")[0],
                originalName: media.originalname
            });
        }
    }
    catch (error) {
        console.log(error);
    }
};
exports.default = HubMessageListener;
