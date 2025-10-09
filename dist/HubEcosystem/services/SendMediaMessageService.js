"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SendMediaMessageService = void 0;
require("dotenv").config();
const { Client, FileContent } = require("notificamehubsdk");
const file_type_1 = __importDefault(require("file-type"));
const promises_1 = require("fs/promises");
const path_1 = require("path");
const convertFiles_1 = require("../../utils/convertFiles");
const showHubToken_1 = require("../helpers/showHubToken");
const CreateMessageService_1 = __importDefault(require("./CreateMessageService"));
const verifyExtensionFile = async (media) => {
    const resultFile = await file_type_1.default.fromFile(media.path);
    const havePoint = media.filename.includes(".");
    const actualExtension = media.filename.split(".").pop();
    const extension = resultFile?.ext || havePoint ? actualExtension : "withoutExtension";
    let newFilename = media.filename;
    if (actualExtension && actualExtension !== extension && havePoint) {
        newFilename = media.filename.replace(actualExtension, extension);
        const newPath = (0, path_1.join)(media.destination, newFilename);
        await (0, promises_1.rename)(media.path, newPath);
    }
    else if (!havePoint) {
        newFilename = `${media.filename}.${extension}`;
        const newPath = (0, path_1.join)(media.destination, newFilename);
        await (0, promises_1.rename)(media.path, newPath);
    }
    media.filename = newFilename;
    media.originalname = newFilename;
};
const verifyFileIsMp4 = async (media) => {
    const extension = (await file_type_1.default.fromFile(media.path))?.ext;
    if (!extension || extension !== "mp4") {
        media.path = await (0, convertFiles_1.convertToMp4)(media);
        media.filename = `${media.filename.split(".").slice(0, -1).join(".")}.mp4`;
        media.originalname = media.filename;
    }
};
const SendMediaMessageService = async (media, message, ticketId, contact, connection, passVerification) => {
    if (!passVerification)
        await verifyExtensionFile(media);
    const notificameHubToken = await (0, showHubToken_1.showHubToken)(connection.companyId.toString());
    const client = new Client(notificameHubToken);
    const channelClient = client.setChannel(connection.channel === 'whatsapp_business_account' ? 'whatsapp' : connection.channel);
    message = message.replace(/\n/g, " ");
    const backendUrl = process.env.BACKEND_URL;
    if (media.mimetype.includes("image")) {
        if (connection.channel === "telegram") {
            media.mimetype = "photo";
        }
        else {
            media.mimetype = "image";
        }
    }
    else if (media.mimetype.includes("audio")) {
        if (connection.channel.includes("facebook")) {
            await verifyFileIsMp4(media);
        }
        media.mimetype = "audio";
    }
    else if (media.mimetype.includes("video")) {
        if (connection.channel.includes("whatsapp") || connection.channel.includes("facebook")) {
            await verifyFileIsMp4(media);
        }
        media.mimetype = "video";
    }
    else if (connection.channel === "telegram") {
        media.mimetype = "document";
    }
    else {
        if (connection.channel.includes("whatsapp")) {
            media.mimetype = "document";
        }
    }
    const mediaUrl = `${backendUrl}/public/company${connection?.companyId}/${media.filename}`;
    try {
        const content = new FileContent(mediaUrl, media.mimetype, media.originalname, media.originalname);
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
            fileName: `${media.filename}`,
            mediaType: media.mimetype.split("/")[0],
            originalName: media.originalname,
            ack: 2
        });
        return newMessage;
    }
    catch (error) {
        console.log("Error:", error);
    }
};
exports.SendMediaMessageService = SendMediaMessageService;
