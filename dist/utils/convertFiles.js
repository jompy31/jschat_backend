"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.convertToMp4 = exports.convertToMp3 = void 0;
const fluent_ffmpeg_1 = __importDefault(require("fluent-ffmpeg"));
const promises_1 = require("fs/promises");
const deleteFile = async (path) => {
    await (0, promises_1.rm)(path);
};
const convertToMp3 = async (media) => {
    return new Promise((resolve, reject) => {
        const outputFilePath = `${media.path
            .split(".")
            .slice(0, -1)
            .join(".")}.mp3`;
        (0, fluent_ffmpeg_1.default)(media.path)
            .audioCodec("libmp3lame")
            .format("mp3")
            .on("end", async () => {
            await deleteFile(media.path);
            resolve(outputFilePath);
        })
            .on("error", err => {
            reject(err);
        })
            .save(outputFilePath);
    });
};
exports.convertToMp3 = convertToMp3;
const convertToMp4 = async (media) => {
    return new Promise((resolve, reject) => {
        const outputFilePath = `${media.path
            .split(".")
            .slice(0, -1)
            .join(".")}.mp4`;
        (0, fluent_ffmpeg_1.default)(media.path)
            .videoCodec("libx264")
            .format("mp4")
            .on("end", async () => {
            await deleteFile(media.path);
            resolve(outputFilePath);
        })
            .on("error", err => {
            reject(err);
        })
            .save(outputFilePath);
    });
};
exports.convertToMp4 = convertToMp4;
