// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract HashAnchor {
    struct Anchor {
        string hashValue;
        uint256 timestamp;
    }

    Anchor[] public anchors;

    event HashAnchored(string indexed hashValue, uint256 timestamp);

    function anchorHash(string calldata _hash) external {
        anchors.push(Anchor(_hash, block.timestamp));
        emit HashAnchored(_hash, block.timestamp);
    }

    function getAnchorCount() external view returns (uint256) {
        return anchors.length;
    }

    function getAnchor(uint256 index) external view returns (string memory, uint256) {
        Anchor storage a = anchors[index];
        return (a.hashValue, a.timestamp);
    }
}
