"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.importFlow = exports.exportFlow = exports.FlowUploadAll = exports.FlowDuplicate = exports.FlowUploadAudio = exports.FlowUploadImg = exports.FlowDataGetOne = exports.FlowDataUpdate = exports.flowOne = exports.myFlows = exports.deleteFlow = exports.updateFlow = exports.createFlow = void 0;
const ListFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/ListFlowBuilderService"));
const CreateFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/CreateFlowBuilderService"));
const UpdateFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/UpdateFlowBuilderService"));
const DeleteFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/DeleteFlowBuilderService"));
const GetFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/GetFlowBuilderService"));
const FlowUpdateDataService_1 = __importDefault(require("../services/FlowBuilderService/FlowUpdateDataService"));
const FlowsGetDataService_1 = __importDefault(require("../services/FlowBuilderService/FlowsGetDataService"));
const UploadImgFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/UploadImgFlowBuilderService"));
const UploadAudioFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/UploadAudioFlowBuilderService"));
const DuplicateFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/DuplicateFlowBuilderService"));
const UploadAllFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/UploadAllFlowBuilderService"));
const ExportFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/ExportFlowBuilderService"));
const ImportFlowBuilderService_1 = __importDefault(require("../services/FlowBuilderService/ImportFlowBuilderService"));
const fs_1 = __importDefault(require("fs"));
// import { handleMessage } from "../services/FacebookServices/facebookMessageListener";
const createFlow = async (req, res) => {
    const { name } = req.body;
    const userId = parseInt(req.user.id);
    const { companyId } = req.user;
    const flow = await (0, CreateFlowBuilderService_1.default)({
        userId,
        name,
        companyId
    });
    if (flow === "exist") {
        return res.status(402).json("exist");
    }
    return res.status(200).json(flow);
};
exports.createFlow = createFlow;
const updateFlow = async (req, res) => {
    const { companyId } = req.user;
    const { flowId, name } = req.body;
    const flow = await (0, UpdateFlowBuilderService_1.default)({ companyId, name, flowId });
    if (flow === 'exist') {
        return res.status(402).json('exist');
    }
    return res.status(200).json(flow);
};
exports.updateFlow = updateFlow;
const deleteFlow = async (req, res) => {
    const { idFlow } = req.params;
    const flowIdInt = parseInt(idFlow);
    const flow = await (0, DeleteFlowBuilderService_1.default)(flowIdInt);
    return res.status(200).json(flow);
};
exports.deleteFlow = deleteFlow;
const myFlows = async (req, res) => {
    const { companyId } = req.user;
    const flows = await (0, ListFlowBuilderService_1.default)({
        companyId
    });
    return res.status(200).json(flows);
};
exports.myFlows = myFlows;
const flowOne = async (req, res) => {
    const { idFlow } = req.params;
    const { companyId } = req.user;
    const idFlowInt = parseInt(idFlow);
    const webhook = await (0, GetFlowBuilderService_1.default)({
        companyId,
        idFlow: idFlowInt
    });
    return res.status(200).json(webhook);
};
exports.flowOne = flowOne;
const FlowDataUpdate = async (req, res) => {
    const userId = parseInt(req.user.id);
    const bodyData = req.body;
    const { companyId } = req.user;
    const keys = Object.keys(bodyData);
    console.log(keys);
    const webhook = await (0, FlowUpdateDataService_1.default)({
        companyId,
        bodyData
    });
    return res.status(200).json(webhook);
};
exports.FlowDataUpdate = FlowDataUpdate;
const FlowDataGetOne = async (req, res) => {
    const { idFlow } = req.params;
    const { companyId } = req.user;
    const idFlowInt = parseInt(idFlow);
    const webhook = await (0, FlowsGetDataService_1.default)({
        companyId,
        idFlow: idFlowInt
    });
    return res.status(200).json(webhook);
};
exports.FlowDataGetOne = FlowDataGetOne;
const FlowUploadImg = async (req, res) => {
    const medias = req.files;
    const { companyId } = req.user;
    const userId = parseInt(req.user.id);
    if (medias.length === 0) {
        return res.status(400).json("No File");
    }
    let nameFile = medias[0].filename;
    if (medias[0].filename.split(".").length === 1) {
        nameFile = medias[0].filename + "." + medias[0].mimetype.split("/")[1];
    }
    const img = await (0, UploadImgFlowBuilderService_1.default)({
        userId,
        name: nameFile,
        companyId
    });
    return res.status(200).json(img);
};
exports.FlowUploadImg = FlowUploadImg;
const FlowUploadAudio = async (req, res) => {
    const medias = req.files;
    const { companyId } = req.user;
    const userId = parseInt(req.user.id);
    if (medias.length === 0) {
        return res.status(400).json("No File");
    }
    let nameFile = medias[0].filename;
    if (medias[0].filename.split(".").length === 1) {
        nameFile = medias[0].filename + "." + medias[0].mimetype.split("/")[1];
    }
    const img = await (0, UploadAudioFlowBuilderService_1.default)({
        userId,
        name: nameFile,
        companyId
    });
    return res.status(200).json(img);
};
exports.FlowUploadAudio = FlowUploadAudio;
const FlowDuplicate = async (req, res) => {
    const { flowId } = req.body;
    const newFlow = await (0, DuplicateFlowBuilderService_1.default)({ id: flowId });
    return res.status(200).json(newFlow);
};
exports.FlowDuplicate = FlowDuplicate;
const FlowUploadAll = async (req, res) => {
    const medias = req.files;
    const { companyId } = req.user;
    const userId = parseInt(req.user.id);
    if (medias.length === 0) {
        return res.status(400).json("No File");
    }
    const items = await (0, UploadAllFlowBuilderService_1.default)({
        userId,
        medias: medias,
        companyId
    });
    return res.status(200).json(items);
};
exports.FlowUploadAll = FlowUploadAll;
const exportFlow = async (req, res) => {
    const { idFlow } = req.params;
    const { companyId } = req.user;
    const idFlowInt = parseInt(idFlow);
    try {
        const exportData = await (0, ExportFlowBuilderService_1.default)({
            companyId,
            idFlow: idFlowInt
        });
        // Definir um nome de arquivo para o download
        const flowName = exportData.name.replace(/\s+/g, "_").toLowerCase();
        res.setHeader("Content-Disposition", `attachment; filename=${flowName}_export.json`);
        res.setHeader("Content-Type", "application/json");
        return res.status(200).json(exportData);
    }
    catch (error) {
        console.error("Erro ao exportar fluxo:", error);
        return res.status(500).json({ error: "Erro ao exportar fluxo" });
    }
};
exports.exportFlow = exportFlow;
const importFlow = async (req, res) => {
    const userId = parseInt(req.user.id);
    const { companyId } = req.user;
    const importFile = req.file;
    if (!importFile) {
        return res.status(400).json({ error: "Nenhum arquivo enviado" });
    }
    try {
        console.log(`Processando arquivo de importação: ${importFile.originalname}`);
        // Ler o arquivo do disco usando o path
        const fileContent = fs_1.default.readFileSync(importFile.path, "utf8");
        // Remover o arquivo temporário após leitura (opcional, mas recomendado)
        fs_1.default.unlinkSync(importFile.path);
        let importData;
        try {
            importData = JSON.parse(fileContent);
            console.log(`Dados de importação JSON parseados com sucesso. Nome do fluxo: ${importData.name}`);
        }
        catch (parseError) {
            console.error("Erro ao fazer parse do arquivo JSON:", parseError);
            return res.status(400).json({ error: "Arquivo JSON inválido" });
        }
        if (!importData || !importData.name || !importData.flow) {
            console.error("Formato de dados inválido:", {
                hasName: !!importData?.name,
                hasFlow: !!importData?.flow
            });
            return res.status(400).json({ error: "Formato de dados inválido" });
        }
        const newFlow = await (0, ImportFlowBuilderService_1.default)({
            userId,
            companyId,
            importData
        });
        return res.status(200).json(newFlow);
    }
    catch (error) {
        console.error("Erro ao importar fluxo:", error);
        return res
            .status(500)
            .json({ error: "Erro ao processar arquivo de importação" });
    }
};
exports.importFlow = importFlow;
