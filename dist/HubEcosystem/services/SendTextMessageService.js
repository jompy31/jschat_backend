"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SendTextMessageService = void 0;
require("dotenv").config();
const { Client, TextContent } = require("notificamehubsdk");
const showHubToken_1 = require("../helpers/showHubToken");
const CreateMessageService_1 = __importDefault(require("./CreateMessageService"));
const SendTextMessageService = async (message, ticketId, contact, connection) => {
    const notificameHubToken = await (0, showHubToken_1.showHubToken)(connection.companyId.toString());
    const client = new Client(notificameHubToken);
    const channelClient = client.setChannel(connection.channel === 'whatsapp_business_account' ? 'whatsapp' : connection.channel);
    const content = new TextContent(message);
    try {
        console.log({
            token: connection.token,
            number: contact.number,
            content,
            message
        });
        let response = await channelClient.sendMessage(connection.token, contact.number, content);
        let data;
        try {
            const jsonStart = response.indexOf("{");
            const jsonResponse = response.substring(jsonStart);
            data = JSON.parse(jsonResponse);
        }
        catch (error) {
            data = response;
        }
        const newMessage = await (0, CreateMessageService_1.default)({
            contactId: contact.id,
            body: message,
            ticketId,
            fromMe: true,
            companyId: connection.companyId,
            ack: 2
        });
        return newMessage;
    }
    catch (error) {
        console.log("Error:", error);
    }
};
exports.SendTextMessageService = SendTextMessageService;
