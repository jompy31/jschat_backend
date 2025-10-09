"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const Contact_1 = __importDefault(require("../../models/Contact"));
const FindOrCreateContactService = async (contact) => {
    const { name, picture, from, connection, firstName, lastName } = contact;
    const contactExists = await Contact_1.default.findOne({
        where: {
            number: from,
            companyId: connection.companyId
        }
    });
    if (contactExists) {
        return contactExists;
    }
    const newContact = await Contact_1.default.create({
        name: name || firstName || lastName,
        profilePicUrl: picture,
        channel: connection.channel,
        number: from,
        companyId: connection.companyId
    });
    return newContact;
};
exports.default = FindOrCreateContactService;
