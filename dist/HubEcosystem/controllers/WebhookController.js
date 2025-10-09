"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.listen = exports.index = void 0;
const Queue_1 = __importDefault(require("../../models/Queue"));
const Whatsapp_1 = __importDefault(require("../../models/Whatsapp"));
const HubMessageListener_1 = __importDefault(require("../services/HubMessageListener"));
const index = async (req, res) => {
    console.log('aaa', req.body, req.params);
    return res.send(req.query["hub.challenge"]);
};
exports.index = index;
const listen = async (req, res) => {
    const medias = req.files;
    const { channelId } = req.params;
    const connection = await Whatsapp_1.default.findOne({
        where: { token: channelId },
        include: [
            {
                model: Queue_1.default,
                as: "queues",
                attributes: ["id", "name", "color", "greetingMessage"],
            }
        ],
        order: [
            ["queues", "id", "ASC"],
        ]
    });
    try {
        await (0, HubMessageListener_1.default)(req.body, connection, medias);
        return res.status(200).json({ message: "Webhook received" });
    }
    catch (error) {
        return res.status(400).json({ message: error });
    }
};
exports.listen = listen;
