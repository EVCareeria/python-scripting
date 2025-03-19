def add(n1,n2):
    return n1 + n2

def multiply(n1,n2):
    return n1 * n2

def divide(n1,n2):
    return n1 / n2

def subtract(n1,n2):
    return n1 - n2

def calculator():
    """Very basic calculator app."""
    operations = {
        "+": add,
        "-": subtract,
        "*": multiply,
        "/": divide
    }
    should_accumulate = True
    first_num = float(input("Give first number:   "))

    while should_accumulate:

        operation = input(f"Choose operation: \n + - * /  ")
        print(f"Operation {operation} chosen")
        second_num = float(input("Give second number:   "))

        result = operations[operation](first_num, second_num)
        print(f"{ result}")

        choice = input(f"Type 'y' to continnue calculating with {result}   ")

        if choice == 'y':
            first_num = result
        else:
            should_accumulate = False

#calculator()
if __name__ == "__main__":
    calculator()
