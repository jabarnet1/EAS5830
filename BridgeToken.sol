// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";


contract BridgeToken is ERC20, ERC20Burnable, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
	address public underlying;

    constructor( address _underlying, string memory name, string memory symbol, address admin ) ERC20(name,symbol) {
		underlying = _underlying;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
    }

    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        console.log("BridgeToken: Mint called by:", msg.sender);
        console.log("BridgeToken: Minting to:", to);
        console.log("BridgeToken: Mint amount:", amount);
        _mint(to, amount);
        console.log("BridgeToken: Mint successful. New balance of recipient:", balanceOf(to));
    }

    function clawBack(address account, uint256 amount) public onlyRole(MINTER_ROLE) {
        console.log("BridgeToken: clawBack called by:", msg.sender);
        console.log("BridgeToken: clawBack account:", account);
        console.log("BridgeToken: clawBack amount:", amount);
        _burn(account, amount);
        console.log("BridgeToken: clawBack successful. New balance of account:", balanceOf(account));
    }

    // This is the function called indirectly by Destination::unwrap
    // when using `wrappedTokenInstance.burn(_amount)`.
    // ERC20Burnable's burn() function will internally call _burn(msg.sender, amount).
    // Adding console logs here will allow inspecting the final stage before the revert.
    function _burn(address account, uint256 amount) internal override {
        console.log("BridgeToken: _burn called internally.");
        console.log("BridgeToken: _burn account:", account);
        console.log("BridgeToken: _burn amount:", amount);
        uint256 accountBalance = ERC20.balanceOf(account); // Explicitly get balance here
        console.log("BridgeToken: _burn account balance:", accountBalance);
        require(accountBalance >= amount, "ERC20: burn amount exceeds balance - from _burn"); // Custom require for debugging
        super._burn(account, amount); // Call the parent's _burn function
        console.log("BridgeToken: _burn successful. New balance:", ERC20.balanceOf(account));
    }

    function burnFrom(address account, uint256 amount) public override {
        console.log("BridgeToken: burnFrom called by:", msg.sender);
        console.log("BridgeToken: burnFrom account:", account);
        console.log("BridgeToken: burnFrom amount:", amount);
		if( ! hasRole(MINTER_ROLE,msg.sender) ) {
            console.log("BridgeToken: burnFrom - msg.sender is NOT MINTER_ROLE. Checking allowance.");
			_spendAllowance(account, _msgSender(), amount);
            console.log("BridgeToken: burnFrom - Allowance spent successfully.");
		} else {
            console.log("BridgeToken: burnFrom - msg.sender IS MINTER_ROLE. No allowance check needed.");
        }
        _burn(account, amount); // This will call the overridden _burn function above
        console.log("BridgeToken: burnFrom successful. New balance of account:", balanceOf(account));
    }
}


