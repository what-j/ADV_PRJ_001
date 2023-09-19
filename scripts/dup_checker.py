import os
import sys
import random
import argparse
import hashlib
import zlib
from Cryptodome.Hash import SHA1, SHA256, SHA512
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from Cryptodome.Util.Padding import pad, unpad


def parse_range(range_str):
    parts = range_str.split(',')
    skip_lines = []
    for part in parts:
        if not part:
            continue
        if '-' in part:
            start, end = map(int, part.split('-'))
            skip_lines.extend(range(start, end + 1))
        else:
            skip_lines.append(int(part))
    return sorted(set(skip_lines))

def create_random_files(directory):
    for i in range(5):
        depth = random.randint(1, 2)
        rand_value = random.randint(0, 1)

        dir_path = directory
        for _ in range(depth):
            dir_path = os.path.join(dir_path, "demo")
            os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, f"demo_{i+1:02d}.txt")

        with open(file_path, "w") as file:
            file.write(str(rand_value))

def generate_aes_key():
    return get_random_bytes(32)

def hash_skipped_lines(hasher, file_path, skip_lines):
    with open(file_path, "rb") as file:
        for line_num, line in enumerate(file, start=1):
            if line_num not in skip_lines:
                hasher.update(line)
    return hasher.hexdigest()

def get_file_hashes(file_path, algorithms, skip_lines, aes_key, block_size=65536):
    hashes = {}
    if algorithms is None:
        algorithms = ["md5"]


    for algorithm in algorithms:
        if algorithm not in {'md5', 'crc32', 'sha1', 'sha256', 'sha512', 'aes'}:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        if algorithm == 'md5':
            hasher = hashlib.md5()
            with open(file_path, 'rb') as file:
                for line_num, line in enumerate(file, start=1):
                    if skip_lines is None or line_num not in skip_lines:
                        hasher.update(line)
            hashes[algorithm] = hasher.hexdigest()

        elif algorithm == 'crc32':
            hasher = zlib.crc32(b'')
            with open(file_path, 'rb') as file:
                for line in file:
                    hasher = zlib.crc32(line, hasher)
            hashes[algorithm] = str(hasher & 0xffffffff)

        elif algorithm in {'sha1', 'sha256', 'sha512'}:
            hasher = hashlib.new(algorithm)
            with open(file_path, 'rb') as file:
                for line in file:
                    hasher.update(line)
            hashes[algorithm] = hasher.hexdigest()

        elif algorithm == 'aes':
            if not aes_key:
                raise ValueError("AES encryption requires a key.")
            cipher = AES.new(aes_key, AES.MODE_ECB)
            with open(file_path, 'rb') as file:
                for line in file:
                    line = pad(line, AES.block_size)
                    line = cipher.encrypt(line)
                    hasher = hashlib.md5()  # MD5ハッシュを計算
                    hasher.update(line)
            hashes[algorithm] = hasher.hexdigest()

    return hashes

def find_duplicate_files(directory, algorithms, skip_lines, aes_key):
    file_hashes = {}
    duplicate_files = {}
    unique_files = []

    if algorithms is None:
        algorithms = ["md5"]

    for root, _, files in os.walk(directory):
        for file in sorted(files):
            file_path = os.path.join(root, file)
            file_hash_dict = get_file_hashes(file_path, algorithms, skip_lines, aes_key)

            for algo in algorithms:
                file_hash = file_hash_dict[algo]

                if file_hash in file_hashes:
                    if file_hash not in duplicate_files:
                        duplicate_files[file_hash] = [file_hashes[file_hash]]
                    duplicate_files[file_hash].append(file_path)
                else:
                    file_hashes[file_hash] = file_path
                    unique_files.append(file_path)

    return duplicate_files, unique_files

def print_duplicate_files(duplicate_files, algorithms, skip_lines, aes_key):
    if not duplicate_files:
        print("No files found.")
    else:
        if duplicate_files:
            print("## Duplicate file groups:\n")
            group_num = 1
            for group in duplicate_files.values():
                print(f"group_{group_num}:")
                for i, file_path in enumerate(group, start=1):
                    print(f"  - {i}. {file_path}:")
                    if algorithms:
                        file_hashes = get_file_hashes(file_path, algorithms, skip_lines, aes_key)
                        for algo in algorithms:
                            print(f"      - {algo}: {file_hashes[algo]}")
                print()
                group_num += 1

def print_unique_files(unique_files, algorithms, skip_lines, aes_key):
    if not unique_files:
        print("No files found.")
    else:
        if unique_files:
            print("## Unique files:\n")
            for i, file_path in enumerate(unique_files, start=1):
                file_hashes = get_file_hashes(file_path, algorithms, skip_lines, aes_key)
                print(f"  - {i}. {file_path}:")
                if algorithms:
                    for algo in algorithms:
                        print(f"      - {algo}: {file_hashes[algo]}")

def print_all_files(duplicate_files, unique_files, algorithms, skip_lines, aes_key):
    if not duplicate_files and not unique_files:
        print("No files found.")
    else:
        if duplicate_files:
            print("## Duplicate file groups:\n")
            group_num = 1
            for group in duplicate_files.values():
                print(f"group_{group_num}:")
                for i, file_path in enumerate(group, start=1):
                    print(f"  - {i}. {file_path}:")
                    if algorithms:
                        file_hashes = get_file_hashes(file_path, algorithms, skip_lines, aes_key)
                        for algo in algorithms:
                            print(f"      - {algo}: {file_hashes[algo]}")

                print()
                group_num += 1
        if unique_files:
            print("## Unique files:\n")
            for i, file_path in enumerate(unique_files, start=1):
                print(f"  - {i}. {file_path}:")
                if algorithms:
                    file_hashes = get_file_hashes(file_path, algorithms, skip_lines, aes_key)
                    for algo in algorithms:
                        print(f"      - {algo}: {file_hashes[algo]}")

def check_dups(file_list, remove_choices, algorithms, skip_lines, aes_key, force_remove):

    print("The following files are duplicates:")
    for i, file_path in enumerate(file_list, start=1):
        print(f"  - {i}. {file_path}:")
        if algorithms:
            file_hashes = get_file_hashes(file_path, algorithms, skip_lines, aes_key)
            for algo in algorithms:
                print(f"      - {algo}: {file_hashes[algo]}")

    valid_choices = []

    if force_remove:
        valid_choices = list(range(2, len(file_list) + 1))
    else:
        try:
            while True:
                choices = input(f"Enter the num to remove (1-{len(file_list)}), Ctrl+D to interrupt: ").strip()
                if not choices:
                    break

                first_choice = True

                for choice in choices.split(','):
                    choice = choice.strip()
                    if '-' in choice:
                        try:
                            start, end = map(int, choice.split('-'))
                            valid_choices.extend(range(start, end + 1))
                        except ValueError:
                            print("Please enter valid numbers or ranges.")
                            break
                    else:
                        try:
                            num = int(choice)
                            if 1 <= num <= len(file_list):
                                if first_choice:
                                    valid_choices.append(num)
                            else:
                                print(f"Please enter a valid number between 1 and {len(file_list)}.")
                                break
                        except ValueError:
                            print("Please enter valid numbers or ranges.")
                            break

                    first_choice = False

        except EOFError:
            sys.exit("\n\nCtrl+D detected. Exiting.")

    if valid_choices:
        remove_choices.extend(valid_choices)

def main():
    parser = argparse.ArgumentParser(description="Find and display duplicate files and unique files in a directory based on content.")
    parser.add_argument("input_dir", help="Directory to scan for files.")
    parser.add_argument("-d", "--dup", action="store_true", help="Display duplicated files.")
    parser.add_argument("-u", "--uniq", action="store_true", help="Display unique files.")
    parser.add_argument("-r", "--remove", action="store_true", help="Remove dupliated files.")
    parser.add_argument("-f", "--force-remove", action="store_true", help="Force removal without first one.")
    parser.add_argument("--algo", nargs='+', default=None, choices=['md5', 'sha1', 'sha256', 'crc32', 'sha512', 'aes'], help="List of hash algorithms to use (md5, crc32, sha1, sha256, sha512, aes)")
    parser.add_argument("--aes-key", default=None, action="store_true", help="Input AES encryption key")
    parser.add_argument("--gen-aes-key", action="store_true", help="Generate a random AES encryption key")
    parser.add_argument("--demo", action="store_true", help="Create demo target directory and the number of random files.")
    parser.add_argument("--skip", type=str, default="", help="Lines to skip in the format: 1,3-5")

    args = parser.parse_args()

    skip_lines = parse_range(args.skip)

    if args.algo == 'aes':
        if args.aes_key:
            aes_key = args.aes_key.encode('utf-8')
        if args.gen_aes_key:
            aes_key = generate_aes_key()
            print("Generated AES Key:", aes_key.hex())
        else:
            raise ValueError("AES encryption requires a key. Use --gen-aes-key to generate one.")

    duplicate_files, unique_files = find_duplicate_files(args.input_dir, args.algo, skip_lines, args.aes_key)
    remove_choices = []

    if args.demo:
        create_random_files(args.input_dir)
        duplicate_files, unique_files = find_duplicate_files(args.input_dir, args.algo, skip_lines, args.aes_key)
        print_all_files(duplicate_files, unique_files, args.algo, skip_lines, args.aes_key)

    elif args.remove:
        for hash_value, file_list in duplicate_files.items():
            check_dups(file_list, remove_choices, args.algo, skip_lines, args.aes_key, args.force_remove)
            if remove_choices:
                to_delete = [file_path for i, file_path in enumerate(file_list, start=1) if i in remove_choices]
                print(f"Delete:", end=" ")
                for file_path in to_delete:
                    os.remove(file_path)
                    print(f"{file_path}", end=", ")
                print("\n\n")

    elif args.dup:
        print_duplicate_files(duplicate_files, args.algo, skip_lines, args.aes_key)
    elif args.uniq:
        print_unique_files(unique_files, args.algo, skip_lines, args.aes_key)
    else:
        print_all_files(duplicate_files, unique_files, args.algo, skip_lines, args.aes_key)


if __name__ == "__main__":
    main()
