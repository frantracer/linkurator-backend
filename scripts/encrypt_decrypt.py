import argparse
import base64
import hashlib
import logging
import os
import sys

from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def convert_to_fernet_key(key: str | bytes) -> bytes:
    """
    Converts any string or bytes to a Fernet-compatible 32-byte urlsafe base64-encoded key.
    """
    if isinstance(key, str):
        key = key.encode()
    key32 = hashlib.sha256(key).digest()
    return base64.urlsafe_b64encode(key32)

def encrypt_file(key: bytes, input_file: str, output_file: str) -> None:
    f = Fernet(key)
    with open(input_file, "rb") as file:
        data = file.read()
    encrypted = f.encrypt(data)
    with open(output_file, "wb") as file:
        file.write(encrypted)
    logging.info(f"Encrypted {input_file} -> {output_file}")

def decrypt_file(key: bytes, input_file: str, output_file: str) -> None:
    f = Fernet(key)
    with open(input_file, "rb") as file:
        encrypted = file.read()
    decrypted = f.decrypt(encrypted)
    with open(output_file, "wb") as file:
        file.write(decrypted)
    logging.info(f"Decrypted {input_file} -> {output_file}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt or decrypt files using Fernet symmetric encryption.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt a file with a provided key.")
    encrypt_parser.add_argument("input_file", type=str, help="Input file to encrypt")
    encrypt_parser.add_argument("output_file", type=str, help="Output file for encrypted data")

    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt a file with a provided key.")
    decrypt_parser.add_argument("input_file", type=str, help="Input file to decrypt")
    decrypt_parser.add_argument("output_file", type=str, help="Output file for decrypted data")

    args = parser.parse_args()

    key = os.getenv("LINKURATOR_VAULT_PASSWORD")
    if not key:
        logging.error("Environment variable LINKURATOR_VAULT_PASSWORD is not set.")
        sys.exit(1)

    if args.command == "encrypt":
        encrypt_file(convert_to_fernet_key(key), args.input_file, args.output_file)
    elif args.command == "decrypt":
        decrypt_file(convert_to_fernet_key(key), args.input_file, args.output_file)

if __name__ == "__main__":
    main()
