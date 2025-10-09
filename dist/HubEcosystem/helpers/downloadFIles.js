"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.downloadFiles = void 0;
const axios_1 = __importDefault(require("axios"));
const path_1 = require("path");
const promises_1 = require("fs/promises");
const file_type_1 = __importDefault(require("file-type"));
const convertFiles_1 = require("../../utils/convertFiles");
const showHubToken_1 = require("./showHubToken");
const { Client, FileContent } = require("notificamehubsdk");
const downloadFiles = async ({ content, connection }) => {
    const { fileUrl, fileMimeType, fileName, type: fileType } = content;
    const { channel, companyId } = connection;
    try {
        if (channel.includes('whatsapp')) {
            const notificameHubToken = await (0, showHubToken_1.showHubToken)(connection.companyId.toString());
            const client = new Client(notificameHubToken);
            const channelClient = await client.setChannel('whatsapp');
            const content = new FileContent(fileUrl, fileMimeType);
            const data = await channelClient.downloadMedia(connection.token, 'whatsapp', content);
            const previousfilename = `${new Date().getTime()}.${fileType}`;
            const path = (0, path_1.join)(__dirname, "..", "..", "..", "public", `company${companyId}`, previousfilename);
            await (0, promises_1.writeFile)(path, data, "binary");
            let fileTypeResult = await file_type_1.default.fromFile(path);
            let mimeType = fileTypeResult.mime;
            const type = fileTypeResult.ext;
            let filename = `${new Date().getTime()}.${type}`;
            await (0, promises_1.rename)(path, (0, path_1.join)(__dirname, "..", "..", "..", "public", `company${companyId}`, filename));
            let filePath = `${__dirname}/../../../public/company${companyId}/${filename}`;
            if (mimeType.includes('audio')) {
                filePath = await (0, convertFiles_1.convertToMp3)({
                    path: filePath
                });
                fileTypeResult = await file_type_1.default.fromFile(filePath);
                mimeType = fileTypeResult.mime;
                filename = `${filename
                    .split(".")
                    .slice(0, -1)
                    .join(".")}.mp3`;
            }
            const extension = (0, path_1.extname)(filePath);
            const originalname = fileName || fileUrl.split("/").pop();
            const media = {
                mimeType,
                extension,
                filename,
                data,
                originalname
            };
            return media;
        }
        const { data } = await axios_1.default.get(fileUrl, {
            responseType: "arraybuffer"
        });
        let type = fileUrl.split("?")[0].split(".").pop();
        type = type.replace(/\//g, '');
        let filename = `${new Date().getTime()}.${type}`;
        let filePath = `${__dirname}/../../../public/company${companyId}/${filename}`;
        await (0, promises_1.writeFile)((0, path_1.join)(__dirname, "..", "..", "..", "public", `company${companyId}`, filename), data, "base64");
        let fileTypeResult = await file_type_1.default.fromBuffer(data);
        let mimeType = fileTypeResult.mime;
        if (mimeType.includes('audio')) {
            filePath = await (0, convertFiles_1.convertToMp3)({
                path: filePath
            });
            fileTypeResult = await file_type_1.default.fromFile(filePath);
            mimeType = fileTypeResult.mime;
            filename = `${filename
                .split(".")
                .slice(0, -1)
                .join(".")}.mp3`;
        }
        const extension = (0, path_1.extname)(filePath);
        const originalname = fileUrl.split("/").pop();
        const media = {
            mimeType,
            extension,
            filename,
            data,
            originalname
        };
        return media;
    }
    catch (error) {
        console.error("Erro ao processar a requisição:", error);
        throw error; // Lança o erro para quem chama a função
    }
};
exports.downloadFiles = downloadFiles;
