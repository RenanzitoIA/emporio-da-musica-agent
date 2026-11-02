"""Print the data-quality report: `python -m emporio.audit`."""

from emporio.data import StoreData


def main() -> None:
    data = StoreData.load()
    print(f"{len(data.products)} products, {len(data.orders)} orders, "
          f"{len(data.customers)} customers, {len(data.promotions)} promotions\n")
    for issue in data.issues:
        print(f"- {issue}")


if __name__ == "__main__":
    main()
