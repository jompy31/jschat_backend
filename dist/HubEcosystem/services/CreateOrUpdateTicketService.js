"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const socket_1 = require("../../libs/socket");
const Ticket_1 = __importDefault(require("../../models/Ticket"));
const CreateOrUpdateTicketService = async (ticketData) => {
    console.log("creating ticket");
    const { contactId, channel, contents, connection } = ticketData;
    const io = (0, socket_1.getIO)();
    const ticketExists = await Ticket_1.default.findOne({
        where: {
            contactId,
            channel,
            whatsappId: connection.id,
            companyId: connection.companyId
        }
    });
    if (ticketExists) {
        console.log("ticket exists");
        let newStatus = ticketExists.status;
        let newQueueId = ticketExists.queueId;
        if (ticketExists.status === "closed") {
            newStatus = "pending";
            newQueueId = connection.sendIdQueue;
        }
        await ticketExists.update({
            lastMessage: contents[0].text,
            status: newStatus,
            queueId: newQueueId
        });
        console.log("ticket queue updated", newQueueId);
        await ticketExists.reload({
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
        });
        io.to(ticketExists.status)
            .to("notification")
            .to(ticketExists.toString())
            .emit(`company-${connection.companyId}-ticket`, {
            action: "update",
            ticket: ticketExists
        });
        return ticketExists;
    }
    const newTicket = await Ticket_1.default.create({
        status: "pending",
        channel,
        lastMessage: contents[0].text,
        contactId,
        whatsappId: connection.id,
        companyId: connection.companyId
        // queueId: connection.sendIdQueue
    });
    await newTicket.reload({
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
    });
    io.to(newTicket.status).emit(`company-${connection.companyId}-ticket`, {
        action: "create",
        ticket: newTicket
    });
    return newTicket;
};
exports.default = CreateOrUpdateTicketService;
