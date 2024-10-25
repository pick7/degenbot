# ruff:noqa:C408
from eth_utils.address import to_checksum_address

CURVE_V1_REGISTRY_ADDRESS = to_checksum_address("0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5")
CURVE_V1_FACTORY_ADDRESS = to_checksum_address("0x127db66E7F0b16470Bec194d0f496F9Fa065d0A9")
CURVE_V1_METAREGISTRY_ADDRESS = to_checksum_address("0xF98B45FA17DE75FB1aD0e7aFD971b0ca00e379fC")

BROKEN_CURVE_V1_POOLS = tuple(
    to_checksum_address(pool_address)
    for pool_address in (
        "0x1F71f05CF491595652378Fe94B7820344A551B8E",
        "0x28B0Cf1baFB707F2c6826d10caf6DD901a6540C5",
        "0x84997FAFC913f1613F51Bb0E2b5854222900514B",
        "0xA77d09743F77052950C4eb4e6547E9665299BecD",
        "0xD652c40fBb3f06d6B58Cb9aa9CFF063eE63d465D",
        # "0x2009f19A8B46642E92Ea19adCdFB23ab05fC20A6",
        # "0x2206cF41E7Db9393a3BcbB6Ad35d344811523b46",
        # "0x46f5ab27914A670CFE260A2DEDb87f84c264835f",
        # "0x883F7d4B6B24F8BF1dB980951Ad08930D9AEC6Bc",
        # "0x99AE07e7Ab61DCCE4383A86d14F61C68CdCCbf27",
    )
)