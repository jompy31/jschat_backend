"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const sequelize_1 = require("sequelize");
// Adicionar a coluna notificameHub na tabela Whatsapps
module.exports = {
    up: (queryInterface) => {
        return queryInterface.addColumn("Whatsapps", "notificameHub", {
            type: sequelize_1.DataTypes.BOOLEAN,
            onUpdate: "CASCADE",
            onDelete: "SET NULL",
            allowNull: false,
            defaultValue: false
        });
    },
};
