"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const showHubToken_1 = require("../helpers/showHubToken");
const { Client } = require("notificamehubsdk");
require("dotenv").config();
const ListChannels = async (companyId) => {
    try {
        const notificameHubToken = await (0, showHubToken_1.showHubToken)(companyId);
        if (!notificameHubToken) {
            throw new Error("NOTIFICAMEHUB_TOKEN_NOT_FOUND");
        }
        const client = new Client(notificameHubToken);
        const response = await client.listChannels();
        return response;
    }
    catch (error) {
        throw new Error(error.body.message);
    }
};
exports.default = ListChannels;
