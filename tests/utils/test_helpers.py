import logging
import json
import datetime
from typing import Any, Optional, Dict, Tuple
from pathlib import Path
from utils.logger import setup_logger

def get_log_filename(base_name: str, symbol: str) -> str:
    """Generate log filename with timestamp and symbol"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    symbol_clean = symbol.replace('-', '_').lower()
    return f"{base_name}_{symbol_clean}_{timestamp}.log"

def setup_test_loggers(symbol: str) -> Tuple[logging.Logger, logging.Logger]:
    """Setup loggers with symbol-specific filenames
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Tuple of (main_logger, test_logger)
    """
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Main logger
    main_log_file = get_log_filename("main", symbol)
    logger = setup_logger("main", log_file=main_log_file)
    
    # Test results logger
    test_log_file = get_log_filename("test_results", symbol)
    test_logger = setup_logger("test_results", log_file=test_log_file, log_to_console=False)
    
    return logger, test_logger

def save_test_results(test_logger: logging.Logger, test_name: str, success: bool, 
                     response: Any, error: Optional[str] = None) -> None:
    """Save detailed test results to log file
    
    Args:
        test_logger: Logger for test results
        test_name: Name of the test
        success: Whether the test passed
        response: API response data
        error: Error message if test failed
    """
    timestamp = datetime.datetime.now().isoformat()
    result = {
        "timestamp": timestamp,
        "test": test_name,
        "success": success,
        "response": response,
        "error": error
    }
    test_logger.info(json.dumps(result, indent=2))

def test_api_endpoint(logger: logging.Logger, test_logger: logging.Logger, 
                     name: str, func, *args) -> bool:
    """Generic API endpoint test function with detailed logging
    
    Args:
        logger: Main logger
        test_logger: Test results logger
        name: Name of the endpoint being tested
        func: Function to test
        *args: Arguments to pass to the function
        
    Returns:
        bool: True if test passed, False otherwise
    """
    try:
        result = func(*args)
        if result:
            logger.info(f"✓ {name} API test successful")
            save_test_results(test_logger, name, True, result)
            return True
        logger.error(f"✗ {name} API test failed - empty response")
        save_test_results(test_logger, name, False, None, "Empty response")
        return False
    except Exception as e:
        logger.error(f"✗ {name} API test failed: {str(e)}")
        save_test_results(test_logger, name, False, None, str(e))
        return False

def generate_test_summary(results: Dict[str, Dict[str, Any]], symbol: str) -> str:
    """Generate a detailed test summary
    
    Args:
        results: Dictionary of test results
        symbol: Trading pair symbol
        
    Returns:
        str: Formatted summary text
    """
    summary = [
        "\n=== FameEX API Test Summary ===\n",
        f"Time: {datetime.datetime.now().isoformat()}",
        f"Symbol: {symbol}\n"
    ]
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r['success'])
    
    summary.append(f"Overall Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    summary.append(f"Tests Passed: {successful_tests}/{total_tests}\n")
    
    summary.append("Detailed Results:")
    for endpoint, result in results.items():
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        summary.append(f"\n{endpoint.upper()}:")
        summary.append(f"Status: {status}")
        if not result['success'] and result['error']:
            summary.append(f"Error: {result['error']}")
            
    return "\n".join(summary) 