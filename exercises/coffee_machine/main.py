import json

def insert_coins():
    quarters = int(input("How many quarters: ").strip() or 0)
    dimes = int(input("How many dimes: ").strip() or 0)
    nickels = int(input("How many nickels: ").strip() or 0)
    pennies = int(input("How many pennies: ").strip() or 0)
    return ((quarters * 25) + (dimes * 10) + (nickels * 5) + (pennies * 1)) / 100

def money_leftover(customer, coffee)-> bool:
    cur_coffee = coffee_data["coffees"][coffee]
    if customer >= cur_coffee["price"]:
         leftover = value - cur_coffee["price"]
         print(f"Heres your left over: {leftover}")
         return True
    else:
         print("Not enough money, ya bitch!")
         return False
    
def Check_resources(coffee)-> bool:
    cur_coffee = coffee_data["coffees"][coffee]
    resources = coffee_data["resources"]
    if (coffee == "espresso" or resources["milk"] >= cur_coffee["milk"]) and resources["water"] >= cur_coffee["water"] and resources["coffee"] >= cur_coffee["coffee"]:
         print(f"Your {coffee} coming right up! ")
         return True
    else:
        print("Someone forgot to fill the machine, sorry! Thanks for the money tho :)")
        return False

def prepare_coffee(coffee):
    cur_coffee = coffee_data["coffees"][coffee]
    resources = coffee_data["resources"]
    if coffee != "espresso":
        resources["milk"] -= cur_coffee["milk"] 
    resources["water"] -= cur_coffee["water"] 
    resources["coffee"] -= cur_coffee["coffee"]
    print("Coffee done, have a nice day!")

def print_info():
    resources = coffee_data["resources"]
    print(f"Condiments left: {resources}")

with open("./coffees.json") as json_file:
        coffee_data = json.load(json_file)

machine_on = True

while machine_on:
    order = input("What would you like? (espresso/latte/cappuccino):")

    if order == "espresso":
        check = Check_resources("espresso")
        if check:
            value = insert_coins()
            money_leftover(value, "espresso")
            prepare_coffee("espresso")
        print(value)
    elif order == "latte":
        check = Check_resources("latte")
        if check:
            value = insert_coins()
            money_leftover(value, "latte")
            prepare_coffee("latte")
        print(value)
    elif order == "cappuccino":
        check = Check_resources("cappuccino")
        if check:
            value = insert_coins()
            money_leftover(value, "cappuccino")
            prepare_coffee("cappuccino")
        print(value)
    elif order == "report":
        print_info()
    elif order == "off":
        machine_on = False
        print("Turning machine off")
    else:
        value = insert_coins()
        print(value)