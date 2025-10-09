"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const sequelize_1 = require("sequelize");
module.exports = {
    up: async (queryInterface) => {
        await queryInterface.sequelize.query(`
      CREATE SEQUENCE IF NOT EXISTS "Messages_id_seq" START WITH 1;
    `);
        await queryInterface.changeColumn("Messages", "id", {
            type: sequelize_1.DataTypes.INTEGER,
            allowNull: false,
            primaryKey: true,
            defaultValue: sequelize_1.Sequelize.literal("nextval('\"Messages_id_seq\"'::regclass)")
        });
    },
    down: async (queryInterface) => {
        await queryInterface.sequelize.query(`
      DROP SEQUENCE IF EXISTS "Messages_id_seq";
    `);
        await queryInterface.changeColumn("Messages", "id", {
            type: sequelize_1.DataTypes.INTEGER,
            allowNull: false,
            primaryKey: true
        });
    }
};
