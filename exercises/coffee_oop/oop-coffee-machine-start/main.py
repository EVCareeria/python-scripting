from menu import Menu
from coffee_maker import CoffeeMaker
from money_machine import MoneyMachine
items = Menu()
coffee_machine = CoffeeMaker()
shutdown = False
machine_ready = True
while machine_ready:
    coffee_machine.report()
    while not shutdown:
        payments = MoneyMachine()
        ask = input("What would you like? espresso/latte/cappuccino:").strip()
        coins = payments.process_coins()

        if ask == "off":
            shutdown = True
            continue
        item = items.find_drink(ask)
        sufficient = coffee_machine.is_resource_sufficient(item)
        if not sufficient:
            print(f'Not enough ingredients for {item.name}')
            pass
        if not payments.make_payment(item.cost):
            pass
        coffee_machine.make_coffee(item)

