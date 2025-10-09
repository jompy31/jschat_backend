"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setChannelWebhook = void 0;
const Whatsapp_1 = __importDefault(require("../../models/Whatsapp"));
const showHubToken_1 = require("./showHubToken");
const { Client, MessageSubscription, WebhookController } = require("notificamehubsdk");
require("dotenv").config();
const setChannelWebhook = async (whatsapp, whatsappId) => {
    const notificameHubToken = await (0, showHubToken_1.showHubToken)(whatsapp.companyId.toString());
    const client = new Client(notificameHubToken);
    const url = `${process.env.BACKEND_URL}/hub-webhook/${whatsapp.token}`;
    const subscription = new MessageSubscription({
        url
    }, {
        channel: whatsapp.token
    });
    // client
    // .updateSubscription("subscription-identifier", subscription)
    await client
        .createSubscription(subscription)
        .then((response) => {
        console.log("Webhook subscribed:", response);
    })
        .catch((error) => {
        console.log("Error:", error);
    });
    await Whatsapp_1.default.update({
        status: "CONNECTED"
    }, {
        where: {
            id: whatsappId
        }
    });
};
exports.setChannelWebhook = setChannelWebhook;
