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

        address buyToken;
        uint256 currentReserveIn;  // Use descriptive names for fetched balances
        uint256 currentReserveOut; // Use descriptive names for fetched balances

        // Determine input and output tokens and fetch their current balances
        if (sellToken == tokenA) {
            qtyA = sellAmount; // User is selling tokenA
            buyToken = tokenB;
            currentReserveIn = IERC20(tokenA).balanceOf(address(this));
            currentReserveOut = IERC20(tokenB).balanceOf(address(this));
        } else { // sellToken == tokenB
            qtyB = sellAmount; // User is selling tokenB
            buyToken = tokenA;
            currentReserveIn = IERC20(tokenB).balanceOf(address(this));
            currentReserveOut = IERC20(tokenA).balanceOf(address(this));
        }

        // Pull the sellToken from the user
        // Requires msg.sender to have pre-approved this contract for `sellAmount`
        IERC20(sellToken).transferFrom(msg.sender, address(this), sellAmount);

        // Calculate the amount of buyToken (swapAmt) to send to the user
        // Using SafeMath for overflow/underflow protection.
        // The check for positive reserves is still crucial to prevent division by zero.
        require(currentReserveIn > 0 && currentReserveOut > 0, "Insufficient liquidity for calculation");

        uint256 amountInWithFee = sellAmount.mul(uint256(10000).sub(feebps)); // Apply the fee
        uint256 numerator = amountInWithFee.mul(currentReserveOut);
        uint256 denominator = currentReserveIn.mul(10000).add(amountInWithFee);
        swapAmt = numerator.div(denominator);

        require(swapAmt >= minBuyAmount, "Slippage exceeds minimum accepted");

        // The state variables reserveA and reserveB are no longer directly updated here.
        // Instead, the token transfers themselves change the actual balances.
        // The new_invariant calculation will reflect these changes.

        IERC20(buyToken).transfer(msg.sender, swapAmt);

        emit Swap(sellToken, buyToken, sellAmount, swapAmt);

		// Fetch balances again after the swap to calculate the new invariant

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

		        // You could allow one if the pool already has liquidity to rebalance,
        // but for a simple AMM, requiring both is safer.

        // 1. Pull tokens from the sender
        IERC20(tokenA).transferFrom(msg.sender, address(this), amtA);
        IERC20(tokenB).transferFrom(msg.sender, address(this), amtB);

        uint256 liquiditySharesMinted;

        if (totalLiquidity == 0) {
            // This is the first liquidity provision
            // Set initial invariant and mint shares based on the geometric mean
            invariant = amtA.mul(amtB); // Initial k = x * y
            require(invariant > 0, "Initial liquidity creates zero invariant"); // Ensure non-zero liquidity

            // Mint LP tokens based on the geometric mean of the initial deposit
            // This sets the initial "price" of LP tokens.
            liquiditySharesMinted = Math.sqrt(amtA.mul(amtB));

            // Store the initial reserves.
            reserveA = amtA;
            reserveB = amtB;

            // Optional: Lock a small amount of initial liquidity to prevent edge case attacks
            // Uniswap V2 locks MINIMUM_LIQUIDITY (1000 shares)
            // if (liquiditySharesMinted > MINIMUM_LIQUIDITY) { // You'd define MINIMUM_LIQUIDITY
            //     liquiditySharesMinted = liquiditySharesMinted.sub(MINIMUM_LIQUIDITY);
            //     liquidityProvided[address(0)] = liquidityProvided[address(0)].add(MINIMUM_LIQUIDITY); // Send to burn address
            // } else {
            //    revert("Insufficient liquidity for initial deposit after minimum lock");
            // }

        } else {
            // Subsequent liquidity provision
            // Check if amounts are proportional to existing reserves
            // This is a crucial check to prevent price manipulation and maintain the pool ratio.
            require(
                (amtA.mul(reserveB) == amtB.mul(reserveA)),
                'Amounts must be proportional to existing reserves'
            );

            // Calculate LP shares to mint proportionally
            // The formula is: (amount of token you provide) * (total supply of LP tokens) / (total amount in the pool of the token you provided)
            // We calculate this for both tokens and take the minimum to ensure the ratio is maintained
            uint256 sharesRatioA = amtA.mul(totalLiquidity).div(reserveA);
            uint256 sharesRatioB = amtB.mul(totalLiquidity).div(reserveB);
            liquiditySharesMinted = sharesRatioA < sharesRatioB ? sharesRatioA : sharesRatioB;
            // The above line is equivalent to Math.min(sharesRatioA, sharesRatioB) if you had a Math.min function.

            require(liquiditySharesMinted > 0, "No liquidity shares minted");

            // Update reserves
            reserveA = reserveA.add(amtA);
            reserveB = reserveB.add(amtB);

            // Re-calculate and update the invariant (implicitly includes fees, making it increase)
            uint256 new_invariant = reserveA.mul(reserveB);
            require(new_invariant >= invariant, 'Invariant decreased after adding liquidity'); // Sanity check
            invariant = new_invariant;
        }

        // Mint LP tokens to the sender
        liquidityProvided[msg.sender] = liquidityProvided[msg.sender].add(liquiditySharesMinted);
        totalLiquidity = totalLiquidity.add(liquiditySharesMinted);



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
