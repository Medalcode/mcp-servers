import argparse
import asyncio
import json
import logging
import sys

logger = logging.getLogger("pathwise-pipeline")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Pathwise Pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    search_parser = sub.add_parser("search", help="Search jobs across boards")
    search_parser.add_argument("query", help="Job search query")
    search_parser.add_argument("--location", default="Chile", help="Location filter")
    search_parser.add_argument("--remote", action="store_true", help="Remote only")

    apply_parser = sub.add_parser("apply", help="Auto-apply to job offers")
    apply_parser.add_argument("urls", nargs="+", help="Job offer URLs")
    apply_parser.add_argument("--profile", type=int, help="Profile ID to use")

    profile_parser = sub.add_parser("profile", help="Show current profile")
    profile_parser.add_argument("--id", type=int, help="Profile ID")

    stats_parser = sub.add_parser("stats", help="Show application statistics")

    init_parser = sub.add_parser("init", help="Initialize database and default profile")

    args = parser.parse_args()

    if args.command == "init":
        from database import init_db
        init_db()
        logger.info("Database initialized successfully.")
        return

    if args.command == "stats":
        from database.repos import applications as app_repo
        stats = app_repo.get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.command == "profile":
        from database.repos import profiles as profile_repo
        if args.id:
            profile = profile_repo.get_full_profile(args.id)
        else:
            profile = profile_repo.get_default_profile()
        if profile:
            print(json.dumps(profile, indent=2, ensure_ascii=False))
        else:
            print("No profile found. Run `pathwise-pipeline init` to create one.")
            sys.exit(1)
        return

    if args.command == "search":
        asyncio.run(_run_search(args.query, args.location, args.remote))
        return

    if args.command == "apply":
        asyncio.run(_run_apply(args.urls, args.profile))
        return


async def _run_search(query: str, location: str, remote_only: bool):
    from services.scraper_engine import search_all
    from database import init_db
    init_db()
    logger.info("Searching for: %s in %s", query, location)
    jobs = await search_all(query, location, remote_only)
    print(json.dumps(jobs, indent=2, ensure_ascii=False))
    logger.info("Found %d jobs", len(jobs))


async def _run_apply(urls: list[str], profile_id: int | None):
    from tools.auto_apply_tools import _batch_apply_one
    from database.repos import profiles as profile_repo
    from database import init_db
    init_db()
    if profile_id:
        profile = profile_repo.get_full_profile(profile_id)
    else:
        profile = profile_repo.get_default_profile()
    if not profile:
        logger.error("No profile found.")
        sys.exit(1)

    results = []
    for url in urls:
        logger.info("Applying to: %s", url)
        res = await _batch_apply_one(url, profile)
        results.append(res)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
