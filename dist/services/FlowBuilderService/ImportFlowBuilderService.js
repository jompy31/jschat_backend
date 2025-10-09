"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const FlowBuilder_1 = require("../../models/FlowBuilder");
const FlowImg_1 = require("../../models/FlowImg");
const FlowAudio_1 = require("../../models/FlowAudio");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const uuid_1 = require("uuid");
const ImportFlowBuilderService = async ({ userId, companyId, importData }) => {
    try {
        if (!importData || !importData.name || !importData.flow) {
            throw new Error("Dados de importação inválidos");
        }
        const urlMap = new Map();
        if (importData.files && Array.isArray(importData.files)) {
            const uploadsDir = path_1.default.join(__dirname, "../../../public/uploads");
            if (!fs_1.default.existsSync(uploadsDir)) {
                fs_1.default.mkdirSync(uploadsDir, { recursive: true });
            }
            for (const fileInfo of importData.files) {
                try {
                    const fileExt = path_1.default.extname(fileInfo.originalName);
                    const newFileName = `${(0, uuid_1.v4)()}${fileExt}`;
                    const filePath = path_1.default.join(__dirname, "../../../public/uploads", newFileName);
                    const fileBuffer = Buffer.from(fileInfo.fileContent, "base64");
                    fs_1.default.writeFileSync(filePath, fileBuffer);
                    urlMap.set(fileInfo.url, `uploads/${newFileName}`);
                    if (fileInfo.mimeType.startsWith("image/")) {
                        await FlowImg_1.FlowImgModel.create({
                            userId: userId,
                            companyId: companyId,
                            name: newFileName
                        });
                    }
                    else if (fileInfo.mimeType.startsWith("audio/")) {
                        await FlowAudio_1.FlowAudioModel.create({
                            userId: userId,
                            companyId: companyId,
                            name: newFileName
                        });
                    }
                    else {
                        await FlowImg_1.FlowImgModel.create({
                            userId: userId,
                            companyId: companyId,
                            name: newFileName
                        });
                    }
                }
                catch (fileError) {
                    console.error(`Erro ao processar arquivo importado:`, fileError);
                }
            }
        }
        const updatedFlow = updateFileUrls(importData.flow, urlMap);
        let flowName = importData.name;
        const existingFlow = await FlowBuilder_1.FlowBuilderModel.findOne({
            where: {
                name: flowName,
                company_id: companyId
            }
        });
        if (existingFlow) {
            flowName = `${flowName} (importado)`;
        }
        const newFlow = await FlowBuilder_1.FlowBuilderModel.create({
            name: flowName,
            user_id: userId,
            company_id: companyId,
            flow: updatedFlow,
            active: true
        });
        return newFlow;
    }
    catch (error) {
        console.error("Erro ao importar fluxo:", error);
        throw error;
    }
};
function updateFileUrls(flow, urlMap) {
    if (!flow || !flow.nodes) {
        console.warn("Flow inválido ou sem nós:", flow);
        return flow;
    }
    console.log(`Atualizando URLs para ${flow.nodes.length} nós`);
    const updatedNodes = flow.nodes.map(node => {
        const updatedNode = { ...node };
        if (node.type === "file" && node.data.url && urlMap.has(node.data.url)) {
            console.log(`Atualizando URL para nó de arquivo: ${node.data.url} -> ${urlMap.get(node.data.url)}`);
            updatedNode.data = {
                ...node.data,
                url: urlMap.get(node.data.url)
            };
        }
        else if (node.type === "img" &&
            node.data.url &&
            urlMap.has(node.data.url)) {
            updatedNode.data = {
                ...node.data,
                url: urlMap.get(node.data.url)
            };
        }
        else if (node.type === "audio" &&
            node.data.url &&
            urlMap.has(node.data.url)) {
            updatedNode.data = {
                ...node.data,
                url: urlMap.get(node.data.url)
            };
        }
        else if (node.type === "video" &&
            node.data.url &&
            urlMap.has(node.data.url)) {
            updatedNode.data = {
                ...node.data,
                url: urlMap.get(node.data.url)
            };
        }
        else if (node.type === "singleBlock") {
            if (node.data.files && Array.isArray(node.data.files)) {
                updatedNode.data.files = node.data.files.map(file => {
                    if (file.url && urlMap.has(file.url)) {
                        return { ...file, url: urlMap.get(file.url) };
                    }
                    return file;
                });
            }
            if (node.data.images && Array.isArray(node.data.images)) {
                updatedNode.data.images = node.data.images.map(img => {
                    if (img.url && urlMap.has(img.url)) {
                        return { ...img, url: urlMap.get(img.url) };
                    }
                    return img;
                });
            }
            if (node.data.audios && Array.isArray(node.data.audios)) {
                updatedNode.data.audios = node.data.audios.map(audio => {
                    if (audio.url && urlMap.has(audio.url)) {
                        return { ...audio, url: urlMap.get(audio.url) };
                    }
                    return audio;
                });
            }
        }
        return updatedNode;
    });
    return {
        ...flow,
        nodes: updatedNodes
    };
}
exports.default = ImportFlowBuilderService;
