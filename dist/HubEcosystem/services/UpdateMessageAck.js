"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.UpdateMessageAck = void 0;
const Message_1 = __importDefault(require("../../models/Message"));
const UpdateMessageAck = async (messageId) => {
    const message = await Message_1.default.findOne({
        where: {
            id: messageId
        }
    });
    if (!message) {
        return;
    }
    await message.update({
        ack: 3
    });
};
exports.UpdateMessageAck = UpdateMessageAck;
