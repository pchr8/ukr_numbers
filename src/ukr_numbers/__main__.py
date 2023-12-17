from ukr_numbers import Numbers
import argparse
import logging

logging.basicConfig()


def run(args):
    n = Numbers()
    res = n.convert_to_auto(n=args.number, desc=args.inflection)
    print(res)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "number",
        help="Number to convert",
        type=int,
    )
    parser.add_argument(
        "inflection",
        help="Plaintext sample declination (e.g. 'перший' if you want your '3' to become a 'третій')",
        type=str,
        default="один",
        nargs="?",
    )
    parser.add_argument("--pdb", "-P", help="Run PDB on exception", action="store_true")
    parser.add_argument(
        "-q",
        help="Output only warnings",
        action="store_const",
        dest="loglevel",
        const=logging.WARN,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Output more details",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger = logging.getLogger(__package__)
    logger.setLevel(args.loglevel if args.loglevel else logging.INFO)
    logger.debug(args)

    try:
        run(args)
    except Exception as e:
        if args.pdb:
            extype, value, tb = sys.exc_info()
            traceback.print_exc()
            pdb.post_mortem(tb)
        else:
            logger.exception(e)


if __name__ == "__main__":
    main()
