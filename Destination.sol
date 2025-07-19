// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

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

		// 1. Check if the underlying token has been registered (created via createToken)
        address wrappedTokenAddress = underlying_tokens[_underlying_token];
        require(wrappedTokenAddress != address(0), "Underlying token not registered");

        // 2. Lookup the BridgeToken instance
        BridgeToken wrappedTokenInstance = BridgeToken(wrappedTokenAddress);

        // 3. Mint the corresponding amount of BridgeTokens to the recipient
        // The _mint function is part of the ERC20 standard and is available in BridgeToken
        wrappedTokenInstance.mint(_recipient, _amount);

        // 4. Emit the Wrap event
        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);

	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE

		 // 1. Verify that the _wrapped_token is indeed a BridgeToken managed by this contract.
        require(wrapped_tokens[_wrapped_token] != address(0), "Invalid wrapped token address");

        // 2. Get the address of the underlying token (on the source chain).
        address underlyingTokenAddress = wrapped_tokens[_wrapped_token];

        // 3. Cast the _wrapped_token address to a BridgeToken contract instance.
        BridgeToken wrappedTokenInstance = BridgeToken(_wrapped_token);

        // 4. Burn the wrapped tokens from the caller (msg.sender).
        wrappedTokenInstance.burn(msg.sender, _amount);

        emit Unwrap(underlyingTokenAddress, _wrapped_token, msg.sender, _recipient_on_source_chain, _amount);
    }


	function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE

		// Ensure this underlying token hasn't been bridged before
        require(underlying_tokens[_underlying_token] == address(0), "Token already bridged");

        // Deploy a new BridgeToken contract
        BridgeToken newToken = new BridgeToken(name, symbol);

        // Store the mapping between the underlying and wrapped tokens
        underlying_tokens[_underlying_token] = address(newToken);
        wrapped_tokens[address(newToken)] = _underlying_token;

        // Add the new token to the list of deployed tokens
        tokens.push(address(newToken));

        // Emit the Creation event
        emit Creation(_underlying_token, address(newToken));

        // Return the address of the newly created BridgeToken
        return address(newToken);

	}

}


