import argparse
import collections
from pathlib import Path
from nearai import EntryLocation
from metadata import index_by_location


CliEntryInformation = collections.namedtuple("CliEntryInformation", ["namespace", "name", "version"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("entry_string", help="The entry to index in the format <namespace>/<name>/<version>")
    parser.add_argument("-o", "--output-dir", default="./cards", help="Directory to save the output cards")

    args = parser.parse_args()

    try:
        namespace, name, version = args.entry_string.split("/")
    except ValueError:
        print("Error: entry_string must be in the format <namespace>/<name>/<version>")
        exit(1)

    cli_entry_info = CliEntryInformation(namespace, name, version)

    print(f"Namespace: {cli_entry_info.namespace}")
    print(f"Name: {cli_entry_info.name}")
    print(f"Version: {cli_entry_info.version}")
    print(f"Output directory: {args.output_dir}")

    if args.output_dir:
        directory_path = Path(args.output_dir)
        directory_path.mkdir(parents=True, exist_ok=True)

    index_by_location(EntryLocation(
        namespace=namespace,
        name=name,
        version=version
    ), output_directory=args.output_dir)

if __name__ == "__main__":
    main()