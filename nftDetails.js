const ethers = require('ethers');
require('dotenv').config();
const fs = require('fs');

const privateKey = process.env.PRIVATE_KEY;
const arbitrumAlchemyApiKey = process.env.ARBITRUM_ALCHEMY_KEY;

const alchemyProvider = new ethers.providers.AlchemyProvider("arbitrum", arbitrumAlchemyApiKey);
const managerContractABI = JSON.parse(fs.readFileSync('managerContractABI.json', 'utf8'));
const poolContractABI = JSON.parse(fs.readFileSync('poolContractABI.json', 'utf8'))
const managerContractAddress = '0xaa277cb7914b7e5514946da92cb9de332ce610ef';
const poolContractAddress = '0x05ba720fc96ea8969f86d7a0b0767bb8dc265232';
const signer = new ethers.Wallet(privateKey, alchemyProvider);

const managerContract = new ethers.Contract(managerContractAddress, managerContractABI, signer);
const poolContract = new ethers.Contract(poolContractAddress, poolContractABI, signer);

async function nftDetails(id) {
    try {
        let price = await poolContract.slot0()
        let priceTick = price.tick
        let positions = await managerContract.positions(id)
        console.log(JSON.stringify({ priceTick: priceTick, tickLower: positions.tickLower, tickUpper: positions.tickUpper, liquidity: positions.liquidity }));
    } catch (error) {
        console.error(JSON.stringify({ error: error.message }));
    }
}

let id = process.argv[2]
nftDetails(id)