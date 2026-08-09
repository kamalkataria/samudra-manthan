from samudra_manthan.gmail.messages import scan_mailbox


def main():
    messages, sender_counts = scan_mailbox()

    print()
    print("=" * 60)
    print("SAMUDRA MANTHAN")
    print("=" * 60)

    print(f"Messages scanned: {len(messages):,}")
    print(f"Unique senders:   {len(sender_counts):,}")

    print()
    print("TOP 50 SENDERS")
    print("-" * 60)

    for number, (sender, count) in enumerate(
        sender_counts.most_common(50),
        start=1,
    ):
        print(f"{number:>3}. {sender:<40} {count:>6,}")


if __name__ == "__main__":
    main()
