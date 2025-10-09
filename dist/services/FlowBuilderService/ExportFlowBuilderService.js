"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const FlowBuilder_1 = require("../../models/FlowBuilder");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const mime_types_1 = __importDefault(require("mime-types"));
const ExportFlowBuilderService = async ({ companyId, idFlow }) => {
    try {
        const flow = await FlowBuilder_1.FlowBuilderModel.findOne({
            where: {
                id: idFlow,
                company_id: companyId
            }
        });
        if (!flow) {
            throw new Error("Fluxo não encontrado");
        }
        const exportData = {
            name: flow.name,
            flow: flow.flow,
            files: []
        };
        if (!flow.flow) {
            return exportData;
        }
        const fileUrls = extractFileUrls(flow.flow);
        for (const url of fileUrls) {
            try {
                const fileName = url.replace(/^uploads\//, "");
                const filePath = path_1.default.join(__dirname, "../../../public/uploads", fileName);
                if (fs_1.default.existsSync(filePath)) {
                    try {
                        const fileContent = fs_1.default.readFileSync(filePath, {
                            encoding: "base64"
                        });
                        const mimeType = getMimeType(fileName);
                        exportData.files.push({
                            originalName: fileName,
                            url: url,
                            fileContent: fileContent,
                            mimeType: mimeType
                        });
                    }
                    catch (readError) {
                        console.error(`Erro ao ler o arquivo ${fileName}:`, readError);
                    }
                }
                else {
                    console.warn(`Arquivo não encontrado: ${filePath}`);
                }
            }
            catch (fileError) {
                console.error(`Erro ao processar arquivo ${url}:`, fileError);
            }
        }
        return exportData;
    }
    catch (error) {
        console.error("Erro ao exportar fluxo:", error);
        throw error;
    }
};
function extractFileUrls(flow) {
    const urls = [];
    console.log("Iniciando extração de URLs...");
    if (flow && flow.nodes) {
        flow.nodes.forEach(node => {
            if ((node.type === "file" ||
                node.type === "img" ||
                node.type === "audio" ||
                node.type === "video") &&
                node.data.url) {
                console.log(`[${node.type}] URL encontrada: ${node.data.url}`);
                urls.push(node.data.url);
            }
            else if (node.type === "singleBlock" &&
                node.data &&
                node.data.elements &&
                Array.isArray(node.data.elements)) {
                console.log(`[singleBlock] Processando ${node.data.elements.length} elementos...`);
                node.data.elements.forEach(element => {
                    if ((element.type === "file" ||
                        element.type === "img" ||
                        element.type === "audio" ||
                        element.type === "video") &&
                        element.value) {
                        const potentialUrl = `uploads/${element.value}`;
                        console.log(`[singleBlock] Elemento tipo ${element.type}, URL construída: ${potentialUrl}`);
                        urls.push(potentialUrl);
                    }
                });
            }
        });
    }
    console.log("URLs extraídas final:", urls);
    return urls;
}
function getMimeType(fileName) {
    const mimeType = mime_types_1.default.lookup(fileName);
    return mimeType || "application/octet-stream";
}
exports.default = ExportFlowBuilderService;
