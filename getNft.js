const ethers = require('ethers');
require('dotenv').config();
const fs = require('fs');

const privateKey = process.env.PRIVATE_KEY;
const arbitrumAlchemyApiKey = process.env.ARBITRUM_ALCHEMY_KEY;

const alchemyProvider = new ethers.providers.AlchemyProvider("arbitrum", arbitrumAlchemyApiKey);
const managerContractABI = JSON.parse(fs.readFileSync('contractABI.json', 'utf8'));
const managerContractAddress = '0xaa277cb7914b7e5514946da92cb9de332ce610ef';
const signer = new ethers.Wallet(privateKey, alchemyProvider);

const contract = new ethers.Contract(managerContractAddress, managerContractABI, signer);

function bigNumToReadable(bigNum, decimals = false) {
    if (!decimals) {
        return Number(ethers.utils.formatUnits(bigNum, 18))
    } else {
        return Number(ethers.utils.formatUnits(bigNum, decimals))
    }
}

async function findNft(address) {
    try {
        let position = await contract.tokenOfOwnerByIndex(address, 0)
        let tokenId = (bigNumToReadable(position) * 10 ** 18)
        console.log(JSON.stringify({ tokenId: tokenId }));
    } catch (error) {
        console.error(JSON.stringify({ error: error.message }));
    }
}

const address = process.argv[2];
findNft(address);