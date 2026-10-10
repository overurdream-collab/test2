import argparse, json, os
from pathlib import Path
from mcias.seed.config import SeedConfig
from mcias.seed.loader import load

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--output", default=".e2e-output/live-fixture.json")
    parser.add_argument("--reset-confirm")
    args = parser.parse_args()
    config = SeedConfig(os.environ["MCIAS_E2E_DATABASE_URL"], os.environ.get("MCIAS_ENVIRONMENT", ""), count=args.count)
    config.validate()
    if args.reset_confirm:
        from mcias.seed.reset import reset
        reset(config, args.reset_confirm)
    os.environ["MCIAS_TEST_DATABASE_URL"] = config.database_url
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config("alembic.ini"), "head")
    manifest = load(config)
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2); output.write("\n")
    path.chmod(0o600)
    print("Synthetic fixture ready; all claims held; private receipt written.")

if __name__ == "__main__": main()
