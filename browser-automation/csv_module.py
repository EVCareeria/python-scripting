import csv

def create_csv():
    # Define the header (columns)
    header = ["Nimi", "Viite", "Maksupäivä", "Arvopäivä", "Summa"]

    with open("data.csv", mode="w", newline="") as file:
        writer = csv.writer(file)

        # Write the header
        writer.writerow(header)

def add_data(data):
    # append mode to add data instead of overwriting
    with open("data.csv", mode='a', newline='') as file:
        writer = csv.writer(file)

        writer.writerow(data)