from __future__ import annotations
import logging
from pathlib import Path
import sys

# Add src/ to path
SRC_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SRC_ROOT))

from element_tester.system.drivers.relay_mcc.driver import ERB08Driver
from element_tester.system.drivers.hypot3865.driver import AR3865Driver
import element_tester.system.procedures.hipot_test_procedures as hipot_procs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hipot_test")


class HipotTestSequence:
    """
    Wrapper class for hipot test sequence.
    Provides object-oriented interface to hipot test procedures.
    """
    
    def __init__(
        self,
        relay_driver: ERB08Driver,
        hipot_driver: AR3865Driver,
        logger: logging.Logger | None = None
    ):
        """
        Initialize hipot test sequence.
        
        Args:
            relay_driver: ERB08 relay board driver
            hipot_driver: AR3865 hipot tester driver
            logger: Optional logger instance
        """
        self.relay_driver = relay_driver
        self.hipot_driver = hipot_driver
        self.log = logger or logging.getLogger("hipot_test_sequence")
    
    def run_test(
        self,
        keep_relay_closed: bool = False,
        reset_after_test: bool = True,
        total_test_duration_s: float = 5.0,
        reset_delay_after_result_s: float = 2.0,
        file_index: int = 1
    ) -> tuple[bool, str]:
        """
        Execute complete hipot test sequence.
        
        Args:
            keep_relay_closed: If True, leaves relay 8 closed after test
            reset_after_test: If True, resets instrument after getting result
            total_test_duration_s: Expected total duration of hipot test
            reset_delay_after_result_s: Additional delay after result before reset
        
        Returns:
            (passed, result_string): Test outcome and raw result
        """
        return hipot_procs.run_hipot_test(
            erb_driver=self.relay_driver,
            hipot_driver=self.hipot_driver,
            file_index=file_index,
            keep_relay_closed=keep_relay_closed,
            reset_after_test=reset_after_test,
            total_test_duration_s=total_test_duration_s,
            reset_delay_after_result_s=reset_delay_after_result_s,
            logger=self.log
        )
    
    def close_relay(self) -> None:
        """Close relay 8 for hipot circuit."""
        hipot_procs.close_hipot_relay(self.relay_driver, logger=self.log)
    
    def open_relay(self) -> None:
        """Open all relays (disable hipot circuit)."""
        hipot_procs.open_all_relays(self.relay_driver, logger=self.log)

def main():
    """
    Standalone test execution.
    Run with: python test.py [--simulate]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Hipot Test Sequence")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode (no hardware required)"
    )
    parser.add_argument(
        "--voltage",
        type=float,
        default=1500.0,
        help="Test voltage in volts (default: 1500V)"
    )
    parser.add_argument(
        "--current-trip",
        type=float,
        default=5.0,
        help="Current trip threshold in mA (default: 5.0mA)"
    )
    args = parser.parse_args()
    
    # Initialize drivers
    logger.info("Initializing drivers...")
    
    relay_drv = ERB08Driver(
        board_num=0,
        port_low=12,
        port_high=13,
        simulate=args.simulate
    )

    hipot_drv = AR3865Driver(
        resource='serial://COM6',
        baudrate=38400,  # AR3865 uses 38400 baud
        simulate=args.simulate
    )
    
    try:
        # Initialize hardware
        logger.info("Initializing hipot instrument...")
        hipot_drv.initialize()
        idn = hipot_drv.idn()
        logger.info(f"Connected to: {idn}")
        
        if not args.simulate and "3865" not in idn:
            logger.warning(f"Unexpected instrument ID: {idn}")
        
        # Run test
        logger.info("=" * 60)
        logger.info("Starting hipot test sequence")
        logger.info("=" * 60)
        
        # Choose FL 2 for 440/480V units per operator selection
        file_index = 2 if int(args.voltage) in (440, 480) else 1
        passed, result = hipot_procs.run_hipot_test(relay_drv, hipot_drv, file_index=file_index, logger=logger)
        
        logger.info("=" * 60)
        if passed:
            logger.info("✓ HIPOT TEST PASSED")
            logger.info("Ready to proceed to measurement test")
        else:
            logger.info("✗ HIPOT TEST FAILED")
            logger.info(f"Failure reason: {result}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Test sequence failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Shutting down drivers...")
        try:
            relay_drv.shutdown()
            logger.info("Relay driver shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down relay driver: {e}")
        
        try:
            hipot_drv.shutdown()
            logger.info("Hipot driver shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down hipot driver: {e}")

if __name__ == "__main__":
    main()

