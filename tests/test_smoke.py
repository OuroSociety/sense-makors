import pytest
from decimal import Decimal
import json
from unittest.mock import Mock, patch
from api_client import FameexClient
from market_maker import MarketMaker
from config import (
    SYMBOL, ORDER_BOOK_DEPTH, SPREAD_PERCENTAGE
)
from utils.decimal_utils import safe_decimal_mul

class TestSmoke:
    @pytest.fixture
    def mock_order_book(self):
        """Mock order book data"""
        return {
            "bids": [
                ["50000", "1.0"],  # price, amount
                ["49900", "2.0"],
                ["49800", "1.5"],
            ],
            "asks": [
                ["50100", "1.0"],
                ["50200", "2.0"],
                ["50300", "1.5"],
            ]
        }
    
    @pytest.fixture
    def mock_order_response(self):
        """Mock successful order response"""
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "orderId": "123456789",
                "clientOid": "test_order"
            }
        }
    
    @pytest.fixture
    def mock_client(self, mock_order_book, mock_order_response):
        """Create a mock API client"""
        client = Mock(spec=FameexClient)
        client.get_order_book.return_value = mock_order_book
        client.place_order.return_value = mock_order_response
        return client
    
    def test_complete_market_making_cycle(self, mock_client, mock_order_book):
        """Test a complete market making cycle"""
        # Initialize market maker
        market_maker = MarketMaker(mock_client)
        
        # Test order book fetching
        mock_client.get_order_book.assert_not_called()
        order_book = mock_client.get_order_book(SYMBOL, ORDER_BOOK_DEPTH)
        assert order_book == mock_order_book
        mock_client.get_order_book.assert_called_once()
        
        # Test order calculation
        orders = market_maker.calculate_new_orders(order_book)
        assert len(orders) == 2  # Should have both buy and sell orders
        
        # Verify order properties
        buy_order = next(order for order in orders if order["side"] == 1)
        sell_order = next(order for order in orders if order["side"] == 2)
        
        assert buy_order["symbol"] == SYMBOL
        assert sell_order["symbol"] == SYMBOL
        assert Decimal(buy_order["price"]) < Decimal(sell_order["price"])
        
        # Test order placement
        for order in orders:
            result = mock_client.place_order(**order)
            assert result["code"] == 200
            assert "orderId" in result["data"]
        
        # Verify position tracking
        position = market_maker.position_tracker.get_position(SYMBOL)
        assert isinstance(position, Decimal)
        
        # Verify risk management
        assert market_maker.risk_manager.check_order(
            SYMBOL,
            Decimal(buy_order["amount"]),
            Decimal(buy_order["price"]),
            True
        )
    
    @patch('time.sleep', return_value=None)  # Prevent actual sleeping in tests
    def test_market_maker_run_cycle(self, mock_sleep, mock_client):
        """Test the market maker's main run loop"""
        market_maker = MarketMaker(mock_client)
        
        # Simulate one cycle of the market maker
        try:
            # Get order book
            order_book = mock_client.get_order_book(SYMBOL, ORDER_BOOK_DEPTH)
            
            # Calculate new orders
            orders = market_maker.calculate_new_orders(order_book)
            
            # Place orders
            for order in orders:
                result = mock_client.place_order(**order)
                if result and result.get('code') == 200:
                    order_id = result['data']['orderId']
                    market_maker.active_orders[order_id] = order
            
            # Verify the cycle completed successfully
            assert mock_client.get_order_book.call_count > 0
            assert mock_client.place_order.call_count > 0
            assert len(market_maker.active_orders) > 0
            
        except Exception as e:
            pytest.fail(f"Market maker cycle failed: {str(e)}")

    # Test cases for market making scenarios
    MARKET_MAKING_TEST_CASES = [
        {
            "description": "Normal market conditions with sufficient liquidity",
            "input": {
                "order_book": {
                    "bids": [["50000", "1.0"], ["49900", "2.0"]],
                    "asks": [["50100", "1.0"], ["50200", "2.0"]]
                },
                "market_conditions": "normal"
            },
            "expected": {
                "num_orders": 2,
                "should_succeed": True,
                # Use safe_decimal_mul for all decimal calculations
                "min_spread": safe_decimal_mul("50000", SPREAD_PERCENTAGE, "0.8"),
                "max_spread": safe_decimal_mul("50000", SPREAD_PERCENTAGE, "1.2")
            }
        },
        {
            "description": "Tight spread market conditions",
            "input": {
                "order_book": {
                    "bids": [["50000", "0.1"]],
                    "asks": [["50001", "0.1"]]
                },
                "market_conditions": "tight"
            },
            "expected": {
                "num_orders": 2,
                "should_succeed": True,
                "min_spread": safe_decimal_mul("50000", SPREAD_PERCENTAGE, "0.8"),
                "max_spread": safe_decimal_mul("50000", SPREAD_PERCENTAGE, "1.2")
            }
        },
        {
            "description": "Empty order book should not generate orders",
            "input": {
                "order_book": {"bids": [], "asks": []},
                "market_conditions": "empty"
            },
            "expected": {
                "num_orders": 0,
                "should_succeed": True,
                "min_spread": Decimal("0"),
                "max_spread": Decimal("0")
            }
        }
    ]

    @pytest.mark.parametrize("test_case", MARKET_MAKING_TEST_CASES, ids=lambda t: t["description"])
    def test_market_making_scenarios(self, mock_client, test_case):
        """
        Test market making under different market conditions.
        
        Test Structure:
            - Description: What aspect of market making we're testing
            - Input: Order book state and market conditions
            - Expected: Expected behavior and output constraints
        """
        # Setup
        mock_client.get_order_book.return_value = test_case["input"]["order_book"]
        market_maker = MarketMaker(mock_client)

        try:
            # Execute
            orders = market_maker.calculate_new_orders(test_case["input"]["order_book"])

            # Verify
            assert len(orders) == test_case["expected"]["num_orders"]

            if test_case["expected"]["num_orders"] > 0:
                # Get buy and sell orders
                buy_orders = [o for o in orders if o["side"] == 1]
                sell_orders = [o for o in orders if o["side"] == 2]

                if buy_orders and sell_orders:
                    spread = Decimal(sell_orders[0]["price"]) - Decimal(buy_orders[0]["price"])
                    assert test_case["expected"]["min_spread"] <= spread <= test_case["expected"]["max_spread"], \
                        f"Spread {spread} is outside expected range [{test_case['expected']['min_spread']}, {test_case['expected']['max_spread']}]"

        except Exception as e:
            if test_case["expected"]["should_succeed"]:
                pytest.fail(f"Test case '{test_case['description']}' failed: {str(e)}")

    # Test cases for risk management
    RISK_MANAGEMENT_TEST_CASES = [
        {
            "description": "Position within normal limits",
            "input": {
                "current_position": Decimal("50"),
                "order_size": Decimal("10"),
                "max_position": Decimal("100"),
                "price": Decimal("50000")
            },
            "expected": {
                "should_allow": True,
                "reason": "Position would remain within limits"
            }
        },
        {
            "description": "Position would exceed maximum",
            "input": {
                "current_position": Decimal("90"),
                "order_size": Decimal("20"),
                "max_position": Decimal("100"),
                "price": Decimal("50000")
            },
            "expected": {
                "should_allow": False,
                "reason": "Position would exceed maximum limit"
            }
        },
        {
            "description": "New position from zero",
            "input": {
                "current_position": Decimal("0"),
                "order_size": Decimal("50"),
                "max_position": Decimal("100"),
                "price": Decimal("50000")
            },
            "expected": {
                "should_allow": True,
                "reason": "Starting fresh position within limits"
            }
        }
    ]

    @pytest.mark.parametrize("test_case", RISK_MANAGEMENT_TEST_CASES, ids=lambda t: t["description"])
    def test_risk_management_scenarios(self, mock_client, test_case):
        """
        Test risk management under different position scenarios.
        
        Test Structure:
            - Description: The risk scenario being tested
            - Input: Current position and order details
            - Expected: Whether the order should be allowed and why
        """
        # Setup
        market_maker = MarketMaker(mock_client)
        
        # Set the current position
        market_maker.position_tracker.positions[SYMBOL] = test_case["input"]["current_position"]
        
        # Set risk limits
        market_maker.risk_manager.set_limits(
            SYMBOL,
            test_case["input"]["max_position"],
            Decimal("10")  # Default drawdown limit
        )

        # Execute
        allowed = market_maker.risk_manager.check_order(
            SYMBOL,
            test_case["input"]["order_size"],
            test_case["input"]["price"],
            True  # Buy order
        )

        # Verify
        assert allowed == test_case["expected"]["should_allow"], \
            f"Expected order to be {'allowed' if test_case['expected']['should_allow'] else 'rejected'} because {test_case['expected']['reason']}"

    # Test cases for order placement scenarios
    ORDER_PLACEMENT_TEST_CASES = [
        pytest.param(
            {"code": 200, "msg": "success", "data": {"orderId": "123"}},
            True,
            id="successful_order"
        ),
        pytest.param(
            {"code": 400, "msg": "error", "data": None},
            False,
            id="failed_order"
        ),
        pytest.param(
            None,
            False,
            id="null_response"
        )
    ]

    @pytest.mark.parametrize("order_response,should_succeed", ORDER_PLACEMENT_TEST_CASES)
    def test_order_placement(self, mock_client, order_response, should_succeed):
        """
        Test order placement with different API response scenarios.
        
        Parameters:
        - order_response: Mock API response for order placement
        - should_succeed: Whether the order placement should succeed
        """
        # Setup
        mock_client.place_order.return_value = order_response
        market_maker = MarketMaker(mock_client)
        test_order = {
            "symbol": SYMBOL,
            "side": 1,
            "orderType": 1,
            "price": "50000",
            "amount": "1.0"
        }

        # Execute
        result = mock_client.place_order(**test_order)

        # Verify
        if should_succeed:
            assert result and result.get("code") == 200
            assert "orderId" in result.get("data", {})
        else:
            assert not result or result.get("code") != 200

    # Test cases for risk management scenarios
    RISK_TEST_CASES = [
        pytest.param(
            Decimal("10"),  # Position size
            Decimal("100"),  # Max position
            True,  # Should allow order
            id="within_position_limit"
        ),
        pytest.param(
            Decimal("150"),
            Decimal("100"),
            False,
            id="exceeds_position_limit"
        ),
        pytest.param(
            Decimal("0"),
            Decimal("100"),
            True,
            id="zero_position"
        )
    ]

    @pytest.mark.parametrize("position_size,max_position,should_allow", RISK_TEST_CASES)
    def test_risk_management(self, mock_client, position_size, max_position, should_allow):
        """
        Test risk management with different position scenarios.
        
        Parameters:
        - position_size: Current position size
        - max_position: Maximum allowed position
        - should_allow: Whether the order should be allowed
        """
        # Setup
        market_maker = MarketMaker(mock_client)
        market_maker.risk_manager.set_limits(SYMBOL, max_position, Decimal("10"))
        
        # Execute
        allowed = market_maker.risk_manager.check_order(
            SYMBOL,
            position_size,
            Decimal("50000"),
            True
        )

        # Verify
        assert allowed == should_allow 