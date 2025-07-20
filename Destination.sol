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

    function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE

		require(_underlying_token != address(0), "Invalid underlying token address");
        require(underlying_tokens[_underlying_token] == address(0), "Wrapped token already exists for this underlying token");

        // Deploy a new BridgeToken contract.
        // The admin for the BridgeToken's AccessControl will be this Destination contract.
        BridgeToken newWrappedToken = new BridgeToken(_underlying_token, name, symbol, address(this));

        // Store the mapping
        underlying_tokens[_underlying_token] = address(newWrappedToken);
        wrapped_tokens[address(newWrappedToken)] = _underlying_token;
        tokens.push(address(newWrappedToken)); // Add to the list of deployed tokens

        // Grant this Destination contract the MINTER_ROLE on the newly deployed BridgeToken
        BridgeToken(address(newWrappedToken)).grantRole(newWrappedToken.MINTER_ROLE(), address(this));

        //emit Creation(_underlying_token, address(newWrappedToken));
        emit Creation(_underlying_token, address(0));

        return address(newWrappedToken);

	}

	function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE

        address wrappedTokenAddress = underlying_tokens[_underlying_token];
        require(wrappedTokenAddress != address(0), "Wrapped token not registered for this underlying token");

        // Use the mint function available in BridgeToken.sol
        BridgeToken(wrappedTokenAddress).mint(_recipient, _amount);

        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);

	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE

        address underlyingTokenAddress = wrapped_tokens[_wrapped_token];
        require(underlyingTokenAddress != address(0), "Not a registered wrapped token");

        // Use the burn function available in BridgeToken.sol (ERC20Burnable extension)
        // This burn function will internally call _burn(msg.sender, amount)
        BridgeToken(_wrapped_token).burn(_amount);

        emit Unwrap(underlyingTokenAddress, _wrapped_token, msg.sender, _recipient, _amount);

        // After burning, a separate mechanism (off-chain relayer) would
        // observe this event and trigger the release of original tokens on the source chain.


    }
}


