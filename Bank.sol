// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

contract VulnerableBank {

    mapping(address => uint256) public balances;
    address public owner;

    constructor() public {
        owner = msg.sender;
    }

    // Уязвимость: integer overflow / отсутствие SafeMath
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // Уязвимость: reentrancy + неправильный порядок CEI
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Not enough balance");

        // внешнее взаимодействие до обновления состояния
        msg.sender.call{value: amount}("");

        // состояние обновляется ПОСЛЕ внешнего вызова
        balances[msg.sender] -= amount;
    }

    // Уязвимость: отсутствие контроля доступа
    function setOwner(address newOwner) public {
        owner = newOwner;
    }

    // Уязвимость: отсутствие проверки возвращаемого значения
    function donate(address to) public payable {
        to.delegatecall("");   // крайне опасная конструкция
    }
}
