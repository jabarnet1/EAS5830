// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

// Change these:
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

    function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE

		require(_underlying_token != address(0), "Invalid underlying token address");
        require(underlying_tokens[_underlying_token] == address(0), "Wrapped token already exists for this underlying token");

        // a new BridgeToken contract.
        BridgeToken newWrappedToken = new BridgeToken(_underlying_token, name, symbol, address(this));

        // mapping
        wrapped_tokens[_underlying_token] = address(newWrappedToken);
        underlying_tokens[address(newWrappedToken)] = _underlying_token;
        tokens.push(address(newWrappedToken));

        // MINTER_ROLE
        BridgeToken(address(newWrappedToken)).grantRole(newWrappedToken.MINTER_ROLE(), address(this));

        // emit
        emit Creation(_underlying_token, address(newWrappedToken));

        return address(newWrappedToken);
	}

	function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE

        // mapping
        address wrappedTokenAddress = wrapped_tokens[_underlying_token];

        // registration check
        require(wrappedTokenAddress != address(0), "Wrapped token not registered for this underlying token");

        // mint
        BridgeToken(wrappedTokenAddress).mint(_recipient, _amount);

        // emit
        emit Wrap(_underlying_token, wrappedTokenAddress, _recipient, _amount);
	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount, address _accountToBurnFrom ) public {
        // YOUR CODE HERE

        // mapping
        address underlyingTokenAddress = underlying_tokens[_wrapped_token];

        // registration check
        require(underlyingTokenAddress != address(0), "Not a registered wrapped token");

        // Add checks before burning (Recommended)
        // Ensure _accountToBurnFrom has enough balance
        require(BridgeToken(_wrapped_token).balanceOf(_accountToBurnFrom) >= _amount, "Unwrap: Insufficient wrapped token balance for account");
        // Ensure _accountToBurnFrom has given allowance to this contract (msg.sender of unwrap call)
        // This assumes the relayer (msg.sender) will be initiating the burnFrom on behalf of _accountToBurnFrom.
        require(BridgeToken(_wrapped_token).allowance(_accountToBurnFrom, msg.sender) >= _amount, "Unwrap: Insufficient allowance from account");


        // burn
        BridgeToken(_wrapped_token).burnFrom(_accountToBurnFrom, _amount);

        // emit
        emit Unwrap(underlyingTokenAddress, _wrapped_token, _accountToBurnFrom, _recipient, _amount); // Updated 'frm' to _accountToBurnFrom
    }
}


