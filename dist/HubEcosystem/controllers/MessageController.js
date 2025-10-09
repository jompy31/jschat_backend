"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.send = void 0;
const Contact_1 = __importDefault(require("../../models/Contact"));
const Ticket_1 = __importDefault(require("../../models/Ticket"));
const SendTextMessageService_1 = require("../services/SendTextMessageService");
const Whatsapp_1 = __importDefault(require("../../models/Whatsapp"));
const SendMediaMessageService_1 = require("../services/SendMediaMessageService");
const send = async (req, res) => {
    const { body: message } = req.body;
    const { ticketId } = req.params;
    const medias = req.files;
    console.log("sending hub message controller");
    const ticket = await Ticket_1.default.findByPk(ticketId, {
        include: [
            {
                model: Contact_1.default,
                as: "contact",
                attributes: ["number"]
            },
            {
                model: Whatsapp_1.default,
                as: "whatsapp",
                attributes: ["token", "channel", "companyId"]
            }
        ]
    });
    try {
        if (medias) {
            await Promise.all(medias.map(async (media) => {
                await (0, SendMediaMessageService_1.SendMediaMessageService)(media, message, ticket.id, ticket.contact, ticket.whatsapp);
            }));
        }
        else {
            await (0, SendTextMessageService_1.SendTextMessageService)(message, ticket.id, ticket.contact, ticket.whatsapp);
        }
        return res.status(200).json({ message: "Message sent" });
    }
    catch (error) {
        console.log(error);
        return res.status(400).json({ message: error });
    }
};
exports.send = send;
