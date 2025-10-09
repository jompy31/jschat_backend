"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const sequelize_1 = require("sequelize");
// Adicionar a coluna notificameHub na tabela CompaniesSettings
module.exports = {
    up: (queryInterface) => {
        return queryInterface.addColumn("CompaniesSettings", "notificameHub", {
            type: sequelize_1.DataTypes.STRING,
            onUpdate: "CASCADE",
            onDelete: "SET NULL",
            allowNull: true
        });
    },
};
