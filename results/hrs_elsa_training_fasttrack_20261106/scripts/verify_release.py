import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release import verify,install
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install-to',type=Path);args=parser.parse_args()
    try:
        install(args.install_to) if args.install_to else verify()
        print('PASS ISSUE=PUBLIC_FASTTRACK_RELEASE_VERIFIED')
    except Exception:
        print('STOP ISSUE=PUBLIC_FASTTRACK_RELEASE_OR_DESTINATION_INVALID');raise SystemExit(2)
