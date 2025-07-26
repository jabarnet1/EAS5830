// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol"; //This allows role-based access control through _grantRole() and the modifier onlyRole
import "@openzeppelin/contracts/token/ERC20/ERC20.sol"; //This contract needs to interact with ERC20 tokens

contract AMM is AccessControl{
    bytes32 public constant LP_ROLE = keccak256("LP_ROLE");
	uint256 public invariant;
	address public tokenA;
	address public tokenB;
	uint256 feebps = 3; //The fee in basis points (i.e., the fee should be feebps/10000)

	event Swap( address indexed _inToken, address indexed _outToken, uint256 inAmt, uint256 outAmt );
	event LiquidityProvision( address indexed _from, uint256 AQty, uint256 BQty );
	event Withdrawal( address indexed _from, address indexed recipient, uint256 AQty, uint256 BQty );

	/*
		Constructor sets the addresses of the two tokens
	*/
    constructor( address _tokenA, address _tokenB ) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender );
        _grantRole(LP_ROLE, msg.sender);

		require( _tokenA != address(0), 'Token address cannot be 0' );
		require( _tokenB != address(0), 'Token address cannot be 0' );
		require( _tokenA != _tokenB, 'Tokens cannot be the same' );
		tokenA = _tokenA;
		tokenB = _tokenB;

    }


	function getTokenAddress( uint256 index ) public view returns(address) {
		require( index < 2, 'Only two tokens' );
		if( index == 0 ) {
			return tokenA;
		} else {
			return tokenB;
		}
	}

	/*
		The main trading functions
		
		User provides sellToken and sellAmount

		The contract must calculate buyAmount using the formula:
	*/
	function tradeTokens( address sellToken, uint256 sellAmount ) public {
		require( invariant > 0, 'Invariant must be nonzero' );
		require( sellToken == tokenA || sellToken == tokenB, 'Invalid token' );
		require( sellAmount > 0, 'Cannot trade 0' );
		require( invariant > 0, 'No liquidity' );
		uint256 qtyA;
		uint256 qtyB;
		uint256 swapAmt;

		//YOUR CODE HERE 

		// Determine which token is being sold and which is being bought
    bool sellingTokenA = (sellToken == tokenA);
    address buyTokenAddress = sellingTokenA ? tokenB : tokenA;
    IERC20 buyToken = IERC20(buyTokenAddress);
    IERC20 sellTokenContract = IERC20(sellToken);

		// Transfer the sellAmount from the user to the contract
		sellTokenContract.safeTransferFrom(msg.sender, address(this), sellAmount);

		// Calculate the effective amount after applying the trading fee
		// The fee is taken from the deposited side (sellAmount)
		uint256 effectiveSellAmount = (sellAmount * (10000 - feebps)) / 10000;

		uint256 currentReserveA = reserveA;
		uint256 currentReserveB = reserveB;

		uint256 buyAmount;

		// Calculate buyAmount using the constant product formula with the effective sell amount
		if (sellingTokenA) {
				uint256 newReserveA = currentReserveA + effectiveSellAmount;
				// Solve for buyAmount: (currentReserveA + effectiveSellAmount) * (currentReserveB - buyAmount) = invariant
				// buyAmount = currentReserveB - (invariant / newReserveA)
				buyAmount = currentReserveB - (invariant / newReserveA);
				require(buyAmount < currentReserveB, "Not enough liquidity for trade");
				require(invariant / newReserveA < currentReserveB, "Insufficient liquidity for trade"); // Handle potential integer division edge case
		} else { // selling Token B
				uint256 newReserveB = currentReserveB + effectiveSellAmount;
				// Solve for buyAmount: (currentReserveB + effectiveSellAmount) * (currentReserveA - buyAmount) = invariant
				// buyAmount = currentReserveA - (invariant / newReserveB)
				buyAmount = currentReserveA - (invariant / newReserveB);
				require(buyAmount < currentReserveA, "Not enough liquidity for trade");
				require(invariant / newReserveB < currentReserveA, "Insufficient liquidity for trade"); // Handle potential integer division edge case
		}

		require(buyAmount > 0, "Trade resulted in zero output");

		// Update the contract's reserves
		if (sellingTokenA) {
				reserveA = currentReserveA + sellAmount; // Full sellAmount is added to reserves (including fee portion)
				reserveB = currentReserveB - buyAmount;
		} else {
				reserveB = currentReserveB + sellAmount; // Full sellAmount is added to reserves (including fee portion)
				reserveA = currentReserveA - buyAmount;
		}

		// The invariant increases because the fee portion is added to the reserves but not used in the swap calculation
		invariant = reserveA * reserveB;

		// Transfer the calculated buyAmount of the other token to the sender
		buyToken.safeTransfer(msg.sender, buyAmount);

		emit Swap(sellToken, buyTokenAddress, sellAmount, buyAmount);



		//END

		uint256 new_invariant = ERC20(tokenA).balanceOf(address(this))*ERC20(tokenB).balanceOf(address(this));
		require( new_invariant >= invariant, 'Bad trade' );
		invariant = new_invariant;
	}

	/*
		Use the ERC20 transferFrom to "pull" amtA of tokenA and amtB of tokenB from the sender
	*/
	function provideLiquidity( uint256 amtA, uint256 amtB ) public {
		require( amtA > 0 || amtB > 0, 'Cannot provide 0 liquidity' );
		//YOUR CODE HERE

		// Transfer tokens from the liquidity provider to the contract
		// The sender (msg.sender) must have approved the AMM contract to spend these tokens previously.
		IERC20(tokenA).safeTransferFrom(msg.sender, address(this), tokenA_quantity);
		IERC20(tokenB).safeTransferFrom(msg.sender, address(this), tokenB_quantity);

		uint256 newLiquidityShares;

		if (invariant == 0) {
				// First liquidity provision - initialize the pool
				invariant = tokenA_quantity * tokenB_quantity;
				reserveA = tokenA_quantity;
				reserveB = tokenB_quantity;
				// The initial liquidity shares can be set arbitrarily, e.g., to the amount of one token
				newLiquidityShares = tokenA_quantity; 
		} else {
				// Subsequent liquidity provision - ensure the ratio is maintained
				require(
						(tokenA_quantity * reserveB) == (tokenB_quantity * reserveA),
						"Amounts must maintain current pool ratio"
				);

		// Calculate new LP shares proportionally to the added liquidity
				newLiquidityShares = (totalLiquidityShares * tokenA_quantity) / reserveA;

				// Update reserves and invariant
				reserveA += tokenA_quantity;
				reserveB += tokenB_quantity;
				invariant = reserveA * reserveB; 
		}

		// Grant the LP role to the sender
		_grantRole(LP_ROLE, msg.sender);
		// Update liquidity share balances
		liquidityShares[msg.sender] += newLiquidityShares;
		totalLiquidityShares += newLiquidityShares;

		// end
		emit LiquidityProvision( msg.sender, amtA, amtB );
	}

	/*
		Use the ERC20 transfer function to send amtA of tokenA and amtB of tokenB to the target recipient
		The modifier onlyRole(LP_ROLE) 
	*/
	function withdrawLiquidity( address recipient, uint256 amtA, uint256 amtB ) public onlyRole(LP_ROLE) {
		require( amtA > 0 || amtB > 0, 'Cannot withdraw 0' );
		require( recipient != address(0), 'Cannot withdraw to 0 address' );
		if( amtA > 0 ) {
			ERC20(tokenA).transfer(recipient,amtA);
		}
		if( amtB > 0 ) {
			ERC20(tokenB).transfer(recipient,amtB);
		}
		invariant = ERC20(tokenA).balanceOf(address(this))*ERC20(tokenB).balanceOf(address(this));
		emit Withdrawal( msg.sender, recipient, amtA, amtB );
	}


}
