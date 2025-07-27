// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract Source is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
	mapping( address => bool) public approved;
	address[] public tokens;

	event Deposit( address indexed token, address indexed recipient, uint256 amount );
	event Withdrawal( address indexed token, address indexed recipient, uint256 amount );
	event Registration( address indexed token );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);

    }

	function deposit(address _token, address _recipient, uint256 _amount ) public {
		//YOUR CODE

		require(approved[_token], "Token is not registered for bridging");
		require(_amount > 0, "Deposit amount must be greater than zero");
        require(_recipient != address(0), "Invalid destination recipient address");
        require(IERC20(_token).transferFrom(msg.sender, address(this), _amount), "Token transfer failed");

        emit Deposit(_token, _recipient, _amount);
	}

	function withdraw(address _token, address _recipient, uint256 _amount ) onlyRole(WARDEN_ROLE) public {
		//YOUR CODE HERE

		require(approved[_token], "Token is not registered for bridging");
		require(_amount > 0, "Withdrawal amount must be greater than zero");
        require(_recipient != address(0), "Invalid recipient address");
        require(IERC20(_token).balanceOf(address(this)) >= _amount, "Insufficient token balance in contract");
        require(IERC20(_token).transfer(_recipient, _amount), "Token transfer failed during withdrawal");

        emit Withdrawal(_token, _recipient, _amount);
	}

	function registerToken(address _token) onlyRole(ADMIN_ROLE) public {
		//YOUR CODE HERE

		require(_token != address(0), "Invalid token address");
        require(!approved[_token], "Token already registered");

        approved[_token] = true;
        tokens.push(_token);
        emit Registration(_token);
	}


}


