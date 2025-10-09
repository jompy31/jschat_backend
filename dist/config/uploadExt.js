"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const path_1 = __importDefault(require("path"));
const multer_1 = __importDefault(require("multer"));
const fs_1 = __importDefault(require("fs"));
const publicFolder = path_1.default.resolve(__dirname, "..", "..", "public");
const uploadFolder = path_1.default.join(publicFolder, "uploads");
if (!fs_1.default.existsSync(uploadFolder)) {
    fs_1.default.mkdirSync(uploadFolder, { recursive: true });
}
const formatFileName = (originalName) => {
    const extension = path_1.default.extname(originalName);
    let baseName = path_1.default.basename(originalName, extension);
    const MAX_NAME_LENGTH = 30;
    if (baseName.length > MAX_NAME_LENGTH) {
        baseName = baseName.substring(0, MAX_NAME_LENGTH);
    }
    baseName = baseName.replace(/[^a-zA-Z0-9]/g, "_");
    baseName = baseName.replace(/_+/g, "_");
    baseName = baseName.replace(/^_|_$/g, "");
    return baseName;
};
exports.default = {
    directory: uploadFolder,
    storage: multer_1.default.diskStorage({
        destination: uploadFolder,
        filename(req, file, cb) {
            const timestamp = new Date().getTime();
            const originalName = file.originalname;
            let extension = path_1.default.extname(originalName).toLowerCase();
            if (!extension) {
                if (file.mimetype === "application/pdf")
                    extension = ".pdf";
                else if (file.mimetype.includes("spreadsheetml"))
                    extension = ".xlsx";
                else if (file.mimetype.includes("wordprocessingml"))
                    extension = ".docx";
                else if (file.mimetype.includes("msword"))
                    extension = ".doc";
                else if (file.mimetype.includes("ms-excel"))
                    extension = ".xls";
                else if (file.mimetype.includes("audio/"))
                    extension = ".mp3";
                else if (file.mimetype.split("/")[1])
                    extension = `.${file.mimetype.split("/")[1]}`;
                else
                    extension = "";
            }
            const formattedName = formatFileName(originalName);
            const finalName = `${formattedName}_${timestamp}${extension}`;
            return cb(null, finalName);
        }
    })
};
