from samudra_manthan.gmail.auth import authenticate_gmail


def main():
    credentials = authenticate_gmail()

    print()
    print("Gmail authentication successful!")
    print(f"Token saved successfully.")
    print(f"Credentials valid: {credentials.valid}")


if __name__ == "__main__":
    main()

