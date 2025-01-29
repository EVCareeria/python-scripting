import csv

class Csv:
    def __init__(self, month):
        self.month = month

    def create_csv(self):
        # Define the header (columns)
        header = ["Nimi", "Viite", "Maksupäivä", "Arvopäivä", "Summa", "Viesti", "Kulutyyppi", "LisätiedotViesti"]

        with open(f"./csv_files/{self.month}.csv", mode="w", newline="") as file:
            writer = csv.writer(file)

            # Write the header
            writer.writerow(header)

    def add_data(self, data):
        # append mode to add data instead of overwriting
        with open(f"./csv_files/{self.month}.csv", mode='a', newline='') as file:
            writer = csv.writer(file)

            writer.writerow(data)