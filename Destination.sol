// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

import {console} from "forge-std/console.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
	mapping( address => address) public underlying_tokens;
	mapping( address => address) public wrapped_tokens;
	address[] public tokens;

	event Creation( address indexed underlying_token, address indexed wrapped_token );
	event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
	event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

	function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE
        require(_amount > 0, "Amount must be positive"); // Add this check
        require(_recipient != address(0), "Invalid recipient"); // Add this check


		console.log("--- wrap START ---");
        console.log("Called by (msg.sender):", msg.sender);
        console.log("Underlying token param (_underlying_token):", _underlying_token);
        console.log("Recipient param (_recipient):", _recipient);
        console.log("Amount param (_amount):", _amount);

        // 1. Check if the underlying token has been registered (created via createToken)
        address wrappedTokenAddress = underlying_tokens[_underlying_token];

        console.log("Lookup result for underlying_tokens[_underlying_token]:", wrappedTokenAddress); // Debug 1.1: Check mapping lookup result
        require(wrappedTokenAddress != address(0), "Underlying token not registered");
        console.log("Require check passed: Underlying token is registered.");

        // 2. Lookup the BridgeToken instance
        BridgeToken wrappedTokenInstance = BridgeToken(wrappedTokenAddress);
        console.log("Wrapped token instance address:", address(wrappedTokenInstance)); // Debug 1.2: Confirm instance address

        // 3. Mint the corresponding amount of BridgeTokens to the recipient
        console.log("Recipient's balance BEFORE mint:", wrappedTokenInstance.balanceOf(_recipient)); // Debug 1.3: Check recipient balance before mint
        wrappedTokenInstance.mint(_recipient, _amount);
        console.log("Mint call executed.");
        console.log("Recipient's balance AFTER mint:", wrappedTokenInstance.balanceOf(_recipient)); // Debug 1.4: Check recipient balance after mint

        // 4. Emit the Wrap event
        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);
        console.log("Wrap event emitted.");
        console.log("--- wrap END ---");

	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE

        require(_amount > 0, "Amount must be positive"); // Add this check
        require(_recipient != address(0), "Invalid recipient"); // Add this check

        console.log("--- unwrap START ---");
        console.log("Called by (msg.sender):", msg.sender);
        console.log("Wrapped token param (_wrapped_token):", _wrapped_token);
        console.log("Recipient param (_recipient):", _recipient);
        console.log("Amount param (_amount):", _amount);

        require(wrapped_tokens[_wrapped_token] != address(0), "Invalid wrapped token address");
        console.log("Require check passed: Wrapped token is registered.");

        address underlyingTokenAddress = wrapped_tokens[_wrapped_token];
        console.log("Resolved underlying token address:", underlyingTokenAddress);

        BridgeToken wrappedTokenInstance = BridgeToken(_wrapped_token);
        console.log("Wrapped token instance address:", address(wrappedTokenInstance));

        uint256 senderBalance = wrappedTokenInstance.balanceOf(msg.sender);
        console.log("User's balance before burn:", senderBalance); // Renamed for clarity
        console.log("Amount to burn:", _amount);

        // The user (msg.sender) must first have approved
        // the Destination contract to spend their wrapped tokens using
        // BridgeToken.approve(address(destination), _amount)

        // --- THIS IS THE CRUCIAL CHANGE ---
        console.log("Calling BridgeToken.burnFrom(msg.sender, _amount)...");
        wrappedTokenInstance.burnFrom(msg.sender, _amount); // Burn tokens from the user (msg.sender)
        console.log("BridgeToken.burnFrom executed successfully.");
        // --- END OF CHANGE ---

        console.log("User's balance AFTER burn:", wrappedTokenInstance.balanceOf(msg.sender));

        emit Unwrap(underlyingTokenAddress, _wrapped_token, msg.sender, _recipient, _amount);
        console.log("Unwrap event emitted.");
        console.log("--- unwrap END ---");

    }


	function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE

		console.log("--- createToken START ---"); // Debug Step 1: Start marker
        console.log("Called by (msg.sender):", msg.sender);
        console.log("Underlying token param (_underlying_token):", _underlying_token);
        console.log("Token name:", name);
        console.log("Token symbol:", symbol);

        // Ensure this underlying token hasn't been bridged before
        require(underlying_tokens[_underlying_token] == address(0), "Token already bridged");
        console.log("Require check passed: Token not already bridged.");

        // Deploy a new BridgeToken contract
        BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this)); 
        console.log("New BridgeToken deployed at address:", address(newToken));
        console.log("Admin for new BridgeToken (address(this)):", address(this));

        // Store the mapping between the underlying and wrapped tokens
        underlying_tokens[_underlying_token] = address(newToken);
        wrapped_tokens[address(newToken)] = _underlying_token;
        tokens.push(address(newToken)); // Note: Check if 'tokens' array grows too large in real usage, not a debug issue here.

        console.log("Mapped underlying_tokens[_underlying_token]:", underlying_tokens[_underlying_token]); // Debug Step 2: Check mapping after assignment
        console.log("Mapped wrapped_tokens[address(newToken)]:", wrapped_tokens[address(newToken)]);   // Debug Step 3: Check mapping after assignment

        emit Creation(_underlying_token, address(newToken));
        console.log("Creation event emitted.");
        console.log("--- createToken END ---"); // Debug Step 4: End marker

        return address(newToken);
	}

}


