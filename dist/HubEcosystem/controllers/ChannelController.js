"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.index = exports.store = void 0;
const socket_1 = require("../../libs/socket");
const setChannelWebhook_1 = require("../helpers/setChannelWebhook");
const CreateChannelsService_1 = __importDefault(require("../services/CreateChannelsService"));
const ListChannels_1 = __importDefault(require("../services/ListChannels"));
const StartWhatsAppSession_1 = require("../../services/WbotServices/StartWhatsAppSession");
const store = async (req, res) => {
    const { channels = [] } = req.body;
    const { companyId } = req.user;
    const { whatsapps } = await (0, CreateChannelsService_1.default)({
        companyId,
        channels
    });
    whatsapps.forEach(whatsapp => {
        setTimeout(() => {
            (0, setChannelWebhook_1.setChannelWebhook)(whatsapp, whatsapp.id.toString());
        }, 2000);
    });
    const io = (0, socket_1.getIO)();
    whatsapps.forEach(whatsapp => {
        (0, StartWhatsAppSession_1.StartWhatsAppSession)(whatsapp, companyId);
        whatsapp.status = "CONNECTED";
        io.of(String(companyId))
            .emit(`company-${companyId}-whatsapp`, {
            action: "update",
            whatsapp
        });
    });
    return res.status(200).json(whatsapps);
};
exports.store = store;
const index = async (req, res) => {
    const { companyId } = req.user;
    try {
        const channels = await (0, ListChannels_1.default)(companyId.toString());
        return res.status(200).json(channels);
    }
    catch (error) {
        return res.status(500).json({ error: error.message });
    }
};
exports.index = index;
