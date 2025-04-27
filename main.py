import argparse
import logging

from logics.solana_logics import get_program_first_deployment_timestamp

def main():
    parser = argparse.ArgumentParser(description="Pass the Solana program ID and network (mainnet/devnet)")
    parser.add_argument("-p", "--program_id", help="Input: Solana program ID", required=True)
    parser.add_argument("-m", "--mainnet", action="store_true", help="Use mainnet if specified, otherwise devnet")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (DEBUG) logging")

    args = parser.parse_args()
    # Setup logging based on --verbose
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Completely disable logging if not verbose
        logging.disable(logging.CRITICAL)
    
    program_id = args.program_id
    is_mainnet = args.mainnet

    unix_timestamp, readable_datetime = get_program_first_deployment_timestamp(program_id, is_mainnet)
    print(f"First Deployment Timestamp: {unix_timestamp}, {readable_datetime} UTC")

if __name__ == "__main__":
    main()
