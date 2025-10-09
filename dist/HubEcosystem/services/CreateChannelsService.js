"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const Company_1 = __importDefault(require("../../models/Company"));
const AppError_1 = __importDefault(require("../../errors/AppError"));
const Whatsapp_1 = __importDefault(require("../../models/Whatsapp"));
const Plan_1 = __importDefault(require("../../models/Plan"));
const CreateChannelsService = async ({ companyId, channels = [] }) => {
    const company = await Company_1.default.findOne({
        where: {
            id: companyId
        },
        include: [{ model: Plan_1.default, as: "plan" }]
    });
    if (company !== null) {
        let whatsappCount = await Whatsapp_1.default.count({
            where: {
                companyId
            }
        });
        whatsappCount += channels.length;
        if (whatsappCount >= company.plan.connections) {
            throw new AppError_1.default(`Número máximo de conexões já alcançado: ${whatsappCount}`);
        }
    }
    channels = channels.map(channel => {
        return {
            ...channel,
            status: "CONNECTED",
            companyId,
            notificameHub: true,
        };
    });
    const whatsapps = await Whatsapp_1.default.bulkCreate(channels, {
        include: ["queues"]
    });
    return { whatsapps };
};
exports.default = CreateChannelsService;
